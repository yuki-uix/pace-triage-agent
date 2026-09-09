"""Which metrics apply to which record, and why the branching is not a DAGMetric.

`docs/02-metrics.md` originally specified DeepEval's `DAGMetric` for this. That
was written before its API was checked. Every node type it offers -
`BinaryJudgementNode`, `NonBinaryJudgementNode`, `TaskNode`, `VerdictNode` - is
LLM-driven: a judgement node takes natural-language criteria and asks a model.
There is no deterministic condition node.

Our branching condition is "does this golden record carry the REFUSAL tag",
which is a set membership test whose answer is already written down. Routing it
through a judgement node would spend a model call, and a model's opinion, on a
fact we hold. `CLAUDE.md` is explicit that a check expressible as a set
comparison does not get a judge, so the flow is a plain function and the metrics
doc is amended rather than the principle bent.

A DAG is still the right shape for the judge pass, where the nodes genuinely are
judgement calls. This is not an argument against `DAGMetric`; it is an argument
against using it where nothing needs judging.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from deepeval.test_case import LLMTestCase

from src.dataset import EnquiryRecord, Tag

# Draft-quality metrics assume the reply engages with the enquiry on its merits.
# A correctly refused enquiry has no merits to engage with, so scoring it here
# would penalise the right answer.
SKIPPED_WHEN_REFUSING: frozenset[str] = frozenset({
    "tone match",
    "summary quality",
    "commitment groundedness",
})


def as_test_case(record: EnquiryRecord, output: dict | None) -> LLMTestCase:
    """Bind a golden record to what the pipeline produced for it.

    `output` is None when the pipeline produced nothing - retry exhaustion, a
    provider error. That case must reach the metrics as a visible absence, not
    as a missing row.
    """
    return LLMTestCase(
        input=f"Subject: {record.subject}\n\n{record.body}",
        actual_output=(output or {}).get("draft_reply") or "",
        metadata={
            "record_id": record.id,
            "expected_type": record.expected_type.value,
            "expected_priority": record.expected_priority.value,
            "acceptable_types": [t.value for t in record.acceptable_types],
            "tags": sorted(t.value for t in record.tags),
            "predicted_type": (output or {}).get("case_type"),
            "predicted_priority": (output or {}).get("priority"),
            "confidence": (output or {}).get("confidence"),
            "summary": (output or {}).get("summary"),
            "draft_reply": (output or {}).get("draft_reply"),
            "produced_output": output is not None,
        },
    )


@dataclass
class CaseResult:
    record_id: str
    scores: dict[str, float] = field(default_factory=dict)
    reasons: dict[str, str] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)
    no_output: bool = False


def applies(metric_name: str, test_case: LLMTestCase) -> bool:
    """The branch. Refusal records skip draft-quality metrics, nothing else."""
    tags = set((test_case.metadata or {}).get("tags") or [])
    if Tag.REFUSAL.value in tags and metric_name in SKIPPED_WHEN_REFUSING:
        return False
    return True


def evaluate_case(test_case: LLMTestCase, metrics) -> CaseResult:
    """Run the applicable metrics over one case.

    A case with no pipeline output is recorded as such and its draft-dependent
    metrics are skipped rather than scored zero: a zero would be
    indistinguishable from a draft that was produced and was wrong, and the two
    failures have different causes and different fixes.
    """
    meta = test_case.metadata or {}
    result = CaseResult(record_id=meta["record_id"],
                        no_output=not meta.get("produced_output", False))

    for metric in metrics:
        name = metric.__name__
        if not applies(name, test_case):
            result.skipped.append(name)
            continue
        if result.no_output:
            # Every metric, including classification. A case that produced no
            # output was not misclassified - there was no classification. Scoring
            # it zero would put a schema failure into the accuracy denominator as
            # a wrong answer, which is the one thing `docs/02-metrics.md` says
            # failure counts must never do.
            result.skipped.append(name)
            continue

        metric.measure(test_case)
        if getattr(metric, "skipped", False):
            metric.skipped = False
            result.skipped.append(name)
            continue

        result.scores[name] = metric.score
        result.reasons[name] = getattr(metric, "reason", "")

    return result
