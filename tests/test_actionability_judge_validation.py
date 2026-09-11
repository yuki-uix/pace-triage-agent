import hashlib

from evals.actionability_judge_validation import input_sha256


def test_actionability_paid_run_inputs_are_traceable(tmp_path):
    source = tmp_path / "input.jsonl"
    source.write_bytes(b"frozen actionability input\n")

    assert input_sha256((source,)) == {
        source.as_posix(): hashlib.sha256(
            b"frozen actionability input\n"
        ).hexdigest()
    }


def test_missing_optional_blind_review_is_not_hashed(tmp_path):
    missing = tmp_path / "missing.jsonl"
    assert input_sha256((missing,)) == {}
