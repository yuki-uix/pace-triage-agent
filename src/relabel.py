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
    args = parser.parse_args(argv[1:])

    load_env()
    client = OpenAI(
        api_key=os.environ["DASHSCOPE_API_KEY"],
        base_url=os.environ["DASHSCOPE_BASE_URL"],
    )
    model = os.environ["JUDGE_MODEL"]

    records = load_records(args.dataset)
    counters, usage = FailureCounters(), Usage()

    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        opinions = list(
            pool.map(lambda r: relabel(client, model, r, counters, usage), records)
        )

    disagreements: list[Disagreement] = []
    for record, opinion in zip(records, opinions):
        common = dict(
            record_id=record.id,
            confidence=opinion.confidence,
            tags=tuple(sorted(t.value for t in record.tags)),
            acceptable=tuple(t.value for t in record.acceptable_types),
        )
        if opinion.case_type is not record.expected_type:
            disagreements.append(Disagreement(
                field="case_type", planned=record.expected_type.value,
                second_opinion=opinion.case_type.value, **common))
        if opinion.priority is not record.expected_priority:
            disagreements.append(Disagreement(
                field="priority", planned=record.expected_priority.value,
                second_opinion=opinion.priority.value, **common))

    kappa_type = cohen_kappa_score(
        [r.expected_type.value for r in records],
        [o.case_type.value for o in opinions],
        labels=[c.value for c in CaseType],
    )
    kappa_priority = cohen_kappa_score(
        [r.expected_priority.value for r in records],
        [o.priority.value for o in opinions],
        labels=[p.value for p in Priority],
    )

    needs_human = [d for d in disagreements if not d.defensible_under_the_guide]

    print(f"{len(records)} records relabelled blind by {model}\n")
    print(f"Cohen's kappa, case_type: {kappa_type:.3f}")
    print(f"Cohen's kappa, priority:  {kappa_priority:.3f}\n")
    print(f"{len(disagreements)} disagreement(s); "
          f"{len(needs_human)} need human adjudication\n")

    for d in sorted(disagreements, key=lambda d: d.record_id):
        marker = "  " if d.defensible_under_the_guide else "->"
        note = " (listed in acceptable_types)" if d.defensible_under_the_guide else ""
        print(f"{marker} {d.record_id} {d.field:<9} plan={d.planned:<16}"
              f" second={d.second_opinion:<16} conf={d.confidence:.2f}"
              f" tags={','.join(d.tags) or '-'}{note}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump({
            "model": model,
            "records": len(records),
            "kappa_case_type": kappa_type,
            "kappa_priority": kappa_priority,
            "disagreements": [vars(d) | {
                "defensible_under_the_guide": d.defensible_under_the_guide
            } for d in disagreements],
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
