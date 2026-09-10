"""The judge meta-evaluation, and its refusal to invent the human column."""

import json
import math
from types import SimpleNamespace

import pytest

from evals.meta_evaluation import (
    _score,
    BANDS,
    METRICS,
    agreement,
    band_of,
    bands_for,
    build_worksheet,
    judge_band,
    label_progress,
    load_human_labels,
    select,
)
from evals.metrics.judged import (
    COMMITMENT_RUBRIC,
    COMMITMENT_STEPS,
    DOMAIN_RUBRIC,
    DOMAIN_STEPS,
    SUMMARY_RUBRIC,
    SUMMARY_STEPS,
    TONE_RUBRIC,
    TONE_STEPS,
)
from src.dataset import Tag
from src.judge import DashScopeJudge, JudgeUsage
from src.quotas import load_records


# ------------------------------------------------------------------- banding

@pytest.mark.parametrize("score,expected", [
    (0, 0), (2, 0), (3, 1), (5, 1), (6, 2), (8, 2), (9, 3), (10, 3),
])
def test_band_boundaries(score, expected):
    assert band_of(score) == expected


@pytest.mark.parametrize("score", [-1, 11])
def test_a_score_outside_the_scale_raises(score):
    with pytest.raises(ValueError):
        band_of(score)


def test_the_judges_decimal_is_banded_the_same_way():
    """A person labels a band; comparing a decimal to it needs the same scale."""
    assert judge_band(1.0) == 3
    assert judge_band(0.0) == 0
    assert judge_band(0.55) == band_of(6)


@pytest.mark.parametrize("metric", ["tone match", "summary quality"])
def test_metric_specific_band_boundaries_match_the_rubric(metric):
    assert bands_for(metric) == ((0, 3), (4, 6), (7, 8), (9, 10))
    assert band_of(3, metric) == 0
    assert band_of(6, metric) == 1
    assert band_of(7, metric) == 2


# ---------------------------------------------------------------- agreement

def test_perfect_agreement():
    result = agreement([3, 2, 1, 0], [3, 2, 1, 0], "tone match")
    assert result.kappa == pytest.approx(1.0)
    assert result.exact == 1.0
    assert result.within_one == 1.0


def test_one_band_out_costs_less_than_three():
    """Quadratic weighting: the measure has to be ordinal to mean anything."""
    near = agreement([3, 3, 3, 0], [2, 3, 3, 0], "tone match")
    far = agreement([3, 3, 3, 0], [0, 3, 3, 0], "tone match")
    assert near.kappa > far.kappa


def test_within_one_band_is_reported_separately_from_exact():
    result = agreement([3, 2, 1], [2, 1, 0], "tone match")
    assert result.exact == 0.0
    assert result.within_one == 1.0


def test_mismatched_label_counts_raise():
    with pytest.raises(ValueError):
        agreement([1, 2], [1], "tone match")


def test_no_labels_raises_rather_than_reporting_zero():
    with pytest.raises(ValueError):
        agreement([], [], "tone match")


# ----------------------------------------------------------------- selection

def test_selection_is_deterministic():
    records = load_records()
    assert [r.id for r in select(records, 15)] == [r.id for r in select(records, 15)]


def test_selection_excludes_refusal_records():
    """They skip the draft-quality metrics, so the rows would have nothing to score."""
    for record in select(load_records(), 15):
        assert Tag.REFUSAL not in record.tags


def test_selection_spreads_across_case_types():
    chosen = select(load_records(), 15)
    assert len({r.expected_type for r in chosen}) == 6


# ----------------------------------------------------------------- worksheet

def rows():
    return [{"record_id": "ENQ-001", "enquiry": "Please update my address.",
             "summary": "Customer wants an address change.",
             "draft_reply": "Dear customer, we will update it."}]


