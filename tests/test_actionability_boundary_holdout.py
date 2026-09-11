from src.actionability_boundary_validation import load_validation_set, validate_set


HOLDOUT = "data/actionability_boundary_holdout_v1.jsonl"
DEVELOPMENT = "data/actionability_boundary_set_v4.jsonl"


def test_holdout_is_balanced_and_valid():
    assert validate_set(load_validation_set(HOLDOUT)) == []


def test_holdout_enquiries_are_disjoint_from_boundary_development_set():
    holdout = {row.record_id for row in load_validation_set(HOLDOUT)}
    development = {row.record_id for row in load_validation_set(DEVELOPMENT)}
    assert len(holdout) == 9
    assert holdout.isdisjoint(development)
