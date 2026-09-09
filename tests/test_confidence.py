"""Deriving confidence, and refusing to invent one."""

import math
from types import SimpleNamespace

import pytest

from src.confidence import ConfidenceMethod, by_self_consistency, from_logprobs


def token(text: str, probability: float) -> SimpleNamespace:
    return SimpleNamespace(token=text, logprob=math.log(probability))


CONTENT = '{"case_type": "ADDRESS_CHANGE", "priority": "NORMAL"}'
TOKENS = [
    token('{"case_type": "', 1.0),
    token("ADDRESS", 0.7365),
    token("_CHANGE", 1.0),
    token('", "priority": "', 1.0),
    token("NORMAL", 0.8116),
    token('"}', 1.0),
]


def test_confidence_is_the_product_over_the_value_tokens():
    result = from_logprobs(CONTENT, TOKENS, "ADDRESS_CHANGE")
    assert result.method is ConfidenceMethod.LOGPROBS
    assert result.value == pytest.approx(0.7365, abs=1e-3)


def test_a_second_field_is_located_independently():
    assert from_logprobs(CONTENT, TOKENS, "NORMAL").value == pytest.approx(0.8116, abs=1e-3)


def test_the_derived_value_has_resolution_a_verbalised_one_would_not():
    """The point of ADR-002: stated confidence clusters in 0.85-0.95."""
    assert from_logprobs(CONTENT, TOKENS, "ADDRESS_CHANGE").value < 0.85


def test_a_value_that_cannot_be_located_returns_none_rather_than_a_guess():
    assert from_logprobs(CONTENT, TOKENS, "CLAIM") is None


def test_no_tokens_returns_none():
    assert from_logprobs(CONTENT, [], "ADDRESS_CHANGE") is None


def test_whitespace_between_tokens_does_not_break_location():
    tokens = [token("{\n  \"case_type\": \"", 1.0), token("CLAIM", 0.5), token("\"\n}", 1.0)]
    assert from_logprobs("", tokens, "CLAIM").value == pytest.approx(0.5)


def test_self_consistency_is_the_modal_vote_share():
    result = by_self_consistency(["CLAIM", "CLAIM", "OTHER"])
    assert result.method is ConfidenceMethod.SELF_CONSISTENCY
    assert result.value == pytest.approx(2 / 3)


def test_unanimous_self_consistency_is_one():
    assert by_self_consistency(["CLAIM"] * 3).value == 1.0


def test_self_consistency_needs_a_vote():
    with pytest.raises(ValueError):
        by_self_consistency([])


def test_the_method_is_always_recorded():
    """A metric that silently degrades to a worse method is worse than one that fails."""
    assert from_logprobs(CONTENT, TOKENS, "NORMAL").method
    assert by_self_consistency(["A"]).method
