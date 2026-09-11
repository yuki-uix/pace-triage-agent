from evals.commitment_v2_holdout_validation import acceptance, assignment_acceptance


def test_acceptance_requires_every_preregistered_gate():
    agreement = {"exact_band_rate": 15 / 18, "quadratic_weighted_kappa": 0.9,
                 "within_one_band_rate": 1.0}
    ordering = {"by_boundary": {str(i): {"ordered": 2, "total": 3}
                                for i in range(3)}}
    result = {"items": [{}] * 18, "failures": [],
              "usage": {"thinking_disabled_retries": 0, "with_logprobs": 18},
              "agreement": agreement, "blind_review_agreement": agreement,
              "pair_ordering": ordering, "blind_pair_ordering": ordering}
    assert acceptance(result)["passed"] is True
    result["usage"]["with_logprobs"] = 17
    assert acceptance(result)["passed"] is False


def test_assignment_acceptance_allows_adjacent_band_misses():
    judged = {"exact_band_rate": 13 / 18, "quadratic_weighted_kappa": 0.865,
              "within_one_band_rate": 1.0}
    blind = {"exact_band_rate": 15 / 18, "quadratic_weighted_kappa": 0.914,
             "within_one_band_rate": 1.0}
    ordering = {"by_boundary": {str(i): {"ordered": 2, "total": 3}
                                for i in range(3)}}
    result = {"items": [{}] * 18, "failures": [],
              "usage": {"with_logprobs": 18}, "agreement": judged,
              "blind_review_agreement": blind, "pair_ordering": ordering,
              "blind_pair_ordering": ordering}
    report = assignment_acceptance(result)
    assert report["passed"] is True
    assert report["profile"] == "assignment-poc-v1"
