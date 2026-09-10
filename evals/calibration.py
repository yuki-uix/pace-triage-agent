"""Calibration: is a stated confidence of 0.8 right about 80% of the time?

Only the triage stage is needed, so this runs triage alone rather than the whole
pipeline - the drafting stage and the judge contribute nothing to a calibration
table and cost most of the money.

**The table is reported with its intervals and its limits, not as a curve.**
`docs/02-metrics.md` is explicit: at n=40 the buckets hold single-digit counts
and Wilson intervals are wide enough that the table cannot distinguish a
well-calibrated agent from a badly calibrated one. Reporting it anyway, with the
intervals visible and the required sample size stated, is the honest move. A
clean-looking reliability curve drawn on 40 points and reasoned from is a
statistical error.

**Nothing is recalibrated.** Fitting Platt scaling or isotonic regression on 40
points would produce a model of this sample, and the corrected numbers would
look better while meaning less.
"""

from __future__ import annotations

import json
import math
import os
import pathlib
from dataclasses import dataclass, field

from openai import OpenAI
from sklearn.metrics import brier_score_loss

from src.contract import FailureCounters, RetryExhaustedError
from src.generate import load_env
from src.pipeline import StageConfig, run_triage
from src.quotas import load_records

# 0.5 upward, since a derived confidence below 0.5 means the model preferred a
# label it did not emit. Anything lower lands in the underflow bucket and is
# reported rather than dropped.
EDGES: tuple[float, ...] = (0.5, 0.6, 0.7, 0.8, 0.9, 1.0001)
Z = 1.96  # 95%


def wilson(successes: int, n: int, z: float = Z) -> tuple[float, float]:
    """Interval for a proportion, which is what a bucket accuracy is.

    The normal approximation is wrong at these counts - at n=3 it can put the
    bound outside [0, 1] - and the whole point of showing the interval is that
    it is honest about small buckets.
    """
    if n == 0:
        return (float("nan"), float("nan"))
    p = successes / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z / denominator * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, centre - half), min(1.0, centre + half))


def required_n(p: float, half_width: float = 0.05, z: float = Z) -> int:
    """Sample size for a Wilson half-width of `half_width` at accuracy `p`.

    The answer to "what would it take to actually claim this", which the metrics
    document asks for by name.
    """
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.ceil(z * z * p * (1 - p) / (half_width * half_width))


@dataclass
class Bucket:
    low: float
    high: float
    confidences: list[float] = field(default_factory=list)
    correct: list[bool] = field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.correct)

    @property
    def hits(self) -> int:
        return sum(self.correct)

    @property
    def accuracy(self) -> float:
        return self.hits / self.n if self.n else float("nan")

    @property
    def mean_confidence(self) -> float:
        return sum(self.confidences) / self.n if self.n else float("nan")

    def interval(self) -> tuple[float, float]:
        return wilson(self.hits, self.n)


def bucket_all(pairs: list[tuple[float, bool]]) -> tuple[list[Bucket], Bucket]:
    """Returns the buckets and the underflow (confidence below the first edge)."""
    buckets = [Bucket(EDGES[i], EDGES[i + 1]) for i in range(len(EDGES) - 1)]
    underflow = Bucket(0.0, EDGES[0])

    for confidence, correct in pairs:
        target = underflow
        for bucket in buckets:
            if bucket.low <= confidence < bucket.high:
                target = bucket
                break
        target.confidences.append(confidence)
        target.correct.append(correct)
    return buckets, underflow


def expected_calibration_error(buckets: list[Bucket], underflow: Bucket) -> float:
    """Weighted mean gap between stated confidence and observed accuracy."""
    populated = [b for b in [underflow, *buckets] if b.n]
    total = sum(b.n for b in populated)
    if not total:
        return float("nan")
    return sum(b.n / total * abs(b.accuracy - b.mean_confidence) for b in populated)


