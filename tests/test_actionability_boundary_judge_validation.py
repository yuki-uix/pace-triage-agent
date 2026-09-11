from evals.actionability_boundary_judge_validation import (
    acceptance,
    pair_ordering,
    paths_for_run,
)


def _item(pair_id, target, score):
    return {"pair_id": pair_id, "target_score": target, "judge_score": score}


def test_pair_ordering_uses_strict_continuous_scores():
    items = []
    for prefix, boundary in (("a", (2, 3)), ("b", (5, 6)), ("c", (8, 9))):
        for index in range(3):
            pair = f"{prefix}{index}"
            items += [_item(pair, boundary[0], 0.4),
                      _item(pair, boundary[1], 0.5 if index < 2 else 0.4)]
    result = pair_ordering(items)
    assert all(value == {"ordered": 2, "total": 3}
               for value in result["by_boundary"].values())


def test_acceptance_requires_every_preregistered_condition():
    result = {
        "items": [{}] * 18,
        "failures": [],
        "usage": {"thinking_disabled_retries": 0, "with_logprobs": 18},
        "agreement": {
            "exact_band_rate": 14 / 18,
            "quadratic_weighted_kappa": 0.80,
            "within_one_band_rate": 1.0,
        },
        "pair_ordering": {"by_boundary": {
            "2/3": {"ordered": 2, "total": 3},
            "5/6": {"ordered": 2, "total": 3},
            "8/9": {"ordered": 2, "total": 3},
        }},
    }
    assert acceptance(result)["passed"] is True
    result["agreement"]["exact_band_rate"] = 13 / 18
    assert acceptance(result)["passed"] is False


def test_holdout_mode_binds_the_untouched_dataset_and_plan():
    paths = paths_for_run(True)
    assert paths["dataset"].name == "actionability_boundary_holdout_v1.jsonl"
    assert paths["plan"].name == "actionability-holdout-validation-plan.md"
    assert paths["out"].as_posix().startswith(".local/actionability_holdout_v1/")
