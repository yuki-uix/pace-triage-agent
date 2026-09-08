"""The dataset record contract.

`data/enquiries.jsonl` and `data/golden.jsonl` are the benchmark. A record that
does not validate here never enters either file, because a benchmark with
undefendable labels is not a benchmark.

Several rules from `data/labeling_guide.md` are enforced here rather than left
as prose. The guide says which rules a labeller is most likely to get wrong;
the ones that can be checked mechanically are checked.
"""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, StrictStr, model_validator

from src.schema import CaseType, Priority

ID_PATTERN = re.compile(r"^ENQ-\d{3}$")


class Tag(str, Enum):
    """Design dimensions from `docs/03-data-spec.md`. A record may carry several.

    These are properties the record was *built* to have, not observations made
    afterwards. They drive both the quota check and the evaluation branching:
    REFUSAL and INJECTION records are scored differently (`docs/02-metrics.md`).
    """

    MIXED_TOPIC = "MIXED_TOPIC"
    ANGRY = "ANGRY"
    MISSING_INFO = "MISSING_INFO"
    REFUSAL = "REFUSAL"
    INJECTION = "INJECTION"
    NOISY = "NOISY"


class EnquiryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: StrictStr
    subject: StrictStr = Field(min_length=1)
    body: StrictStr = Field(min_length=1)

    expected_type: CaseType
    expected_priority: Priority
    acceptable_types: tuple[CaseType, ...] = ()
    tags: frozenset[Tag] = frozenset()

    must_include: tuple[StrictStr, ...] = ()
    must_not_assert: tuple[StrictStr, ...] = ()
    label_note: StrictStr | None = None

    @model_validator(mode="after")
    def _id_is_well_formed(self) -> EnquiryRecord:
        if not ID_PATTERN.match(self.id):
            raise ValueError(f"id must look like ENQ-001, got {self.id!r}")
        return self

    @model_validator(mode="after")
    def _acceptable_types_track_the_mixed_topic_tag(self) -> EnquiryRecord:
        """Guide rule 2: only mixed-topic records have defensible alternatives.

        Scoring lenient accuracy against `acceptable_types` on a record that is
        not genuinely ambiguous would inflate the lenient number and destroy the
        meaning of the gap between the two accuracies.
        """
        mixed = Tag.MIXED_TOPIC in self.tags
        if mixed and not self.acceptable_types:
            raise ValueError("a MIXED_TOPIC record must list acceptable_types")
        if self.acceptable_types and not mixed:
            raise ValueError("acceptable_types is only valid on a MIXED_TOPIC record")
        if self.acceptable_types and self.expected_type not in self.acceptable_types:
            raise ValueError("expected_type must be among acceptable_types")
        return self

    @model_validator(mode="after")
    def _mixed_topic_records_cite_their_adjudication(self) -> EnquiryRecord:
        """Guide rule 2 again: ambiguity must be adjudicated, not asserted."""
        if Tag.MIXED_TOPIC in self.tags and not self.label_note:
            raise ValueError("a MIXED_TOPIC record must record why the label won")
        return self

    @model_validator(mode="after")
    def _angry_and_urgent_needs_a_reason(self) -> EnquiryRecord:
        """Guide: "Angry tone alone does not make an enquiry URGENT."

        The guide names this as the rule both a model and a human labeller are
        most likely to violate. A record that is angry *and* URGENT must state
        the consequence or deadline that earned the URGENT, so the label can be
        checked rather than taken on trust.
        """
        if (
            Tag.ANGRY in self.tags
            and self.expected_priority is Priority.URGENT
            and not self.label_note
        ):
            raise ValueError(
                "an ANGRY + URGENT record must state in label_note what makes it "
                "urgent besides tone"
            )
        return self

    @model_validator(mode="after")
    def _refusal_records_name_their_bait(self) -> EnquiryRecord:
        """A refusal case exists to bait a specific fabrication. Name it."""
        if Tag.REFUSAL in self.tags and not self.must_not_assert:
            raise ValueError(
                "a REFUSAL record must list what the reply must not assert"
            )
        return self
