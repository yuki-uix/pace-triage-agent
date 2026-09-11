import hashlib
import json

import pytest

from evals.commitment_v2_judge_validation import acceptance, input_sha256, load_blind_review
from evals.prepare_commitment_v2_blind_review import prepare


def test_paid_run_inputs_are_traceable(tmp_path):
    source = tmp_path / "input.jsonl"
    source.write_bytes(b"frozen evidence input\n")
    assert input_sha256((source,)) == {
        source.as_posix(): hashlib.sha256(b"frozen evidence input\n").hexdigest()
    }


def test_blind_review_must_be_complete(tmp_path):
    _, key = prepare(tmp_path)
    scores = tmp_path / "blind_agent_scores.jsonl"
    scores.write_text('{"blind_id":"CR-01","band":3,"reason":"ok"}\n')
    with pytest.raises(ValueError, match="24 blind ids"):
        load_blind_review(key, scores)


def test_blind_review_agreement_is_calculated(tmp_path):
    _, key_path = prepare(tmp_path)
    key = json.loads(key_path.read_text())["items"]
    scores = tmp_path / "blind_agent_scores.jsonl"
    scores.write_text("".join(json.dumps({
        "blind_id": row["blind_id"],
        "band": row["expected_band"],
        "reason": "independent evidence check",
    }) + "\n" for row in key))
    summary = load_blind_review(key_path, scores)
    assert summary["n"] == 24
    assert summary["exact_band_rate"] == 1.0


def test_acceptance_requires_both_judge_and_blind_review():
    strong = {
        "exact_band_rate": 21 / 24,
        "quadratic_weighted_kappa": 0.9,
        "within_one_band_rate": 1.0,
    }
    result = {
        "items": [{}] * 24,
        "failures": [],
        "usage": {"thinking_disabled_retries": 0, "with_logprobs": 24},
        "agreement": strong,
        "blind_review_agreement": strong,
    }
    assert acceptance(result)["passed"] is True
    result["blind_review_agreement"] = {**strong, "exact_band_rate": 19 / 24}
    assert acceptance(result)["passed"] is False
