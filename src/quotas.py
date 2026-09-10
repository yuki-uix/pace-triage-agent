"""Dataset quotas, as assertions rather than as a counting exercise.

`docs/03-data-spec.md`: "Fix these before generating. Do not generate freely and
count afterwards." This module is what makes that true — the quotas are declared
here, the generator targets them, and the check fails loudly if the finished
dataset misses one.

`QUOTAS` is exported and is the single source of truth. The tests iterate it, so
a quota added here without being satisfiable is a test failure rather than a
line in a checklist nobody re-reads.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from src.dataset import Enquiry, EnquiryRecord, GoldenLabel, Tag
from src.schema import CaseType, Priority

MIN_RECORDS = 40
MAX_RECORDS = 50


@dataclass(frozen=True)
class Quota:
    """One counted property. Exactly one of `minimum` or `exact` is set."""

    name: str
    predicate: Callable[[EnquiryRecord], bool]
    minimum: int | None = None
    exact: int | None = None

    def __post_init__(self) -> None:
        if (self.minimum is None) == (self.exact is None):
            raise ValueError(f"quota {self.name!r} needs exactly one of minimum/exact")

    def violation(self, records: Sequence[EnquiryRecord]) -> str | None:
        count = sum(1 for record in records if self.predicate(record))
        if self.exact is not None and count != self.exact:
            return f"{self.name}: expected exactly {self.exact}, found {count}"
        if self.minimum is not None and count < self.minimum:
            return f"{self.name}: expected at least {self.minimum}, found {count}"
        return None


def _of_type(case_type: CaseType) -> Callable[[EnquiryRecord], bool]:
    return lambda record: record.expected_type is case_type


def _of_priority(priority: Priority) -> Callable[[EnquiryRecord], bool]:
    return lambda record: record.expected_priority is priority


def _tagged(tag: Tag) -> Callable[[EnquiryRecord], bool]:
    return lambda record: tag in record.tags


QUOTAS: tuple[Quota, ...] = (
    *(
        Quota(f"case type {case_type.value}", _of_type(case_type), minimum=5)
        for case_type in CaseType
    ),
    Quota("priority URGENT", _of_priority(Priority.URGENT), minimum=8),
    Quota("priority NORMAL", _of_priority(Priority.NORMAL), minimum=15),
    Quota("priority LOW", _of_priority(Priority.LOW), minimum=8),
    Quota("mixed topic", _tagged(Tag.MIXED_TOPIC), exact=5),
    Quota("angry tone", _tagged(Tag.ANGRY), exact=4),
    Quota("missing information", _tagged(Tag.MISSING_INFO), exact=4),
    Quota("refusal", _tagged(Tag.REFUSAL), exact=2),
    Quota("prompt injection", _tagged(Tag.INJECTION), exact=2),
    Quota("noisy", _tagged(Tag.NOISY), exact=6),
)


def check_quotas(records: Sequence[EnquiryRecord]) -> list[str]:
    """Every unmet quota, as human-readable strings. Empty means the set is valid."""
    violations = []

    if not MIN_RECORDS <= len(records) <= MAX_RECORDS:
        violations.append(
            f"record count: expected {MIN_RECORDS}-{MAX_RECORDS}, found {len(records)}"
        )

    ids = [record.id for record in records]
    duplicates = sorted({record_id for record_id in ids if ids.count(record_id) > 1})
    if duplicates:
        violations.append(f"duplicate ids: {', '.join(duplicates)}")

    violations.extend(
        violation
        for violation in (quota.violation(records) for quota in QUOTAS)
        if violation is not None
    )
    return violations


ENQUIRIES = "data/enquiries.jsonl"
GOLDEN = "data/golden.jsonl"


def _read(path: str, model):
    with open(path, encoding="utf-8") as handle:
        return [model.model_validate_json(line) for line in handle if line.strip()]


def load_enquiries(path: str = ENQUIRIES) -> list[Enquiry]:
    """The emails, without their answers. This is what the pipeline reads."""
    return _read(path, Enquiry)


def load_golden(path: str = GOLDEN) -> list[GoldenLabel]:
    """The answers. Frozen at tag `golden-v1`."""
    return _read(path, GoldenLabel)


def load_records(path: str = ENQUIRIES, golden_path: str = GOLDEN) -> list[EnquiryRecord]:
    """The joined view, for generation, quota checking and scoring.

    An id present in one file and missing from the other raises. A benchmark
    whose halves have drifted apart is worse than no benchmark, and the failure
    is otherwise silent - the missing record simply never gets scored.
    """
    enquiries = {enquiry.id: enquiry for enquiry in load_enquiries(path)}
    labels = {label.id: label for label in load_golden(golden_path)}

    only_enquiries = sorted(set(enquiries) - set(labels))
    only_labels = sorted(set(labels) - set(enquiries))
    if only_enquiries or only_labels:
        raise ValueError(
            f"enquiries and golden labels disagree; "
            f"unlabelled: {only_enquiries}, orphaned labels: {only_labels}"
        )

    return [EnquiryRecord.join(enquiries[key], labels[key])
            for key in sorted(enquiries)]


def main(argv: Sequence[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Check a dataset against the quotas in docs/03-data-spec.md.")
    parser.add_argument("dataset", nargs="?", default=ENQUIRIES,
                        help=f"enquiries JSONL (default: {ENQUIRIES})")
    parser.add_argument("--golden", default=GOLDEN,
                        help=f"golden labels JSONL (default: {GOLDEN})")
    args = parser.parse_args(list(argv[1:]))

    records = load_records(args.dataset, args.golden)
    violations = check_quotas(records)

    if violations:
        print(f"{len(violations)} quota violation(s) in {args.dataset}:",
              file=sys.stderr)
        for violation in violations:
            print(f"  - {violation}", file=sys.stderr)
        return 1

    print(f"{len(records)} records, all {len(QUOTAS)} quotas met")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
