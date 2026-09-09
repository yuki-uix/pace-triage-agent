"""Case-type and priority scoring. No LLM: a set comparison cannot need a judge.

Per-case metrics for DeepEval, plus the aggregation that turns them into the
confusion matrix and per-class F1 the results table needs. The aggregation lives
here rather than in the runner so the report and the pass/fail check read the
same numbers from the same function.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

from src.schema import CaseType, Priority


def _meta(test_case: LLMTestCase) -> dict:
    if not test_case.metadata:
        raise ValueError("test case carries no metadata; build it with as_test_case()")
    return test_case.metadata


class CaseTypeAccuracy(BaseMetric):
    """Strict accuracy against `expected_type`.

    `lenient` scores against `acceptable_types` instead, for records the labeling
    guide has adjudicated as genuinely ambiguous. Both are reported: the gap
    between them says how much of the error is the task being ambiguous rather
    than the model being weak.
    """

    def __init__(self, threshold: float = 1.0, lenient: bool = False):
        self.threshold = threshold
        self.lenient = lenient

    @property
    def __name__(self) -> str:  # BaseMetric declares this read-only
        return "case type (lenient)" if self.lenient else "case type"

    def measure(self, test_case: LLMTestCase) -> float:
        meta = _meta(test_case)
        expected = meta["expected_type"]
        acceptable = set(meta.get("acceptable_types") or [expected])
        predicted = meta["predicted_type"]

        correct = predicted in acceptable if self.lenient else predicted == expected
        self.score = 1.0 if correct else 0.0
        self.success = self.score >= self.threshold
        self.reason = (
            f"predicted {predicted}, expected {expected}"
            + (f", acceptable {sorted(acceptable)}" if self.lenient else "")
        )
        return self.score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return bool(getattr(self, "success", False))


class PriorityAccuracy(BaseMetric):
    """Priority accuracy. `urgent_only` restricts scoring to the URGENT records.

    URGENT recall gets its own bar (95%) because the cost of missing one is not
    the cost of missing any other label — see `docs/02-metrics.md`.
    """

    def __init__(self, threshold: float = 1.0, urgent_only: bool = False):
        self.threshold = threshold
        self.urgent_only = urgent_only

    @property
    def __name__(self) -> str:
        return "urgent recall" if self.urgent_only else "priority"

    def measure(self, test_case: LLMTestCase) -> float:
        meta = _meta(test_case)
        expected, predicted = meta["expected_priority"], meta["predicted_priority"]

        if self.urgent_only and expected != Priority.URGENT.value:
            self.skipped = True
            self.score = 1.0
            self.success = True
            self.reason = "not an URGENT record; excluded from urgent recall"
            return self.score

        self.score = 1.0 if predicted == expected else 0.0
        self.success = self.score >= self.threshold
        self.reason = f"predicted {predicted}, expected {expected}"
        return self.score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return bool(getattr(self, "success", False))


@dataclass
class ClassificationReport:
    """Aggregate view. Counts are kept, not just rates — n=40 needs both."""

    labels: list[str]
    matrix: dict[str, Counter] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(sum(row.values()) for row in self.matrix.values())

    @property
    def correct(self) -> int:
        return sum(row[label] for label, row in self.matrix.items())

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0

    def support(self, label: str) -> int:
        return sum(self.matrix[label].values())

    def recall(self, label: str) -> float:
        support = self.support(label)
        return self.matrix[label][label] / support if support else 0.0

    def precision(self, label: str) -> float:
        predicted = sum(row[label] for row in self.matrix.values())
        return self.matrix[label][label] / predicted if predicted else 0.0

    def f1(self, label: str) -> float:
        precision, recall = self.precision(label), self.recall(label)
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)

    def render(self) -> str:
        width = max(len(label) for label in self.labels) + 2
        head = "expected \\ predicted".ljust(width) + "".join(
            label[:8].rjust(10) for label in self.labels
        )
        lines = [head]
        for expected in self.labels:
            row = self.matrix[expected]
            lines.append(
                expected.ljust(width)
                + "".join(str(row[p]).rjust(10) for p in self.labels)
            )
        lines.append("")
        lines.append("label".ljust(width) + "".join(
            h.rjust(10) for h in ("support", "precision", "recall", "f1")))
        for label in self.labels:
            lines.append(
                label.ljust(width)
                + str(self.support(label)).rjust(10)
                + f"{self.precision(label):.3f}".rjust(10)
                + f"{self.recall(label):.3f}".rjust(10)
                + f"{self.f1(label):.3f}".rjust(10)
            )
        lines.append("")
        lines.append(f"accuracy: {self.correct}/{self.total} = {self.accuracy:.3f}")
        return "\n".join(lines)


def build_report(pairs: list[tuple[str, str]], labels: list[str]) -> ClassificationReport:
    """`pairs` is (expected, predicted). Unknown labels raise rather than vanish."""
    report = ClassificationReport(labels=labels,
                                  matrix={label: Counter() for label in labels})
    for expected, predicted in pairs:
        if expected not in labels or predicted not in labels:
            raise ValueError(f"unknown label in pair ({expected!r}, {predicted!r})")
        report.matrix[expected][predicted] += 1
    return report


def case_type_report(pairs: list[tuple[str, str]]) -> ClassificationReport:
    return build_report(pairs, [c.value for c in CaseType])


def priority_report(pairs: list[tuple[str, str]]) -> ClassificationReport:
    return build_report(pairs, [p.value for p in Priority])
