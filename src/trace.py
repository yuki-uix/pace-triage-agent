"""The observability boundary (ADR-004).

The model receives the enquiry as the customer wrote it, because redacting
before inference destroys the draft: a reply has to address the customer by name
and quote their actual policy number. Redaction happens on the path to disk
instead, so the compliance benefit arrives without the quality cost.

**The operator is reversible.** Replacement with `<PERSON>` makes an audit trail
useless - a genuine dispute cannot be traced back to a customer. Sensitive fields
are encrypted with a key held outside the trace store, so a trace can be
resolved by someone with the key and by no one else.

**Whole fields are encrypted, not detected entities, and that is the whole
point.** The first version ran Presidio over each field and encrypted what it
found. Measured, it failed open: in a trace whose prompt was a system message
plus a delimited enquiry, the policy number, phone, email and amount were all
encrypted and the customer's name was not. spaCy's NER is context-sensitive, and
the same name it finds in a short string it misses inside a long prompt. In the
dataset that kind of miss leaves a synthetic name as generated; here it puts real
customer data on disk in the clear.

A compliance boundary cannot be a statistical one. We do not need to *find* the
customer text in these fields - we know which fields carry it, because we wrote
them. So the gate is structural: every field not explicitly classified as
non-sensitive is encrypted in full. Counts, timings, model names and the
confidence method stay readable, which is what debugging throughput actually
needs; reading content requires the key, which is the posture we want.

**Coverage comes from the type, not from a checklist.** Every field on
`TraceEntry` is either named in `NON_SENSITIVE_FIELDS` or redacted. A field
added without being classified fails the tests rather than quietly writing
customer data to disk.
"""

from __future__ import annotations

import json
import os
import pathlib

from presidio_anonymizer.operators.aes_cipher import AESCipher
from pydantic import BaseModel, ConfigDict

# Fields that carry no customer data. Anything not listed here is redacted, so
# forgetting to classify a new field fails safe.
NON_SENSITIVE_FIELDS: frozenset[str] = frozenset({
    "record_id",
    "stage",
    "model",
    "thinking",
    "attempts",
    "prompt_tokens",
    "completion_tokens",
    "reasoning_tokens",
    "seconds",
    "confidence_method",
    "confidence_detail",
    "extra_calls",
})


class MissingTraceKey(RuntimeError):
    """Raised rather than writing customer data to disk in the clear."""


class TraceEntry(BaseModel):
    """One stage of one enquiry, as it will be stored.

    The text fields are what makes this useful for debugging and what makes it
    dangerous. They are the reason this module exists.
    """

    model_config = ConfigDict(extra="forbid")

    record_id: str
    stage: str
    model: str
    thinking: bool = False
    attempts: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    seconds: float = 0.0
    confidence_method: str | None = None
    confidence_detail: str | None = None
    extra_calls: int = 0

    # Sensitive: free text that quotes the customer.
    prompt: str = ""
    response: str = ""
    raw_failures: tuple[str, ...] = ()


def sensitive_fields() -> tuple[str, ...]:
    """Derived from the model, so a new field is covered without being listed."""
    return tuple(
        name for name in TraceEntry.model_fields if name not in NON_SENSITIVE_FIELDS
    )


def load_key() -> str:
    """The key lives in the environment, never in the trace store beside the data."""
    key = os.environ.get("TRACE_ENCRYPTION_KEY", "")
    if len(key) not in (16, 24, 32):
        raise MissingTraceKey(
            "TRACE_ENCRYPTION_KEY must be 16, 24 or 32 characters. Traces are "
            "not written without it: writing them unredacted would be the "
            "failure this boundary exists to prevent."
        )
    return key


class Redactor:
    """Encrypts whole fields. No detection step, so nothing to fail open."""

    def __init__(self, key: str):
        self.key = key.encode("utf-8")

    def redact(self, text: str) -> str:
        return AESCipher.encrypt(self.key, text) if text else text

    def resolve(self, ciphertext: str) -> str:
        """For a genuine dispute, by someone holding the key."""
        return AESCipher.decrypt(self.key, ciphertext) if ciphertext else ciphertext

    def redact_entry(self, entry: TraceEntry) -> TraceEntry:
        updates: dict = {}
        for field in sensitive_fields():
            value = getattr(entry, field)
            if isinstance(value, str):
                updates[field] = self.redact(value)
            elif isinstance(value, tuple):
                updates[field] = tuple(self.redact(item) for item in value)
        return entry.model_copy(update=updates)


class TraceStore:
    """Append-only JSONL. The only way in is `write`, and it redacts."""

    def __init__(self, path: str, redactor: Redactor):
        self.path = pathlib.Path(path)
        self.redactor = redactor
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, entry: TraceEntry) -> TraceEntry:
        redacted = self.redactor.redact_entry(entry)
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(redacted.model_dump(), ensure_ascii=False) + "\n")
        return redacted
