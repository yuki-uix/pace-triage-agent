"""Blind second labelling, for drift rather than for truth.

`data/labeling_guide.md` requires ambiguous records to be labelled a second time
by a different model family, with Cohen's kappa reported. This runs it over
*every* record, not only the ones that look ambiguous, because the failure it
catches is invisible by inspection: the generator drifting the prose away from
the label the plan assigned.

That happened in the pilot. A slot planned as POLICY_QUERY came back as an email
about why a premium had increased, which reads as PREMIUM_BILLING. Nothing in
the pipeline would have objected, and the record would have entered the golden
set carrying a label a reviewer could argue with.

**A disagreement is not a verdict.** The second model is not more right than the
plan. A disagreement means one of three things — the prose drifted, the record is
genuinely ambiguous, or the second model is wrong — and a human decides which.
Per the labeling guide, genuine ambiguity is reported alongside the accuracy
numbers rather than quietly resolved.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass

from openai import OpenAI
from sklearn.metrics import cohen_kappa_score

from src.contract import FailureCounters, call_with_contract
from src.dataset import EnquiryRecord, Tag
from src.generate import Usage, load_env
from src.quotas import load_records
from src.schema import CaseType, Priority, TriageOutput

SYSTEM = (
    "You are an experienced customer service supervisor at a Hong Kong life "
    "insurer. Classify the enquiry you are shown. Judge only what the email "
    "says. Respond with JSON only, no prose and no code fence."
)

RUBRIC = """Classify this customer enquiry.

case_type is one of:
  POLICY_QUERY     - a question about coverage, terms, or how the policy works
  PREMIUM_BILLING  - payments, deductions, refunds, premium amounts
  ADDRESS_CHANGE   - updating contact or correspondence details
  CLAIM            - anything about a submitted or intended claim
  COMPLAINT        - dissatisfaction with service as the primary subject
  OTHER            - genuinely fits none of the above, not merely difficult

priority is one of:
  URGENT - a financial or coverage consequence with a near-term deadline, or an
           explicit escalation threat. Anger on its own is NOT urgent.
  NORMAL - an ordinary request with no stated deadline
  LOW    - informational, no deadline, no dissatisfaction

confidence is your own probability, 0 to 1, that your case_type is correct.

Return JSON: {"case_type": ..., "priority": ..., "confidence": ...}

Subject: %s

