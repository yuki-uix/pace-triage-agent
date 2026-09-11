from src.actionability_boundary_validation import (
    BOUNDARIES,
    TARGET_SCORES,
    load_validation_set,
    validate_set,
)


def test_committed_boundary_set_is_balanced_and_valid():
    assert validate_set(load_validation_set()) == []


def test_each_score_and_boundary_has_three_examples():
    rows = load_validation_set()
    for score in TARGET_SCORES:
        assert sum(row.target_score == score for row in rows) == 3
    for lower, upper in BOUNDARIES:
        pairs = {
            row.pair_id for row in rows if row.target_score in (lower, upper)
        }
        assert len(pairs) == 3
        for pair_id in pairs:
            assert {row.target_score for row in rows if row.pair_id == pair_id} == {
                lower, upper
            }


def test_validator_detects_a_broken_pair():
    rows = load_validation_set()
    changed = [row.model_copy(update={"pair_id": "ABP-002"})
               if row.variant_id == "AB-001-3" else row for row in rows]
    problems = validate_set(changed)
    assert "ABP-001 is not one complete boundary pair" in problems
