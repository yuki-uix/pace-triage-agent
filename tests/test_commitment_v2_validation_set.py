from src.commitment_v2_validation import load_validation_set, validate_set


def test_commitment_v2_set_is_balanced_and_evidence_frozen():
    rows = load_validation_set()
    assert len(rows) == 24
    assert validate_set(rows) == []


def test_commitment_v2_set_rejects_stale_evidence_ids():
    rows = load_validation_set()
    changed = rows[0].model_copy(update={"evidence_ids": ("STALE",)})
    problems = validate_set([changed, *rows[1:]])
    assert any("evidence ids differ" in problem for problem in problems)