def render(model: str, pairs: list[tuple[float, bool]], buckets: list[Bucket],
           underflow: Bucket, ece: float, brier: float,
           counters: FailureCounters) -> str:
    lines = [
        f"Calibration, triage stage, {model}",
        f"n = {len(pairs)} records from the frozen golden set",
        "",
        f"{'bucket':<14}{'n':>4}{'mean conf':>11}{'accuracy':>10}"
        f"{'95% Wilson interval':>24}",
    ]
    for bucket in [underflow, *buckets]:
        if not bucket.n:
            continue
        low, high = bucket.interval()
        label = (f"<{bucket.high:.1f}" if bucket is underflow
                 else f"{bucket.low:.1f}-{min(bucket.high, 1.0):.1f}")
        lines.append(
            f"{label:<14}{bucket.n:>4}{bucket.mean_confidence:>11.3f}"
            f"{bucket.accuracy:>10.3f}{f'[{low:.3f}, {high:.3f}]':>24}")

    lines += [
        "",
        f"ECE   {ece:.4f}",
        f"Brier {brier:.4f}",
        "",
        "What this table cannot show:",
    ]
    widest = max((b for b in [underflow, *buckets] if b.n),
                 key=lambda b: b.interval()[1] - b.interval()[0], default=None)
    if widest is not None:
        low, high = widest.interval()
        lines.append(
            f"  The widest bucket interval spans {high - low:.2f} on n={widest.n}. "
            f"An interval that wide is consistent with both good and bad "
            f"calibration in that bucket.")
    overall = sum(1 for _, correct in pairs if correct) / len(pairs) if pairs else 0.0
    lines += [
        f"  To claim a bucket accuracy to within +/-0.05 at the observed overall "
        f"accuracy of {overall:.3f} would need about {required_n(overall)} records "
        f"in that bucket alone.",
        "  No recalibration is fitted: Platt or isotonic on this many points "
        "models the sample, not the agent.",
        "",
        f"failure counts: {counters.as_dict()}",
    ]
    return "\n".join(lines)


def collect(client, model: str, records, counters: FailureCounters,
            workers: int) -> list[dict]:
    """Triage only. The draft stage and the judge add nothing here."""
    from concurrent.futures import ThreadPoolExecutor

    config = StageConfig(model)

    def one(record):
        try:
            output, trace = run_triage(client, config, record.subject, record.body,
                                       counters)
        except (RetryExhaustedError, Exception):  # noqa: BLE001
            return None
        return {"record_id": record.id, "confidence": output.confidence,
                "predicted_type": output.case_type.value,
                "expected_type": record.expected_type.value,
                "correct": output.case_type is record.expected_type,
                "confidence_method": trace.confidence_method}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return [row for row in pool.map(one, records) if row is not None]


def main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", default=None,
                        help="comma-separated; defaults to both under test")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--out", default="results/calibration.json")
    args = parser.parse_args(argv[1:])

    load_env()
    client = OpenAI(api_key=os.environ["DASHSCOPE_API_KEY"],
                    base_url=os.environ["DASHSCOPE_BASE_URL"])
    models = (args.models.split(",") if args.models
              else [os.environ["TRIAGE_MODEL_A"], os.environ["TRIAGE_MODEL_B"]])
    records = load_records()

    payload = {"golden_set": "golden-v1", "runs": 1,
               "no_recalibration_fitted": True, "models": {}}

    for model in models:
        counters = FailureCounters()
        rows = collect(client, model, records, counters, args.workers)
        pairs = [(row["confidence"], row["correct"]) for row in rows]
        buckets, underflow = bucket_all(pairs)
        ece = expected_calibration_error(buckets, underflow)
        brier = brier_score_loss([int(c) for _, c in pairs],
                                 [p for p, _ in pairs]) if pairs else float("nan")

        print(render(model, pairs, buckets, underflow, ece, brier, counters))
        print()

        payload["models"][model] = {
            "n": len(pairs), "ece": ece, "brier": brier,
            "confidence_methods": sorted({row["confidence_method"] for row in rows}),
            "buckets": [
                {"low": b.low, "high": b.high, "n": b.n,
                 "mean_confidence": b.mean_confidence, "accuracy": b.accuracy,
                 "wilson_low": b.interval()[0], "wilson_high": b.interval()[1]}
                for b in [underflow, *buckets] if b.n],
            "per_record": rows,
            "failure_counts": counters.as_dict(),
        }

    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True)
                                      + "\n", encoding="utf-8")
    print(f"written to {args.out}")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv))
