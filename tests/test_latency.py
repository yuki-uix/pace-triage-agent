"""Serial measurement, and the properties that make it worth measuring."""

import math
import pathlib
import re
from types import SimpleNamespace

import pytest

from evals.latency import (
    MissingPrice,
    StageSamples,
    cost_per_invocation,
    load_prices,
    measure,
    render,
)
from src.contract import FailureCounters
from src.dataset import Enquiry
from src.pipeline import PipelineConfig, StageConfig

TRIAGE_JSON = '{"case_type": "CLAIM", "priority": "URGENT"}'
DRAFT_JSON = '{"summary": "s", "draft_reply": "d"}'


def token(text, probability):
    return SimpleNamespace(token=text, logprob=math.log(probability))


CLAIM_TOKENS = [token('{"case_type": "', 1.0), token("CLAIM", 0.9),
                token('", "priority": "URGENT"}', 1.0)]


class PacedClient:
    """Returns canned responses and burns a little wall clock per call."""

    def __init__(self, delay: float = 0.0, failures: int = 0):
        self.delay = delay
        self.failures = failures
        self.calls = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        import time

        self.calls += 1
        time.sleep(self.delay)
        if self.failures > 0:
            self.failures -= 1
            content = "not json"
        else:
            content = TRIAGE_JSON if kwargs["messages"][0]["content"].startswith(
                "You triage") else DRAFT_JSON
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content),
                                     logprobs=SimpleNamespace(content=CLAIM_TOKENS))],
            usage=SimpleNamespace(prompt_tokens=100, completion_tokens=20,
                                  completion_tokens_details=SimpleNamespace(
                                      reasoning_tokens=0)))


def records(count: int):
    return [Enquiry(id=f"ENQ-{i + 1:03d}", subject="s", body="b")
            for i in range(count)]


def config() -> PipelineConfig:
    return PipelineConfig(StageConfig("cheap"), StageConfig("careful"))


# ------------------------------------------------------------------- serial

def test_the_module_contains_no_concurrency():
    """Structural, because a future reader will be tempted.

    A concurrent run measures the harness's queueing rather than the model, and
    CLAUDE.md forbids merging it with the quality run. Asserting the absence is
    cheaper than hoping the comment is read.
    """
    source = pathlib.Path("evals/latency.py").read_text(encoding="utf-8")
    for forbidden in ("ThreadPoolExecutor", "ProcessPoolExecutor", "asyncio",
                      "threading", "multiprocessing", "pool.map"):
        assert forbidden not in source, f"{forbidden} in the latency harness"


def test_calls_happen_one_at_a_time():
    """Two stages per record, in order, with nothing overlapping."""
    client = PacedClient()
    measure(client, config(), records(3), FailureCounters(), warmups=0)
    assert client.calls == 6


# ------------------------------------------------------------------ warm-up

def test_the_first_record_is_discarded():
    """A cold first call measures TLS and connection setup, not the model."""
    stages, end_to_end, discarded = measure(
        PacedClient(), config(), records(4), FailureCounters(), warmups=1)

    assert discarded == 1
    assert stages["triage"].n == 3
    assert len(end_to_end) == 3


def test_warmups_can_be_turned_off_for_a_short_run():
    stages, _, discarded = measure(PacedClient(), config(), records(2),
                                   FailureCounters(), warmups=0)
    assert discarded == 0
    assert stages["triage"].n == 2


# -------------------------------------------------------------- percentiles

@pytest.mark.parametrize("values,expected", [
    ([1.0], 1.0),
    ([1.0, 2.0], 2.0),
    ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 10),
    ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20], 19),
])
def test_p95_is_nearest_rank_not_interpolated(values, expected):
    samples = StageSamples("triage", "m")
    samples.seconds = [float(v) for v in values]
    assert samples.p95() == pytest.approx(float(expected))


def test_median_and_p95_are_reported_per_stage():
    stages, _, _ = measure(PacedClient(), config(), records(3),
                           FailureCounters(), warmups=0)
    assert stages["triage"].model == "cheap"
    assert stages["draft"].model == "careful"
    assert stages["triage"].n == stages["draft"].n == 3


# --------------------------------------------------------------------- cost

def test_a_model_without_a_price_refuses_rather_than_costing_zero():
    with pytest.raises(MissingPrice):
        cost_per_invocation("unpriced", 100, 20, {})


def test_a_half_filled_price_still_refuses():
    with pytest.raises(MissingPrice):
        cost_per_invocation("m", 100, 20,
                            {"m": {"input_per_mtok": 1.0, "output_per_mtok": None}})


def test_cost_uses_the_measured_token_counts():
    cost = cost_per_invocation("m", 1_000_000, 1_000_000,
                               {"m": {"input_per_mtok": 2.0, "output_per_mtok": 5.0}})
    assert cost == pytest.approx(7.0)


def test_the_shipped_price_file_is_a_template_not_a_guess():
    """Prices were not published anywhere citable; inventing them would make the
    cost column fiction dressed as measurement."""
    prices = load_prices()
    assert prices
    assert all(entry["input_per_mtok"] is None for entry in prices.values())


def test_the_report_says_no_price_rather_than_printing_a_number():
    stages, end_to_end, discarded = measure(PacedClient(), config(), records(3),
                                            FailureCounters(), warmups=0)
    report = render(stages, end_to_end, discarded, FailureCounters(), {})
    assert "no price" in report


# ----------------------------------------------------------------- failures

def test_failure_counts_are_reported_apart_from_the_timings():
    counters = FailureCounters()
    stages, _, _ = measure(PacedClient(failures=1), config(), records(2),
                           counters, warmups=0)

    report = render(stages, [], 0, counters, {})
    assert counters.schema_failures == 1
    assert "schema failures    1" in report
    assert "retry exhaustions  0" in report
    assert "provider refusals  0" in report


def test_a_case_that_produced_nothing_is_not_timed():
    """Its end-to-end time would be the time taken to fail, which measures
    nothing about serving a customer."""
    counters = FailureCounters()
    stages, end_to_end, _ = measure(PacedClient(failures=99), config(),
                                    records(2), counters, warmups=0)

    assert end_to_end == []
    assert stages["triage"].n == 0
    assert counters.retry_exhaustions == 2


def test_a_failed_first_record_does_not_consume_the_warm_up():
    """Warm-ups are counted among successful records, not by position.

    Otherwise a first record that exhausts its retries takes the warm-up slot
    silently and the report claims none was discarded while the first timed call
    is the cold one.
    """
    class FirstRecordFails(PacedClient):
        def _create(self, **kwargs):
            self.calls += 1
            if self.calls <= 3:          # the first record's triage retries out
                return SimpleNamespace(
                    choices=[SimpleNamespace(
                        message=SimpleNamespace(content="not json"),
                        logprobs=SimpleNamespace(content=CLAIM_TOKENS))],
                    usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1,
                                          completion_tokens_details=SimpleNamespace(
                                              reasoning_tokens=0)))
            return super()._create(**kwargs)

    counters = FailureCounters()
    stages, end_to_end, discarded = measure(
        FirstRecordFails(), config(), records(3), counters, warmups=1)

    assert counters.retry_exhaustions == 1
    assert discarded == 1, "the warm-up must come from a record that succeeded"
    assert stages["triage"].n == 1
    assert len(end_to_end) == 1
