"""The observability boundary: what reaches disk, and what cannot.

The tests that matter here assert an absence, and they derive what to look for
from the type rather than from a list someone maintains.
"""

import json
import math
import pathlib
from types import SimpleNamespace

import pytest

from src.contract import FailureCounters
from src.pipeline import PipelineConfig, StageConfig, run
from src.redaction import build_analyzer, merge_overlaps, resolve_overlaps
from src.trace import (
    NON_SENSITIVE_FIELDS,
    MissingTraceKey,
    Redactor,
    TraceEntry,
    TraceStore,
    load_key,
    sensitive_fields,
)

KEY = "0123456789abcdef"
PII = "Chan Ka Yan, policy P06421883, mobile 9123 4567, ka.yan@example.com, HK$1,847.00"
PROBES = ["Chan Ka Yan", "P06421883", "9123 4567", "ka.yan@example.com", "1,847"]


@pytest.fixture(scope="module")
def redactor():
    return Redactor(KEY)


def entry(**overrides) -> TraceEntry:
    base = {"record_id": "ENQ-002", "stage": "triage", "model": "m"}
    return TraceEntry(**{**base, **overrides})


# ------------------------------------------------------------ span coverage

def test_choosing_a_span_can_leave_a_fragment_behind():
    """Why entity-level substitution needs merging, not picking.

    The HKID pattern matches 'P064218' inside 'P06421883' at a higher score than
    the policy pattern matches the whole thing. Picking the winner leaves '83'.
    Right for labelling, wrong whenever the question is coverage.
    """
    analyzer = build_analyzer()
    text = "policy P06421883"
    entities = ["POLICY_NUMBER", "HK_ID", "PERSON", "PHONE_NUMBER"]
    results = analyzer.analyze(text=text, language="en", entities=entities)

    assert "P06421883" not in [text[r.start:r.end] for r in resolve_overlaps(results)]
    assert "P06421883" in [text[r.start:r.end] for r in merge_overlaps(results)]


def test_the_boundary_does_not_depend_on_ner_finding_anything():
    """The finding that changed this module'"'"'s design.

    An earlier version detected entities and encrypted what it found. In a trace
    whose prompt was a system message plus a delimited enquiry, the policy
    number, phone, email and amount were encrypted and the customer'"'"'s name was
    not: spaCy'"'"'s NER is context-sensitive and misses in a long prompt what it
    finds in a short string. A compliance boundary cannot fail open, so whole
    fields are encrypted and detection is not in the path at all.
    """
    long_prompt = ("You triage inbound email for an insurer. " * 40 +
                   "\n<enquiry>\nChan Ka Yan, policy P06421883\n</enquiry>")
    redacted = Redactor(KEY).redact(long_prompt)

    assert "Chan Ka Yan" not in redacted
    assert "triage inbound email" not in redacted


# --------------------------------------------------------------- redaction

@pytest.mark.parametrize("probe", PROBES)
def test_pii_does_not_reach_the_trace_store(tmp_path, redactor, probe):
    store = TraceStore(str(tmp_path / "traces.jsonl"), redactor)
    store.write(entry(prompt=PII, response=PII, raw_failures=(PII,)))

    assert probe not in (tmp_path / "traces.jsonl").read_text(encoding="utf-8")


def test_raw_failures_are_redacted_too(tmp_path, redactor):
    """The exit found while verifying the output contract: malformed model
    output is stored verbatim, and malformed output still quotes the customer."""
    store = TraceStore(str(tmp_path / "t.jsonl"), redactor)
    written = store.write(entry(raw_failures=("garbage from Chan Ka Yan",)))
    assert "Chan Ka Yan" not in written.raw_failures[0]


@pytest.mark.parametrize("field", sensitive_fields())
def test_every_sensitive_field_is_actually_redacted(tmp_path, redactor, field):
    """Parametrised over the type. A field added without being classified as
    non-sensitive lands here automatically and must survive this test."""
    value = (PII,) if field == "raw_failures" else PII
    store = TraceStore(str(tmp_path / "t.jsonl"), redactor)
    store.write(entry(**{field: value}))

    written = (tmp_path / "t.jsonl").read_text(encoding="utf-8")
    for probe in PROBES:
        assert probe not in written


def test_the_sensitive_set_is_derived_from_the_model():
    """Not a hand-kept list: every field is classified or encrypted."""
    assert set(sensitive_fields()) | NON_SENSITIVE_FIELDS == set(TraceEntry.model_fields)
    assert set(sensitive_fields()) & NON_SENSITIVE_FIELDS == set()


def test_the_non_sensitive_list_names_only_real_fields():
    """A stray name would be dead weight hiding intent, even though it fails safe."""
    assert NON_SENSITIVE_FIELDS <= set(TraceEntry.model_fields)


