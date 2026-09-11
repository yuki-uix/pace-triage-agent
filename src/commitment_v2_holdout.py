"""Integrity checks for the disjoint commitment-v2 boundary holdout."""

from __future__ import annotations

from collections import Counter, defaultdict

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator

from src.draft_evidence import draft_evidence
from src.quotas import load_enquiries


HOLDOUT_SET = "data/commitment_v2_holdout_v1.jsonl"
TARGETS = (2, 3, 5, 6, 8, 9)
BOUNDARIES = ((2, 3), (5, 6), (8, 9))


def band_of(score: int) -> int:
    return 0 if score <= 2 else 1 if score <= 5 else 2 if score <= 8 else 3


class CommitmentV2HoldoutDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    variant_id: StrictStr = Field(pattern=r"^CH-\d{3}-(2|3|5|6|8|9)$")
    pair_id: StrictStr = Field(pattern=r"^CHP-\d{3}$")
    record_id: StrictStr = Field(pattern=r"^ENQ-\d{3}$")
    target_score: StrictInt
    expected_band: StrictInt = Field(ge=0, le=3)
    draft_reply: StrictStr = Field(min_length=1)
    evidence_ids: tuple[StrictStr, ...] = Field(min_length=1)
    boundary_change: StrictStr = Field(min_length=1)
    rationale: StrictStr = Field(min_length=1)

    @model_validator(mode="after")
    def _consistent(self) -> "CommitmentV2HoldoutDraft":
        if self.target_score not in TARGETS or self.expected_band != band_of(self.target_score):
            raise ValueError("target score and expected band disagree")
        number = self.record_id[4:7]
        if self.variant_id[3:6] != number or self.pair_id[4:7] != number:
            raise ValueError("variant, pair and record ids disagree")
        if not self.variant_id.endswith(f"-{self.target_score}"):
            raise ValueError("variant suffix and target score disagree")
        return self


def load_holdout(path: str = HOLDOUT_SET) -> list[CommitmentV2HoldoutDraft]:
    with open(path, encoding="utf-8") as handle:
        return [CommitmentV2HoldoutDraft.model_validate_json(line)
                for line in handle if line.strip()]


def validate_holdout(rows: list[CommitmentV2HoldoutDraft]) -> list[str]:
    problems = []
    if len(rows) != 18:
        problems.append(f"expected 18 variants, found {len(rows)}")
    if len({row.variant_id for row in rows}) != len(rows):
        problems.append("variant ids are not unique")
    if Counter(row.target_score for row in rows) != Counter({score: 3 for score in TARGETS}):
        problems.append("expected three examples at every target score")
    enquiries = {row.id: row for row in load_enquiries()}
    pairs: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        pairs[row.pair_id].append(row.target_score)
        enquiry = enquiries.get(row.record_id)
        if enquiry is None:
            problems.append(f"unknown record id: {row.record_id}")
            continue
        selected = draft_evidence(f"{enquiry.subject}\n{enquiry.body}").ids
        if row.evidence_ids != selected:
            problems.append(f"{row.variant_id} has stale evidence ids")
    if Counter(tuple(sorted(scores)) for scores in pairs.values()) != Counter(
        {boundary: 3 for boundary in BOUNDARIES}
    ):
        problems.append("expected three complete pairs at every boundary")
    return problems


def main() -> int:
    rows = load_holdout()
    problems = validate_holdout(rows)
    if problems:
        print("\n".join(problems))
        return 1
    print("18 variants in 9 disjoint pairs; 3 pairs at each commitment-v2 boundary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
