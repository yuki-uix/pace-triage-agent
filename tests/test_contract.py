"""The validation boundary: what gets counted, what raises, what never happens."""

import json

import pytest

from src.contract import (
    DEFAULT_MAX_ATTEMPTS,
    FailureCounters,
    RetryExhaustedError,
    SchemaValidationError,
    call_with_contract,
    parse,
)
from src.schema import CaseType, DraftOutput, TriageOutput

VALID_TRIAGE = {"case_type": "CLAIM", "priority": "URGENT", "confidence": 0.82}
VALID_RAW = json.dumps(VALID_TRIAGE)


def responder(*responses):
    """A stand-in model call that returns each response in turn."""
    queue = list(responses)

    def call():
        return queue.pop(0)

    return call


def test_valid_response_parses():
    assert parse(VALID_RAW, TriageOutput).case_type is CaseType.CLAIM


def test_fenced_json_is_unwrapped():
    fenced = f"```json\n{VALID_RAW}\n```"
    assert parse(fenced, TriageOutput).confidence == 0.82


def test_non_json_response_raises_and_keeps_the_raw_payload():
    with pytest.raises(SchemaValidationError) as exc:
        parse("I'm sorry, I can't help with that.", TriageOutput)
    assert exc.value.raw == "I'm sorry, I can't help with that."


def test_json_array_is_rejected():
    with pytest.raises(SchemaValidationError):
        parse("[]", TriageOutput)


def test_unknown_enum_value_raises_rather_than_defaulting():
    raw = json.dumps({**VALID_TRIAGE, "case_type": "BILLING_DISPUTE"})
    with pytest.raises(SchemaValidationError):
        parse(raw, TriageOutput)


def test_missing_field_raises_rather_than_defaulting():
    raw = json.dumps({"case_type": "CLAIM", "priority": "URGENT"})
    with pytest.raises(SchemaValidationError):
        parse(raw, TriageOutput)


def test_valid_first_attempt_leaves_every_counter_at_zero():
    counters = FailureCounters()
    result = call_with_contract(responder(VALID_RAW), TriageOutput, counters)
    assert result.case_type is CaseType.CLAIM
    assert counters.as_dict() == {
        "schema_failures": 0,
        "retry_exhaustions": 0,
        "provider_refusals": 0,
    }


def test_recovery_counts_the_failed_attempt_but_not_an_exhaustion():
    counters = FailureCounters()
    call = responder("not json", json.dumps({"case_type": "CLAIM"}), VALID_RAW)

    result = call_with_contract(call, TriageOutput, counters, max_attempts=3)

    assert result.case_type is CaseType.CLAIM
    assert counters.schema_failures == 2
    assert counters.retry_exhaustions == 0
    assert counters.raw_failures == ["not json", '{"case_type": "CLAIM"}']


def test_retry_exhaustion_raises_and_is_counted_separately():
    counters = FailureCounters()
    call = responder("nope", "still nope", "nope again")

    with pytest.raises(RetryExhaustedError) as exc:
        call_with_contract(call, TriageOutput, counters, max_attempts=3)

    assert exc.value.attempts == 3
    assert len(exc.value.failures) == 3
    assert counters.schema_failures == 3
    assert counters.retry_exhaustions == 1


def test_attempts_are_bounded():
    counters = FailureCounters()
    calls = {"n": 0}

    def call():
        calls["n"] += 1
        return "nope"

    with pytest.raises(RetryExhaustedError):
        call_with_contract(call, TriageOutput, counters, max_attempts=2)

    assert calls["n"] == 2


def test_default_attempt_bound_is_applied_when_not_passed():
    counters = FailureCounters()
    calls = {"n": 0}

    def call():
        calls["n"] += 1
        return "nope"

    with pytest.raises(RetryExhaustedError):
        call_with_contract(call, TriageOutput, counters)

    assert calls["n"] == DEFAULT_MAX_ATTEMPTS


def test_zero_attempts_is_a_programming_error():
    with pytest.raises(ValueError):
        call_with_contract(responder(VALID_RAW), TriageOutput, FailureCounters(), 0)


def test_provider_errors_propagate_and_are_not_counted_as_schema_failures():
    counters = FailureCounters()

    def call():
        raise TimeoutError("provider timed out")

    with pytest.raises(TimeoutError):
        call_with_contract(call, TriageOutput, counters)

    assert counters.schema_failures == 0
    assert counters.retry_exhaustions == 0


def test_boolean_confidence_fails_the_contract_at_the_boundary():
    counters = FailureCounters()
    raw = json.dumps({"case_type": "CLAIM", "priority": "URGENT", "confidence": True})

    with pytest.raises(RetryExhaustedError):
        call_with_contract(responder(raw, raw, raw), TriageOutput, counters)

    assert counters.schema_failures == 3


def test_as_dict_withholds_raw_payloads_by_default():
    """`as_dict` is what results and traces serialise; PII must not ride along."""
    counters = FailureCounters()
    with pytest.raises(RetryExhaustedError):
        call_with_contract(
            responder(*["Policy HK-8842011 for Chan Ka Ming"] * 3),
            TriageOutput,
            counters,
        )

    serialised = counters.as_dict()

    assert "raw_failures" not in serialised
    assert "HK-8842011" not in json.dumps(serialised)
    assert serialised["schema_failures"] == 3


def test_raw_payloads_are_available_only_when_asked_for_explicitly():
    counters = FailureCounters()
    with pytest.raises(RetryExhaustedError):
        call_with_contract(responder(*["nope"] * 3), TriageOutput, counters)

    assert counters.as_dict(include_raw=True)["raw_failures"] == ["nope"] * 3


def test_provider_refusal_is_its_own_counter():
    counters = FailureCounters()
    counters.record_provider_refusal()
    assert counters.provider_refusals == 1
    assert counters.schema_failures == 0


def test_counters_accumulate_across_cases():
    counters = FailureCounters()

    call_with_contract(responder(VALID_RAW), TriageOutput, counters)
    with pytest.raises(RetryExhaustedError):
        call_with_contract(responder("a", "b", "c"), TriageOutput, counters)
    call_with_contract(responder("bad", VALID_RAW), TriageOutput, counters)

    assert counters.schema_failures == 4
    assert counters.retry_exhaustions == 1


def test_the_same_boundary_serves_the_draft_stage():
    counters = FailureCounters()
    raw = json.dumps({"summary": "Premium dispute.", "draft_reply": "Dear Ms Chan,"})

    result = call_with_contract(responder(raw), DraftOutput, counters)

    assert result.draft_reply == "Dear Ms Chan,"
    assert counters.schema_failures == 0
