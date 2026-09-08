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

from src.dataset import EnquiryRecord, Tag
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


def load_records(path: str) -> list[EnquiryRecord]:
    """Read a JSONL dataset. A record that does not validate raises here."""
    with open(path, encoding="utf-8") as handle:
        return [
            EnquiryRecord.model_validate_json(line)
            for line in handle
            if line.strip()
        ]


def main(argv: Sequence[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m src.quotas <dataset.jsonl>", file=sys.stderr)
        return 2

    records = load_records(argv[1])
    violations = check_quotas(records)

    if violations:
        print(f"{len(violations)} quota violation(s) in {argv[1]}:", file=sys.stderr)
        for violation in violations:
            print(f"  - {violation}", file=sys.stderr)
        return 1

    print(f"{len(records)} records, all {len(QUOTAS)} quotas met")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
