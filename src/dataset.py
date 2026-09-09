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


class _Identified(BaseModel):
    """Shared id discipline. Both halves of a record must agree on it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: StrictStr

    @model_validator(mode="after")
    def _id_is_well_formed(self) -> "_Identified":
        if not ID_PATTERN.match(self.id):
            raise ValueError(f"id must look like ENQ-001, got {self.id!r}")
        return self


class Enquiry(_Identified):
    """What the pipeline is allowed to see: an id and an email.

    The labels live in a different file. That is the point — a prompt cannot
    accidentally include ground truth that is not in the object it was built
    from, and "the pipeline does not read the labels" stops being a discipline
    someone has to maintain and becomes a property of the data layout.
    """

    subject: StrictStr = Field(min_length=1)
    body: StrictStr = Field(min_length=1)


class GoldenLabel(_Identified):
    """The answers. Frozen and tagged; see `data/labeling_guide.md`."""

    expected_type: CaseType
    expected_priority: Priority
    acceptable_types: tuple[CaseType, ...] = ()
    tags: frozenset[Tag] = frozenset()

    must_include: tuple[StrictStr, ...] = ()
    must_not_assert: tuple[StrictStr, ...] = ()
    label_note: StrictStr | None = None

    @property
    def refuses(self) -> bool:
        return Tag.REFUSAL in self.tags

    @property
    def carries_injection(self) -> bool:
        return Tag.INJECTION in self.tags

    @model_validator(mode="after")
    def _acceptable_types_are_well_formed(self) -> EnquiryRecord:
        """Every mixed-topic record is ambiguous; not every ambiguous record is mixed.

        `acceptable_types` was originally admissible only on MIXED_TOPIC records.
        Repeated blind relabelling then found a record that is not two topics at
        all — a fraud report that also asks whether the policy is still in force —
        which a second labeller read differently in every run. Ambiguity there is
        a property of the category boundary, not of the email having two subjects,
        and the guide says such a record should be reported as ambiguous rather
        than silently scored wrong.

        Still enforced: a MIXED_TOPIC record must list alternatives, the planned
        label must be among them, and any record claiming ambiguity must say why.
        Handing out `acceptable_types` freely would inflate lenient accuracy and
        destroy the meaning of the gap between the strict and lenient numbers.
        """
        if Tag.MIXED_TOPIC in self.tags and not self.acceptable_types:
            raise ValueError("a MIXED_TOPIC record must list acceptable_types")
        if self.acceptable_types and self.expected_type not in self.acceptable_types:
            raise ValueError("expected_type must be among acceptable_types")
        if self.acceptable_types and not self.label_note:
            raise ValueError("a record claiming ambiguity must record why")
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


class EnquiryRecord(GoldenLabel):
    """The joined view: an enquiry and its labels together.

    Generation, the quota check and the metrics all want both halves. Only the
    pipeline is restricted to `Enquiry`, and only because it is the one caller
    that must not see the answers.
    """

    subject: StrictStr = Field(min_length=1)
    body: StrictStr = Field(min_length=1)

    def enquiry(self) -> Enquiry:
        return Enquiry(id=self.id, subject=self.subject, body=self.body)

    def label(self) -> GoldenLabel:
        return GoldenLabel(**{
            field: getattr(self, field) for field in GoldenLabel.model_fields
        })

    @classmethod
    def join(cls, enquiry: Enquiry, label: GoldenLabel) -> "EnquiryRecord":
        if enquiry.id != label.id:
            raise ValueError(f"id mismatch: {enquiry.id} vs {label.id}")
        return cls(subject=enquiry.subject, body=enquiry.body,
                   **{f: getattr(label, f) for f in GoldenLabel.model_fields})
