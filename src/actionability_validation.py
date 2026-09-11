"""Contract and integrity checks for the balanced actionability challenge set."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from pydantic import (
    BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator,
)


VALIDATION_SET = "data/actionability_validation_set.jsonl"
BANDS = ((0, 2), (3, 5), (6, 8), (9, 10))
EXPECTED_RECORDS = 6
EXPECTED_VARIANTS = 24


class ActionabilityValidationDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    variant_id: StrictStr = Field(pattern=r"^AV-\d{3}-[A-D]$")
    record_id: StrictStr = Field(pattern=r"^ENQ-\d{3}$")
    expected_band: StrictInt = Field(ge=0, le=3)
    expected_score_range: tuple[StrictInt, StrictInt]
    draft_reply: StrictStr = Field(min_length=1)
    actionability_tags: tuple[StrictStr, ...] = Field(min_length=1)
    rationale: StrictStr = Field(min_length=1)

    @model_validator(mode="after")
    def _band_and_id_agree(self) -> "ActionabilityValidationDraft":
        if self.expected_score_range != BANDS[self.expected_band]:
            raise ValueError("expected_score_range does not match expected_band")
        expected_suffix = chr(ord("A") + self.expected_band)
        if not self.variant_id.endswith(expected_suffix):
            raise ValueError("variant suffix does not match expected_band")
        if self.variant_id[3:6] != self.record_id[4:7]:
            raise ValueError("variant id does not match record_id")
        return self


def load_validation_set(
    path: str = VALIDATION_SET,
) -> list[ActionabilityValidationDraft]:
    with open(path, encoding="utf-8") as handle:
        return [ActionabilityValidationDraft.model_validate_json(line)
                for line in handle if line.strip()]


def validate_set(rows: list[ActionabilityValidationDraft]) -> list[str]:
    problems: list[str] = []
    if len(rows) != EXPECTED_VARIANTS:
        problems.append(f"expected {EXPECTED_VARIANTS} variants, found {len(rows)}")

    variant_ids = [row.variant_id for row in rows]
    if len(variant_ids) != len(set(variant_ids)):
        problems.append("variant ids are not unique")
    replies = [row.draft_reply for row in rows]
    if len(replies) != len(set(replies)):
        problems.append("draft replies are not unique")

    bands = Counter(row.expected_band for row in rows)
    if bands != Counter({0: 6, 1: 6, 2: 6, 3: 6}):
        problems.append(f"expected six examples in every band, found {dict(bands)}")

    by_record: dict[str, set[int]] = defaultdict(set)
    for row in rows:
        by_record[row.record_id].add(row.expected_band)
    if len(by_record) != EXPECTED_RECORDS:
        problems.append(f"expected {EXPECTED_RECORDS} source records, found {len(by_record)}")
    for record_id, record_bands in by_record.items():
        if record_bands != {0, 1, 2, 3}:
            problems.append(f"{record_id} does not cover all four bands")
    return problems


def main() -> int:
    rows = load_validation_set()
    problems = validate_set(rows)
    if problems:
        for problem in problems:
            print(problem)
        return 1
    print(f"{len(rows)} variants across {len({row.record_id for row in rows})} "
          "enquiries; 6 examples in each actionability band")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
