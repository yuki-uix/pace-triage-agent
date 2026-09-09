"""Serial latency and cost measurement.

`CLAUDE.md`: latency is measured single-threaded, with the first call discarded,
and never in the same run as the concurrent quality evaluation. Those are not
stylistic preferences. A concurrent run measures queueing behaviour rather than
the model, and a cold first call measures connection setup.

This module therefore has no concurrency in it at all, and says so where a
future reader would otherwise be tempted to add some.

**Tokens are measured; prices are an input.** The provider does not publish
per-token prices for these snapshots anywhere citable, so they come from
`data/model_prices.json`, filled in from the billing console. A missing price
produces a refusal, not a zero: a cost table that looks complete and is wrong is
worse than one with a hole in it.
"""

from __future__ import annotations

import json
import math
import os
import pathlib
import statistics
import time
from dataclasses import dataclass, field

from openai import OpenAI

from src.contract import FailureCounters, RetryExhaustedError
from src.generate import load_env
from src.pipeline import PipelineConfig, StageConfig, run_draft, run_triage
from src.quotas import load_enquiries

PRICES_PATH = "data/model_prices.json"


class MissingPrice(RuntimeError):
    """Raised rather than reporting a cost of zero for an unpriced model."""


@dataclass
class StageSamples:
    """Latency and token counts for one stage, across the measured records."""

    stage: str
    model: str
    seconds: list[float] = field(default_factory=list)
    prompt_tokens: list[int] = field(default_factory=list)
    completion_tokens: list[int] = field(default_factory=list)
    reasoning_tokens: list[int] = field(default_factory=list)

    def add(self, trace) -> None:
        self.seconds.append(trace.seconds)
        self.prompt_tokens.append(trace.prompt_tokens)
        self.completion_tokens.append(trace.completion_tokens)
        self.reasoning_tokens.append(trace.reasoning_tokens)

    @property
    def n(self) -> int:
        return len(self.seconds)

    def median(self) -> float:
        return statistics.median(self.seconds) if self.seconds else float("nan")

    def p95(self) -> float:
        """Nearest-rank p95. At n=39 this is the second-slowest observation, and
        the write-up should say so rather than implying a smooth distribution."""
        if not self.seconds:
            return float("nan")
        ordered = sorted(self.seconds)
        rank = max(1, math.ceil(0.95 * len(ordered)))
        return ordered[rank - 1]

    def mean_tokens(self) -> tuple[float, float]:
        return (statistics.mean(self.prompt_tokens) if self.prompt_tokens else 0.0,
                statistics.mean(self.completion_tokens) if self.completion_tokens else 0.0)


def load_prices(path: str = PRICES_PATH) -> dict:
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    return data.get("prices", {})


def cost_per_invocation(model: str, prompt_tokens: float, completion_tokens: float,
                        prices: dict) -> float:
    """Money for one call. Raises when the model has no price on file."""
    entry = prices.get(model) or {}
    input_price = entry.get("input_per_mtok")
    output_price = entry.get("output_per_mtok")
    if input_price is None or output_price is None:
        raise MissingPrice(
            f"no price on file for {model!r}. Fill it in from the billing "
            f"console in {PRICES_PATH}; a cost of zero would look like an answer."
        )
    return (prompt_tokens * input_price + completion_tokens * output_price) / 1_000_000


def measure(client, config: PipelineConfig, records, counters: FailureCounters,
            warmups: int = 1) -> tuple[dict[str, StageSamples], list[float], int]:
    """One record at a time. No pool, no gather, no threads - deliberately.

    Adding concurrency here would make the numbers describe the harness rather
    than the models, and the two runs must never be merged.
    """
    stages = {
        "triage": StageSamples("triage", config.triage.model),
        "draft": StageSamples("draft", config.draft.model),
    }
    end_to_end: list[float] = []
    discarded = 0

    for record in records:
        started = time.perf_counter()
        try:
            triage, triage_trace = run_triage(client, config.triage, record.subject,
                                              record.body, counters)
            _, draft_trace = run_draft(client, config.draft, record.subject,
                                       record.body, triage, counters)
        except RetryExhaustedError:
            # Counted in `counters`, never folded into a latency figure: a case
            # that produced no output has no meaningful end-to-end time.
            continue
        elapsed = time.perf_counter() - started

        if discarded < warmups:
            # Counted among the records that succeeded, not by position. A first
            # record that exhausts its retries would otherwise consume the
            # warm-up slot silently, and the report would claim none was taken
            # while the first timed call was the cold one.
            discarded += 1
            continue

        stages["triage"].add(triage_trace)
        stages["draft"].add(draft_trace)
        end_to_end.append(elapsed)

    return stages, end_to_end, discarded