Body:
%s"""


@dataclass
class Disagreement:
    record_id: str
    field: str
    planned: str
    second_opinion: str
    confidence: float
    tags: tuple[str, ...]
    acceptable: tuple[str, ...]

    @property
    def defensible_under_the_guide(self) -> bool:
        """A mixed-topic record listing this alternative is ambiguous by design."""
        return self.field == "case_type" and self.second_opinion in self.acceptable


def relabel(client: OpenAI, model: str, record: EnquiryRecord,
            counters: FailureCounters, usage: Usage) -> TriageOutput:
    def call() -> str:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": RUBRIC % (record.subject, record.body)},
            ],
            max_tokens=2048,
        )
        usage.add(response.usage)
        return response.choices[0].message.content or ""

    return call_with_contract(call, TriageOutput, counters)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="data/enquiries.jsonl")
    parser.add_argument("--out", default="results/relabel.json")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--runs", type=int, default=1,
                        help="repeat the whole pass; a single run cannot separate "
                             "label drift from relabeller noise")
    args = parser.parse_args(argv[1:])

    load_env()
    client = OpenAI(
        api_key=os.environ["DASHSCOPE_API_KEY"],
        base_url=os.environ["DASHSCOPE_BASE_URL"],
    )
    model = os.environ["JUDGE_MODEL"]

    records = load_records(args.dataset)
    counters, usage = FailureCounters(), Usage()

    from collections import Counter
    from concurrent.futures import ThreadPoolExecutor
    from statistics import mean, stdev

    kappas: list[tuple[float, float]] = []
    contested: Counter[tuple[str, str]] = Counter()
    seen: dict[tuple[str, str], set[str]] = {}

    for run in range(args.runs):
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            opinions = list(
                pool.map(lambda r: relabel(client, model, r, counters, usage), records)
            )

        for record, opinion in zip(records, opinions):
            if opinion.case_type is not record.expected_type:
                key = (record.id, "case_type")
                contested[key] += 1
                seen.setdefault(key, set()).add(opinion.case_type.value)
            if opinion.priority is not record.expected_priority:
                key = (record.id, "priority")
                contested[key] += 1
                seen.setdefault(key, set()).add(opinion.priority.value)

        kappas.append((
            cohen_kappa_score(
                [r.expected_type.value for r in records],
                [o.case_type.value for o in opinions],
                labels=[c.value for c in CaseType],
            ),
            cohen_kappa_score(
                [r.expected_priority.value for r in records],
                [o.priority.value for o in opinions],
                labels=[p.value for p in Priority],
            ),
        ))
        print(f"run {run + 1}/{args.runs}: kappa case_type "
              f"{kappas[-1][0]:.3f}, priority {kappas[-1][1]:.3f}", flush=True)

    def spread(values: list[float]) -> str:
        if len(values) == 1:
            return f"{values[0]:.3f} (single run - no spread measurable)"
        return (f"{mean(values):.3f} +/- {stdev(values):.3f} "
                f"(min {min(values):.3f}, max {max(values):.3f})")

    planned = {r.id: r for r in records}

    print(f"\n{len(records)} records x {args.runs} run(s), blind, by {model}\n")
    print(f"Cohen's kappa, case_type: {spread([k[0] for k in kappas])}")
    print(f"Cohen's kappa, priority:  {spread([k[1] for k in kappas])}\n")

    def documented(key: tuple[str, str]) -> bool:
        """The record already declares this alternative as defensible.

        A record carrying `acceptable_types` has been adjudicated: lenient
        accuracy credits either label and the guide asks for the ambiguity to be
        reported, not resolved. Counting it as outstanding would invite someone
        to 'fix' a label that is deliberately contestable.
        """
        record_id, field = key
        if field != "case_type":
            return False
        allowed = {t.value for t in planned[record_id].acceptable_types}
        return bool(allowed) and seen[key] <= allowed

    always = [k for k, n in contested.items() if n == args.runs]
    outstanding = [k for k in always if not documented(k)]
    sometimes = [k for k, n in contested.items() if n < args.runs]
    print(f"{len(always)} contested in every run, of which {len(outstanding)} "
          f"outstanding ({len(always) - len(outstanding)} already documented as "
          f"ambiguous); {len(sometimes)} contested in some runs only\n")
    print("A record contested in every run is a label worth arguing about. One")
    print("contested intermittently is mostly relabeller noise and adjudicating")
    print("it would be reading signal into a coin flip.\n")

    for key, count in contested.most_common():
        record_id, field = key
        record = planned[record_id]
        current = (record.expected_type if field == "case_type"
                   else record.expected_priority).value
        if count == args.runs:
            marker = "  " if documented(key) else "->"
        else:
            marker = "  "
        note = "  (declared in acceptable_types)" if documented(key) else ""
        print(f"{marker} {record_id} {field:<9} {count}/{args.runs}  "
              f"plan={current:<16} second={'/'.join(sorted(seen[key]))}{note}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump({
            "model": model,
            "records": len(records),
            "runs": args.runs,
            "kappa_per_run": [{"case_type": k[0], "priority": k[1]} for k in kappas],
            "contested": [
                {"record_id": rid, "field": field, "runs_contested": count,
                 "of_runs": args.runs,
                 "second_opinions": sorted(seen[(rid, field)]),
                 "documented_as_ambiguous": documented((rid, field))}
                for (rid, field), count in contested.most_common()
            ],
            "usage": {"calls": usage.calls, "prompt_tokens": usage.prompt_tokens,
                      "completion_tokens": usage.completion_tokens,
                      "reasoning_tokens": usage.reasoning_tokens},
            "contract_failures": counters.as_dict(),
        }, handle, indent=2)

    print(f"\nusage: {usage.report()}")
    print(f"contract failures: {counters.as_dict()}")
    print(f"written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
