from src.actionability_validation import (
    BANDS,
    load_validation_set,
    validate_set,
)


def test_committed_actionability_validation_set_is_balanced_and_valid():
    assert validate_set(load_validation_set()) == []


def test_every_source_record_has_one_variant_in_every_band():
    rows = load_validation_set()
    record_ids = {row.record_id for row in rows}
    for record_id in record_ids:
        record_rows = [row for row in rows if row.record_id == record_id]
        assert {row.expected_band for row in record_rows} == {0, 1, 2, 3}
        assert {row.expected_score_range for row in record_rows} == set(BANDS)


def test_validator_rejects_a_missing_band_for_one_record():
    rows = load_validation_set()
    changed = [row.model_copy(update={"record_id": "ENQ-001"})
               if row.variant_id == "AV-008-D" else row for row in rows]
    problems = validate_set(changed)
    assert "ENQ-008 does not cover all four bands" in problems


def test_variants_and_replies_are_unique():
    rows = load_validation_set()
    assert len({row.variant_id for row in rows}) == len(rows)
    assert len({row.draft_reply for row in rows}) == len(rows)