def test_the_worksheet_carries_the_rubric_bands(tmp_path):
    path = build_worksheet(rows(), str(tmp_path / "w.md"))
    text = open(path, encoding="utf-8").read()
    for metric in METRICS:
        assert metric in text
    assert COMMITMENT_RUBRIC[0].expected_outcome[:40] in text


def test_the_worksheet_does_not_show_the_judges_scores(tmp_path):
    """An anchored human column measures the anchor, not the human."""
    path = build_worksheet(rows(), str(tmp_path / "w.md"))
    text = open(path, encoding="utf-8").read().lower()
    assert "judge" not in text.split("## commitment groundedness")[1]


def test_the_worksheet_contains_the_draft_and_the_summary(tmp_path):
    path = build_worksheet(rows(), str(tmp_path / "w.md"))
    text = open(path, encoding="utf-8").read()
    assert "we will update it" in text
    assert "Customer wants an address change." in text


# -------------------------------------------------------------- human labels

def test_unfilled_rows_are_skipped(tmp_path):
    path = tmp_path / "labels.jsonl"
    path.write_text(
        json.dumps({"record_id": "ENQ-001", "metric": "tone match", "human": None})
        + "\n"
        + json.dumps({"record_id": "ENQ-002", "metric": "tone match", "human": 7})
        + "\n", encoding="utf-8")

    labels = load_human_labels(str(path))
    assert labels == {("ENQ-002", "tone match"): 7}


def test_a_label_outside_the_scale_raises(tmp_path):
    path = tmp_path / "labels.jsonl"
    path.write_text(json.dumps(
        {"record_id": "ENQ-001", "metric": "tone match", "human": 11}) + "\n",
        encoding="utf-8")
    with pytest.raises(ValueError):
        load_human_labels(str(path))


def test_label_progress_does_not_need_judge_scores(tmp_path):
    path = tmp_path / "labels.jsonl"
    path.write_text(
        json.dumps({"record_id": "ENQ-001", "metric": "tone match", "human": 7})
        + "\n"
        + json.dumps({"record_id": "ENQ-002", "metric": "tone match", "human": None})
        + "\n", encoding="utf-8")

    progress = label_progress(str(path))
    assert progress.total == 2
    assert progress.completed == 1
    assert progress.missing == (("ENQ-002", "tone match"),)


