import pytest
from pydantic import ValidationError

from src.judge_validation import (
    JudgeValidationDraft,
    load_validation_set,
    validate_set,
)
from src.quotas import load_enquiries


def test_validation_set_is_balanced_and_complete():
    assert validate_set(load_validation_set()) == []


def test_every_source_enquiry_exists_in_the_frozen_dataset():
    enquiry_ids = {row.id for row in load_enquiries()}
    assert {row.record_id for row in load_validation_set()} <= enquiry_ids


def test_high_band_examples_have_no_seeded_faults():
    rows = load_validation_set()
    assert all(not row.fault_tags for row in rows if row.expected_band == 3)
    assert all(row.fault_tags for row in rows if row.expected_band < 3)


def test_middle_bands_isolate_one_fault_and_low_band_has_multiple():
    rows = load_validation_set()
    assert all(len(row.fault_tags) == 1 for row in rows
               if row.expected_band in {1, 2})
    assert all(len(row.fault_tags) >= 2 for row in rows
               if row.expected_band == 0)


def test_band_range_and_variant_suffix_cannot_drift():
    row = load_validation_set()[0].model_dump(mode="json")
    row["expected_score_range"] = [0, 2]
    with pytest.raises(ValidationError, match="score_range"):
        JudgeValidationDraft.model_validate(row)


def test_variant_id_must_name_its_source_record():
    row = load_validation_set()[0].model_dump(mode="json")
    row["record_id"] = "ENQ-009"
    with pytest.raises(ValidationError, match="record_id"):
        JudgeValidationDraft.model_validate(row)


def test_unknown_evidence_is_reported():
    row = load_validation_set()[0].model_dump(mode="json")
    row["evidence_ids"] = ["MADE_UP_SOURCE"]
    changed = JudgeValidationDraft.model_validate(row)
    assert validate_set([changed])[-1] == "unknown evidence ids: MADE_UP_SOURCE"
