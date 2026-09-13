import json
from types import SimpleNamespace

import pytest

from evals.assignment_demo import (
    DEFAULT_DATASET,
    DEFAULT_GOLDEN,
    DEFAULT_MANIFEST,
    VERSION,
    main,
    render_report,
    review_rows,
    validate_demo,
    validate_resume,
)


def test_frozen_assignment_demo_is_valid_and_ordered():
    records, manifest = validate_demo(
        DEFAULT_DATASET, DEFAULT_MANIFEST, DEFAULT_GOLDEN)
    assert [record.id for record in records] == manifest["record_ids"]
    assert len(records) == 5


def test_demo_rejects_a_non_verbatim_enquiry(tmp_path):
    rows = DEFAULT_DATASET.read_text(encoding="utf-8").splitlines()
    payload = json.loads(rows[0])
    payload["subject"] += " edited"
    rows[0] = json.dumps(payload)
    changed = tmp_path / "changed.jsonl"
    changed.write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not a verbatim copy"):
        validate_demo(changed, DEFAULT_MANIFEST, DEFAULT_GOLDEN)


def test_review_template_requires_a_reason_for_a_preference(tmp_path):
    path = tmp_path / "review.jsonl"
    rows = review_rows(path, ["ENQ-009", "ENQ-021"])
    assert rows["ENQ-009"]["preferred"] is None
    changed = path.read_text(encoding="utf-8").replace(
        '"preferred": null', '"preferred": "baseline"', 1)
    path.write_text(changed, encoding="utf-8")
    with pytest.raises(ValueError, match="requires a reason"):
        review_rows(path, ["ENQ-009", "ENQ-021"])


def test_resume_refuses_a_different_model():
    expected = {"version": VERSION, "inputs": {"a": 1},
                "models": {"draft": "plus"}}
    existing = {**expected, "models": {"draft": "flash"}}
    with pytest.raises(ValueError, match="different models"):
        validate_resume(existing, expected)


def test_report_keeps_unscored_and_pending_values_visible():
    payload = {
        "claim_scope": "assignment proof of concept",
        "cases": [{"record_id": "ENQ-009", "variants": {
            "baseline": {"deterministic_scores": {
                "entity groundedness": {"score": 1.0}}, "judged_scores": {}},
            "evidence_backed": {"deterministic_scores": {},
                                "judged_scores": {}}},
            "human_review": {"preferred": None, "reason": None}}],
    }
    report = render_report(payload)
    assert "| ENQ-009 | baseline | 1.000 | —" in report
    assert "| ENQ-009 | — | — |" in report
    assert "| ENQ-009 | pending | pending |" in report


def test_runner_completes_pairs_and_resume_makes_no_paid_calls(
        tmp_path, monkeypatch):
    import evals.assignment_demo as demo

    calls = []
    judge_calls = []

    class Usage:
        def as_dict(self):
            return {"calls": len(judge_calls), "with_logprobs": len(judge_calls),
                    "prompt_tokens": 0, "completion_tokens": 0,
                    "reasoning_tokens": 0, "thinking_disabled_retries": 0,
                    "failures": []}

    class Judge:
        usage = Usage()

        def get_model_name(self):
            return "judge"

    class Metric:
        def measure(self, test_case, **kwargs):
            judge_calls.append(test_case.input)
            self.score = 0.8
            self.reason = "supported"

    def fake_run(client, config, record_id, subject, body, counters):
        calls.append((record_id, config.evidence_backed))
        return SimpleNamespace(
            case_type="CLAIM", priority="LOW", confidence=0.9,
            summary="Summary.", draft_reply="Draft.",
            evidence_ids=["SVC_CLAIM_01"] if config.evidence_backed else [],
            traces=[])

    monkeypatch.setattr(demo, "load_env", lambda: None)
    monkeypatch.setattr(demo, "OpenAI", lambda **kwargs: object())
    monkeypatch.setattr(demo, "DashScopeJudge", Judge)
    monkeypatch.setattr(demo, "build_analyzer", lambda: object())
    monkeypatch.setattr(demo, "run", fake_run)
    monkeypatch.setattr(demo, "deterministic_scores",
                        lambda record, output, analyzer: {})
    monkeypatch.setattr(demo, "commitment_groundedness_v2", lambda judge: Metric())
    monkeypatch.setattr(demo, "actionability", lambda judge: Metric())
    monkeypatch.setenv("TRIAGE_MODEL_A", "triage")
    monkeypatch.setenv("TRIAGE_MODEL_B", "draft")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setenv("DASHSCOPE_BASE_URL", "https://example.invalid/v1")

    out, review, report = (tmp_path / "result.json", tmp_path / "review.jsonl",
                           tmp_path / "report.md")
    args = ["assignment_demo", "--out", str(out), "--review", str(review),
            "--report", str(report)]
    assert main(args) == 0
    assert len(calls) == 10
    assert len(judge_calls) == 16  # the refusal pair skips both judged metrics
    assert json.loads(out.read_text())["status"] == "awaiting_human_review"

    assert main(args + ["--resume"]) == 0
    assert len(calls) == 10
    assert len(judge_calls) == 16