def test_duplicate_human_label_rows_are_rejected(tmp_path):
    row = json.dumps({"record_id": "ENQ-001", "metric": "tone match", "human": 7})
    path = tmp_path / "labels.jsonl"
    path.write_text(row + "\n" + row + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate"):
        label_progress(str(path))


def test_unknown_human_label_metric_is_rejected(tmp_path):
    path = tmp_path / "labels.jsonl"
    path.write_text(json.dumps({
        "record_id": "ENQ-001", "metric": "overall vibes", "human": 7,
    }) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unknown metric"):
        label_progress(str(path))


def test_score_refuses_partial_labels_before_reading_judge_output(
        tmp_path, capsys):
    labels = tmp_path / "labels.jsonl"
    labels.write_text(json.dumps({
        "record_id": "ENQ-001", "metric": "tone match", "human": None,
    }) + "\n", encoding="utf-8")
    judge = tmp_path / "judge.json"
    judge.write_text("not json and must not be read", encoding="utf-8")

    assert _score(labels, judge) == 1
    assert "agreement remains hidden" in capsys.readouterr().out


def test_score_refuses_missing_judge_rows(tmp_path, capsys):
    labels = tmp_path / "labels.jsonl"
    labels.write_text(json.dumps({
        "record_id": "ENQ-001", "metric": "tone match", "human": 7,
    }) + "\n", encoding="utf-8")
    judge = tmp_path / "judge.json"
    judge.write_text(json.dumps({
        "judge_model": "test-judge", "scores": {},
    }), encoding="utf-8")

    assert _score(labels, judge) == 2
    assert "missing 1 prepared label" in capsys.readouterr().out


# ------------------------------------------------------- rubrics and judging

@pytest.mark.parametrize(
    "steps", [COMMITMENT_STEPS, TONE_STEPS, SUMMARY_STEPS, DOMAIN_STEPS]
)
def test_evaluation_steps_are_specific_not_boilerplate(steps):
    """Auto-generated from a criteria string means an unexamined rubric.

    Length is not the property - "Do not reward or penalise length on its own"
    is 44 characters and is exactly the kind of instruction that has to be
    written by someone who watched the judge get it wrong. What distinguishes a
    hand-written set is that it says what to do, several times, in the
    vocabulary of this task.
    """
    assert len(steps) >= 4
    assert sum(len(step) for step in steps) > 500
    assert not any(step.strip().lower().startswith(("evaluate whether", "assess the"))
                   for step in steps), "reads as an auto-generated criteria echo"


@pytest.mark.parametrize(
    "rubric", [COMMITMENT_RUBRIC, TONE_RUBRIC, SUMMARY_RUBRIC, DOMAIN_RUBRIC]
)
def test_rubric_bands_cover_the_whole_scale_without_gaps(rubric):
    covered = sorted(band.score_range for band in rubric)
    assert covered[0][0] == 0
    assert covered[-1][1] == 10
    for (_, previous_high), (next_low, _) in zip(covered, covered[1:]):
        assert next_low == previous_high + 1


def test_rubric_bands_match_the_metric_specific_banding_used_for_agreement():
    """The worksheet, the rubric and the kappa must all use one scale."""
    for metric, rubric in (
        ("commitment groundedness", COMMITMENT_RUBRIC),
        ("tone match", TONE_RUBRIC),
        ("summary quality", SUMMARY_RUBRIC),
        ("domain correctness", DOMAIN_RUBRIC),
    ):
        assert tuple(band.score_range for band in rubric) == bands_for(metric)


# ------------------------------------------------------------- judge wrapper

class FakeCompletions:
    def __init__(self, with_logprobs: bool):
        self.with_logprobs = with_logprobs

    def create(self, **kwargs):
        logprobs = None
        if self.with_logprobs and kwargs.get("logprobs"):
            logprobs = SimpleNamespace(content=[SimpleNamespace(
                token="4", logprob=math.log(0.9),
                top_logprobs=[SimpleNamespace(token="4", logprob=math.log(0.9))])])
        return SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content='{"score": 4, "reason": "ok"}'),
                logprobs=logprobs)],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5,
                                  completion_tokens_details=SimpleNamespace(
                                      reasoning_tokens=2)))


def judge(monkeypatch, with_logprobs: bool) -> DashScopeJudge:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "x")
    monkeypatch.setenv("DASHSCOPE_BASE_URL", "http://localhost")
    monkeypatch.setenv("JUDGE_MODEL", "glm-5.2")
    instance = DashScopeJudge(usage=JudgeUsage())
    instance._client = SimpleNamespace(chat=SimpleNamespace(
        completions=FakeCompletions(with_logprobs)))
    return instance


def test_continuous_scoring_is_recorded_when_logprobs_arrive(monkeypatch):
    instance = judge(monkeypatch, with_logprobs=True)
    instance.generate_raw_response("prompt", top_logprobs=5)
    assert instance.usage.continuous_scoring_rate == 1.0


def test_the_degradation_is_visible_when_logprobs_do_not_arrive(monkeypatch):
    """GEval falls back to the integer silently; the rate is what exposes it."""
    instance = judge(monkeypatch, with_logprobs=False)
    instance.generate_raw_response("prompt", top_logprobs=5)
    assert instance.usage.continuous_scoring_rate == 0.0
    assert instance.usage.calls == 1


def test_the_judge_records_reasoning_tokens(monkeypatch):
    instance = judge(monkeypatch, with_logprobs=True)
    instance.generate("prompt")
    assert instance.usage.reasoning_tokens == 2
