"""Contract checks for the predeclared actionability boundary challenge set."""

from __future__ import annotations

from collections import Counter, defaultdict

from pydantic import (
    BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator,
)


VALIDATION_SET = "data/actionability_boundary_set_v4.jsonl"
TARGET_SCORES = (2, 3, 5, 6, 8, 9)
BOUNDARIES = ((2, 3), (5, 6), (8, 9))
EXPECTED_RECORDS = 9
EXPECTED_VARIANTS = 18


def band_of(score: int) -> int:
    if score <= 2:
        return 0
    if score <= 5:
        return 1
    if score <= 8:
        return 2
    return 3


class ActionabilityBoundaryDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    variant_id: StrictStr = Field(pattern=r"^AB-\d{3}-(2|3|5|6|8|9)$")
    pair_id: StrictStr = Field(pattern=r"^ABP-\d{3}$")
    record_id: StrictStr = Field(pattern=r"^ENQ-\d{3}$")
    target_score: StrictInt
    expected_band: StrictInt = Field(ge=0, le=3)
    draft_reply: StrictStr = Field(min_length=1)
    boundary_change: StrictStr = Field(min_length=1)
    rationale: StrictStr = Field(min_length=1)

    @model_validator(mode="after")
    def _ids_and_score_agree(self) -> "ActionabilityBoundaryDraft":
        if self.target_score not in TARGET_SCORES:
            raise ValueError("target_score is not a declared boundary score")
        if self.expected_band != band_of(self.target_score):
            raise ValueError("expected_band does not match target_score")
        if not self.variant_id.endswith(f"-{self.target_score}"):
            raise ValueError("variant suffix does not match target_score")
        if self.variant_id[3:6] != self.record_id[4:7]:
            raise ValueError("variant id does not match record_id")
        if self.pair_id[4:7] != self.record_id[4:7]:
            raise ValueError("pair id does not match record_id")
        return self


def load_validation_set(
    path: str = VALIDATION_SET,
) -> list[ActionabilityBoundaryDraft]:
    with open(path, encoding="utf-8") as handle:
        return [ActionabilityBoundaryDraft.model_validate_json(line)
                for line in handle if line.strip()]


def validate_set(rows: list[ActionabilityBoundaryDraft]) -> list[str]:
    problems: list[str] = []
    if len(rows) != EXPECTED_VARIANTS:
        problems.append(f"expected {EXPECTED_VARIANTS} variants, found {len(rows)}")

    ids = [row.variant_id for row in rows]
    if len(ids) != len(set(ids)):
        problems.append("variant ids are not unique")
    replies = [row.draft_reply for row in rows]
    if len(replies) != len(set(replies)):
        problems.append("draft replies are not unique")

    score_counts = Counter(row.target_score for row in rows)
    expected_counts = Counter({score: 3 for score in TARGET_SCORES})
    if score_counts != expected_counts:
        problems.append(
            f"expected three examples at every target score, found {dict(score_counts)}"
        )

    by_pair: dict[str, list[int]] = defaultdict(list)
    pair_records: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        by_pair[row.pair_id].append(row.target_score)
        pair_records[row.pair_id].add(row.record_id)
    if len(by_pair) != EXPECTED_RECORDS:
        problems.append(f"expected {EXPECTED_RECORDS} pairs, found {len(by_pair)}")
    for pair_id, scores in by_pair.items():
        if tuple(sorted(scores)) not in BOUNDARIES:
            problems.append(f"{pair_id} is not one complete boundary pair")
        if len(pair_records[pair_id]) != 1:
            problems.append(f"{pair_id} spans multiple enquiries")

    boundary_counts = Counter(tuple(sorted(scores)) for scores in by_pair.values())
    if boundary_counts != Counter({boundary: 3 for boundary in BOUNDARIES}):
        problems.append(
            f"expected three pairs at every boundary, found {dict(boundary_counts)}"
        )
    return problems


def main() -> int:
    rows = load_validation_set()
    problems = validate_set(rows)
    if problems:
        for problem in problems:
            print(problem)
        return 1
    print(
        "18 variants in 9 minimal pairs; 3 pairs at each of the "
        "2/3, 5/6 and 8/9 actionability boundaries"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
