"""The contract itself: what the enums admit and what the fields refuse."""

import pytest
from pydantic import ValidationError

from src.schema import CaseType, DraftOutput, Priority, TriageOutput

VALID_TRIAGE = {"case_type": "CLAIM", "priority": "URGENT", "confidence": 0.82}


def test_valid_triage_payload_validates():
    result = TriageOutput.model_validate(VALID_TRIAGE)
    assert result.case_type is CaseType.CLAIM
    assert result.priority is Priority.URGENT
    assert result.confidence == 0.82


def test_case_type_enum_is_closed():
    assert {c.value for c in CaseType} == {
        "POLICY_QUERY",
        "PREMIUM_BILLING",
        "ADDRESS_CHANGE",
        "CLAIM",
        "COMPLAINT",
        "OTHER",
    }


def test_priority_enum_is_closed():
    assert {p.value for p in Priority} == {"URGENT", "NORMAL", "LOW"}


def test_unknown_case_type_is_rejected_not_coerced_to_other():
    with pytest.raises(ValidationError):
        TriageOutput.model_validate({**VALID_TRIAGE, "case_type": "BILLING_DISPUTE"})


def test_lowercase_enum_value_is_rejected():
    with pytest.raises(ValidationError):
        TriageOutput.model_validate({**VALID_TRIAGE, "priority": "urgent"})


@pytest.mark.parametrize("missing", ["case_type", "priority", "confidence"])
def test_missing_triage_field_is_rejected(missing):
    payload = {k: v for k, v in VALID_TRIAGE.items() if k != missing}
    with pytest.raises(ValidationError):
        TriageOutput.model_validate(payload)


@pytest.mark.parametrize("confidence", [-0.01, 1.01, 42])
def test_confidence_outside_zero_to_one_is_rejected(confidence):
    with pytest.raises(ValidationError):
        TriageOutput.model_validate({**VALID_TRIAGE, "confidence": confidence})


def test_extra_field_is_rejected_rather_than_dropped():
    with pytest.raises(ValidationError):
        TriageOutput.model_validate({**VALID_TRIAGE, "reasoning": "because"})


def test_triage_output_is_immutable():
    result = TriageOutput.model_validate(VALID_TRIAGE)
    with pytest.raises(ValidationError):
        result.confidence = 0.99


def test_valid_draft_payload_validates():
    result = DraftOutput.model_validate(
        {"summary": "Customer disputes a premium increase.", "draft_reply": "Dear ..."}
    )
    assert result.summary.startswith("Customer")


@pytest.mark.parametrize("missing", ["summary", "draft_reply"])
def test_missing_draft_field_is_rejected(missing):
    payload = {"summary": "s", "draft_reply": "r"}
    del payload[missing]
    with pytest.raises(ValidationError):
        DraftOutput.model_validate(payload)


@pytest.mark.parametrize("field", ["summary", "draft_reply"])
def test_empty_draft_field_is_rejected(field):
    payload = {"summary": "s", "draft_reply": "r", field: ""}
    with pytest.raises(ValidationError):
        DraftOutput.model_validate(payload)