def render(stages: dict[str, StageSamples], end_to_end: list[float],
           discarded: int, counters: FailureCounters, prices: dict) -> str:
    lines = [
        f"Serial run, single-threaded. {discarded} warm-up call(s) discarded.",
        "",
        f"{'stage':<10}{'model':<26}{'n':>4}{'median s':>11}{'p95 s':>9}"
        f"{'in tok':>9}{'out tok':>9}{'cost/call':>12}",
    ]
    for stage in ("triage", "draft"):
        samples = stages[stage]
        prompt_mean, completion_mean = samples.mean_tokens()
        try:
            cost = f"{cost_per_invocation(samples.model, prompt_mean, completion_mean, prices):.6f}"
        except MissingPrice:
            cost = "no price"
        lines.append(
            f"{stage:<10}{samples.model:<26}{samples.n:>4}"
            f"{samples.median():>11.2f}{samples.p95():>9.2f}"
            f"{prompt_mean:>9.0f}{completion_mean:>9.0f}{cost:>12}"
        )

    if end_to_end:
        ordered = sorted(end_to_end)
        lines += [
            "",
            f"end to end   median {statistics.median(ordered):.2f}s   "
            f"p95 {ordered[max(1, math.ceil(0.95 * len(ordered))) - 1]:.2f}s   "
            f"n={len(ordered)}",
            f"p95 at n={len(ordered)} is the "
            f"{len(ordered) - max(1, math.ceil(0.95 * len(ordered))) + 1}"
            f"-slowest observation, not a fitted quantile.",
        ]

    failures = counters.as_dict()
    lines += [
        "",
        "failure counts, kept apart and never folded into any denominator:",
        f"  schema failures    {failures['schema_failures']}",
        f"  retry exhaustions  {failures['retry_exhaustions']}",
        f"  provider refusals  {failures['provider_refusals']}",
    ]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="data/enquiries.jsonl")
    parser.add_argument("--triage-model", default=None)
    parser.add_argument("--draft-model", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--out", default="results/latency.json")
    args = parser.parse_args(argv[1:])

    load_env()
    client = OpenAI(api_key=os.environ["DASHSCOPE_API_KEY"],
                    base_url=os.environ["DASHSCOPE_BASE_URL"])
    config = PipelineConfig.from_env(args.triage_model, args.draft_model)
    records = load_enquiries(args.dataset)[: args.limit]
    counters = FailureCounters()
    prices = load_prices()

    stages, end_to_end, discarded = measure(client, config, records, counters,
                                            args.warmups)
    report = render(stages, end_to_end, discarded, counters, prices)
    print(report)

    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.out).write_text(json.dumps({
        "mode": "serial, single-threaded; never merged with a quality run",
        "warmups_discarded": discarded,
        "stages": {
            name: {
                "model": s.model, "n": s.n,
                "median_seconds": s.median(), "p95_seconds": s.p95(),
                "seconds": s.seconds,
                "mean_prompt_tokens": s.mean_tokens()[0],
                "mean_completion_tokens": s.mean_tokens()[1],
                "mean_reasoning_tokens": (statistics.mean(s.reasoning_tokens)
                                          if s.reasoning_tokens else 0.0),
            } for name, s in stages.items()
        },
        "end_to_end_seconds": end_to_end,
        "failure_counts": counters.as_dict(),
        "prices_available": {m: bool(p.get("input_per_mtok") is not None)
                             for m, p in prices.items()},
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nwritten to {args.out}")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv))
