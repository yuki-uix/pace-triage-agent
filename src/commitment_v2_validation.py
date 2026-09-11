"""Contract and integrity checks for commitment-groundedness v2 data."""

from __future__ import annotations

from collections import Counter, defaultdict

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator

from src.draft_evidence import draft_evidence
from src.quotas import load_enquiries


VALIDATION_SET = "data/commitment_v2_validation_set.jsonl"
BANDS = ((0, 2), (3, 5), (6, 8), (9, 10))
EXPECTED_RECORDS = 6
EXPECTED_VARIANTS = 24


class CommitmentV2ValidationDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    variant_id: StrictStr = Field(pattern=r"^CV2-\d{3}-[A-D]$")
    record_id: StrictStr = Field(pattern=r"^ENQ-\d{3}$")
    expected_band: StrictInt = Field(ge=0, le=3)
    expected_score_range: tuple[StrictInt, StrictInt]
    draft_reply: StrictStr = Field(min_length=1)
    evidence_ids: tuple[StrictStr, ...] = Field(min_length=1)
    fault_tags: tuple[StrictStr, ...] = Field(min_length=1)
    rationale: StrictStr = Field(min_length=1)

    @model_validator(mode="after")
    def _band_and_id_agree(self) -> "CommitmentV2ValidationDraft":
        if self.expected_score_range != BANDS[self.expected_band]:
            raise ValueError("expected_score_range does not match expected_band")
        if not self.variant_id.endswith(chr(ord("A") + self.expected_band)):
            raise ValueError("variant suffix does not match expected_band")
        if self.variant_id[4:7] != self.record_id[4:7]:
            raise ValueError("variant id does not match record_id")
        return self


def load_validation_set(path: str = VALIDATION_SET) -> list[CommitmentV2ValidationDraft]:
    with open(path, encoding="utf-8") as handle:
        return [CommitmentV2ValidationDraft.model_validate_json(line)
                for line in handle if line.strip()]


def validate_set(rows: list[CommitmentV2ValidationDraft]) -> list[str]:
    problems: list[str] = []
    if len(rows) != EXPECTED_VARIANTS:
        problems.append(f"expected {EXPECTED_VARIANTS} variants, found {len(rows)}")
    if len({row.variant_id for row in rows}) != len(rows):
        problems.append("variant ids are not unique")
    if len({row.draft_reply for row in rows}) != len(rows):
        problems.append("draft replies are not unique")
    bands = Counter(row.expected_band for row in rows)
    if bands != Counter({0: 6, 1: 6, 2: 6, 3: 6}):
        problems.append(f"expected six examples in every band, found {dict(bands)}")

    enquiries = {row.id: row for row in load_enquiries()}
    by_record: dict[str, set[int]] = defaultdict(set)
    for row in rows:
        by_record[row.record_id].add(row.expected_band)
        enquiry = enquiries.get(row.record_id)
        if enquiry is None:
            problems.append(f"unknown record id: {row.record_id}")
            continue
        selected = draft_evidence(f"{enquiry.subject}\n{enquiry.body}").ids
        if row.evidence_ids != selected:
            problems.append(
                f"{row.variant_id} evidence ids differ from deterministic selection: "
                f"{row.evidence_ids!r} != {selected!r}"
            )
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
        print("\n".join(problems))
        return 1
    print(f"{len(rows)} variants across {len({row.record_id for row in rows})} "
          "enquiries; 6 examples in each commitment-v2 band")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
