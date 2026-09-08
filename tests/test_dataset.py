"""The record contract, and the labeling-guide rules it makes executable."""

import pytest
from pydantic import ValidationError

from src.dataset import EnquiryRecord, Tag
from src.schema import CaseType, Priority

BASE = {
    "id": "ENQ-001",
    "subject": "Address change",
    "body": "I have moved and need to update my address.",
    "expected_type": "ADDRESS_CHANGE",
    "expected_priority": "NORMAL",
}


def record(**overrides) -> EnquiryRecord:
    return EnquiryRecord.model_validate({**BASE, **overrides})


def test_minimal_record_validates():
    assert record().expected_type is CaseType.ADDRESS_CHANGE


@pytest.mark.parametrize("bad_id", ["ENQ-1", "enq-001", "001", "ENQ-0001", ""])
def test_id_must_be_well_formed(bad_id):
    with pytest.raises(ValidationError):
        record(id=bad_id)


def test_mixed_topic_record_must_list_acceptable_types():
    with pytest.raises(ValidationError, match="acceptable_types"):
        record(tags=["MIXED_TOPIC"], label_note="address change is the work item")


def test_acceptable_types_without_the_mixed_topic_tag_is_rejected():
    """Otherwise lenient accuracy inflates on records that are not ambiguous."""
    with pytest.raises(ValidationError, match="only valid on a MIXED_TOPIC"):
        record(acceptable_types=["ADDRESS_CHANGE", "COMPLAINT"])


def test_expected_type_must_be_among_the_acceptable_types():
    with pytest.raises(ValidationError, match="among acceptable_types"):
        record(
            tags=["MIXED_TOPIC"],
            acceptable_types=["CLAIM", "COMPLAINT"],
            label_note="shorter regulatory clock wins",
        )


def test_mixed_topic_record_must_record_why_the_label_won():
    with pytest.raises(ValidationError, match="why the label won"):
        record(tags=["MIXED_TOPIC"], acceptable_types=["ADDRESS_CHANGE", "COMPLAINT"])


def test_valid_mixed_topic_record():
    result = record(
        tags=["MIXED_TOPIC"],
        acceptable_types=["ADDRESS_CHANGE", "COMPLAINT"],
        label_note="complaint is tone; the address change is the work item",
    )
    assert Tag.MIXED_TOPIC in result.tags


def test_angry_and_urgent_must_justify_the_urgency():
    """The guide names this as the rule most likely to be violated."""
    with pytest.raises(ValidationError, match="besides tone"):
        record(tags=["ANGRY"], expected_priority="URGENT")


def test_angry_and_urgent_is_fine_with_a_stated_consequence():
    result = record(
        tags=["ANGRY"],
        expected_priority="URGENT",
        label_note="policy lapses in 4 days if the payment failure is not resolved",
    )
    assert result.expected_priority is Priority.URGENT


def test_angry_and_normal_needs_no_note():
    assert record(tags=["ANGRY"]).label_note is None


def test_refusal_record_must_name_what_it_baits():
    with pytest.raises(ValidationError, match="must not assert"):
        record(tags=["REFUSAL"])


def test_valid_refusal_record():
    result = record(
        tags=["REFUSAL"],
        must_not_assert=("that the claim will be approved",),
    )
    assert Tag.REFUSAL in result.tags


def test_record_is_immutable():
    result = record()
    with pytest.raises(ValidationError):
        result.expected_priority = Priority.URGENT


def test_unknown_tag_is_rejected():
    with pytest.raises(ValidationError):
        record(tags=["SARCASTIC"])


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        record(difficulty="hard")
