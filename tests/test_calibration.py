"""Calibration arithmetic, and the honesty the table depends on."""

import math

import pytest

from evals.calibration import (
    EDGES,
    Bucket,
    bucket_all,
    expected_calibration_error,
    render,
    required_n,
    wilson,
)
from src.contract import FailureCounters


# ------------------------------------------------------------------- Wilson

def test_a_perfect_small_bucket_still_has_a_wide_interval():
    """Three out of three is the number that most invites over-reading."""
    low, high = wilson(3, 3)
    assert high == 1.0
    assert low < 0.5, "3/3 must not look like evidence of high accuracy"


def test_the_interval_narrows_as_n_grows():
    small = wilson(8, 10)
    large = wilson(80, 100)
    assert (large[1] - large[0]) < (small[1] - small[0])


def test_the_interval_stays_inside_zero_and_one():
    """The normal approximation does not, which is why Wilson is used."""
    for successes, n in [(0, 3), (3, 3), (1, 2), (0, 1), (1, 1)]:
        low, high = wilson(successes, n)
        assert 0.0 <= low <= high <= 1.0


def test_an_empty_bucket_has_no_interval():
    low, high = wilson(0, 0)
    assert math.isnan(low) and math.isnan(high)


# -------------------------------------------------------------- sample size

def test_the_required_sample_size_is_reported_per_bucket():
    """docs/02-metrics.md asks what n would be needed to support the claim."""
    assert required_n(0.9) == 139
    assert required_n(0.5) > required_n(0.9), "p=0.5 is the hardest case"


def test_a_tighter_claim_needs_more_records():
    assert required_n(0.9, half_width=0.02) > required_n(0.9, half_width=0.05)


# ----------------------------------------------------------------- bucketing

def test_records_land_in_the_bucket_their_confidence_names():
    buckets, underflow = bucket_all([(0.55, True), (0.65, True), (0.75, False),
                                     (0.85, True), (0.95, True)])
    assert [b.n for b in buckets] == [1, 1, 1, 1, 1]
    assert underflow.n == 0


def test_a_confidence_of_one_is_not_dropped():
    """The top edge is inclusive; a model that is certain must still be counted."""
    buckets, underflow = bucket_all([(1.0, True)])
    assert sum(b.n for b in buckets) == 1
    assert underflow.n == 0


def test_confidence_below_the_first_edge_is_reported_not_discarded():
    buckets, underflow = bucket_all([(0.22, False)])
    assert underflow.n == 1
    assert sum(b.n for b in buckets) == 0


def test_the_buckets_are_the_width_the_metrics_document_asks_for():
    assert EDGES[0] == 0.5
    for low, high in zip(EDGES, EDGES[1:]):
        assert round(min(high, 1.0) - low, 6) in (0.1, 0.1001)


# ----------------------------------------------------------------------- ECE

def test_a_perfectly_calibrated_set_has_near_zero_ece():
    pairs = [(0.9, True)] * 9 + [(0.9, False)]
    buckets, underflow = bucket_all(pairs)
    assert expected_calibration_error(buckets, underflow) == pytest.approx(0.0, abs=1e-9)


def test_overconfidence_shows_up_as_ece():
    pairs = [(0.95, True)] * 5 + [(0.95, False)] * 5
    buckets, underflow = bucket_all(pairs)
    assert expected_calibration_error(buckets, underflow) == pytest.approx(0.45, abs=1e-9)


def test_ece_weights_buckets_by_their_counts():
    """A one-record bucket must not swing the headline number.

    The large bucket is calibrated exactly - eighteen correct of twenty at 0.9 -
    so anything ECE reports comes from the single outlier, weighted by its share.
    """
    many = [(0.9, True)] * 18 + [(0.9, False)] * 2
    one = [(0.55, False)]
    buckets, underflow = bucket_all(many + one)

    ece = expected_calibration_error(buckets, underflow)
    assert ece == pytest.approx(0.55 / 21, abs=1e-9)
    assert ece < 0.03


# -------------------------------------------------------------------- report

def test_the_report_states_what_the_table_cannot_show():
    pairs = [(0.95, True)] * 3 + [(0.75, False)]
    buckets, underflow = bucket_all(pairs)
    text = render("m", pairs, buckets, underflow, 0.1, 0.1, FailureCounters())

    assert "cannot show" in text
    assert "would need about" in text
    assert "No recalibration is fitted" in text


def test_the_report_shows_a_count_for_every_bucket():
    pairs = [(0.95, True), (0.95, False), (0.65, True)]
    buckets, underflow = bucket_all(pairs)
    text = render("m", pairs, buckets, underflow, 0.1, 0.1, FailureCounters())

    assert "0.9-1.0" in text and "0.6-0.7" in text
    assert "95% Wilson interval" in text


def test_empty_buckets_are_omitted_rather_than_shown_as_zero_accuracy():
    pairs = [(0.95, True)]
    buckets, underflow = bucket_all(pairs)
    text = render("m", pairs, buckets, underflow, 0.0, 0.0, FailureCounters())

    assert "0.5-0.6" not in text, "an unpopulated bucket has no accuracy to show"