def test_counts_are_not_redacted(tmp_path, redactor):
    """Redacting the numbers would make the trace store useless for its job."""
    store = TraceStore(str(tmp_path / "t.jsonl"), redactor)
    store.write(entry(prompt_tokens=1234, model="qwen3.7-flash", stage="triage"))

    written = json.loads((tmp_path / "t.jsonl").read_text(encoding="utf-8"))
    assert written["prompt_tokens"] == 1234
    assert written["model"] == "qwen3.7-flash"


# ------------------------------------------------------------- reversibility

def test_redaction_is_reversible_for_a_genuine_dispute(redactor):
    """ADR-004: replacement with <PERSON> makes the audit trail useless."""
    assert redactor.resolve(redactor.redact(PII)) == PII


def test_a_different_key_cannot_read_the_trace(redactor):
    with pytest.raises(Exception):
        Redactor("fedcba9876543210").resolve(redactor.redact(PII))


# --------------------------------------------------------------------- keys

def test_a_missing_key_refuses_to_write(monkeypatch):
    """Writing unredacted is the failure this boundary exists to prevent."""
    monkeypatch.delenv("TRACE_ENCRYPTION_KEY", raising=False)
    with pytest.raises(MissingTraceKey):
        load_key()


@pytest.mark.parametrize("bad", ["", "short", "x" * 17])
def test_a_key_of_the_wrong_length_is_refused(monkeypatch, bad):
    monkeypatch.setenv("TRACE_ENCRYPTION_KEY", bad)
    with pytest.raises(MissingTraceKey):
        load_key()


def test_a_valid_key_is_accepted(monkeypatch):
    monkeypatch.setenv("TRACE_ENCRYPTION_KEY", KEY)
    assert load_key() == KEY


# ------------------------------------------------------ the pipeline path

def token(text, probability):
    return SimpleNamespace(token=text, logprob=math.log(probability))


class FakeClient:
    def __init__(self, responses, tokens=None):
        self.responses = list(responses)
        self.tokens = tokens
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content=self.responses.pop(0)),
                logprobs=SimpleNamespace(content=self.tokens) if self.tokens else None)],
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1,
                                  completion_tokens_details=SimpleNamespace(
                                      reasoning_tokens=0)),
        )


def test_the_pipeline_writes_redacted_traces(tmp_path, redactor):
    """Every write path, not just a direct call to the store."""
    store = TraceStore(str(tmp_path / "t.jsonl"), redactor)
    client = FakeClient(
        ['{"case_type": "PREMIUM_BILLING", "priority": "URGENT"}',
         '{"summary": "s", "draft_reply": "Dear Chan Ka Yan, policy P06421883."}'],
        [token('{"case_type": "', 1.0), token("PREMIUM_BILLING", 0.8),
         token('", "priority": "URGENT"}', 1.0)])

    run(client, PipelineConfig(StageConfig("a"), StageConfig("b")),
        "ENQ-002", "Billing", PII, FailureCounters(), store)

    written = (tmp_path / "t.jsonl").read_text(encoding="utf-8")
    assert len(written.strip().splitlines()) == 2
    for probe in PROBES:
        assert probe not in written


def test_the_pending_queue_is_not_the_trace_store(tmp_path, redactor):
    """The reviewer's queue holds the draft in the clear on purpose. A reviewer
    cannot review ciphertext; this is a considered exception, not an oversight."""
    client = FakeClient(
        ['{"case_type": "PREMIUM_BILLING", "priority": "URGENT"}',
         '{"summary": "s", "draft_reply": "Dear Chan Ka Yan"}'],
        [token('{"case_type": "', 1.0), token("PREMIUM_BILLING", 0.8),
         token('"}', 1.0)])

    item = run(client, PipelineConfig(StageConfig("a"), StageConfig("b")),
               "ENQ-002", "s", PII, FailureCounters())

    assert "Chan Ka Yan" in item.draft_reply
    assert all("prompt" not in trace for trace in item.traces)


def test_a_failed_stage_still_leaves_a_trace(tmp_path, redactor):
    """The stage that failed is the one you most want a trace for."""
    store = TraceStore(str(tmp_path / "t.jsonl"), redactor)
    client = FakeClient(["not json", "still not json", "nope"],
                        [token('{"case_type": "', 1.0)])

    with pytest.raises(Exception):
        run(client, PipelineConfig(StageConfig("a"), StageConfig("b")),
            "ENQ-002", "s", PII, FailureCounters(), store)

    written = (tmp_path / "t.jsonl").read_text(encoding="utf-8")
    assert written.strip(), "a failed stage wrote no trace at all"
    for probe in PROBES:
        assert probe not in written
