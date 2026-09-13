"""Deriving a confidence score instead of asking for one (ADR-002).

Verbalised confidence clusters in 0.85-0.95 regardless of correctness, so a
calibration table built on it has no resolution. Two derivations, in order of
preference, and which one ran is recorded per call — a metric that silently
degrades to a worse method is worse than one that fails.

Measured on this provider: the enum value's first token carries essentially all
of the uncertainty. For one address-change enquiry the value token 'ADDRESS' came
back at p=0.7365 with 'OTHER' at 0.128 and 'COM' at 0.113, while the continuation
'_CHANGE' was p=1.0000. That is the resolution the calibration table needs.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Sequence


class ConfidenceMethod(str, Enum):
    LOGPROBS = "LOGPROBS"
    SELF_CONSISTENCY = "SELF_CONSISTENCY"


@dataclass(frozen=True)
class Confidence:
    value: float
    method: ConfidenceMethod
    detail: str = ""


def _token_spans(tokens: Sequence) -> list[tuple[int, int, float]]:
    """Character span and probability of each token in the reconstructed text."""
    spans, cursor = [], 0
    for token in tokens:
        text = token.token
        spans.append((cursor, cursor + len(text), math.exp(token.logprob)))
        cursor += len(text)
    return spans


def from_logprobs(content: str, tokens: Sequence, value: str,
                  key: str | None = None) -> Confidence | None:
    """Probability the model assigned to the label string it actually emitted.

    The product over the tokens spanning the value, which is the model's
    probability of that exact label rather than of one convenient token of it.
    Returns None when the value cannot be located, so the caller falls back
    rather than inventing a number.

    **The value is located after its key, not by first occurrence.** Models
    restate the permitted values before answering, and a first-occurrence match
    then measures the echo instead of the decision. Caught by probe: with the
    real value token at p=0.55 behind an echoed copy, first-occurrence matching
    returned 1.0000 — a malformed-looking response wearing maximum certainty,
    the same failure class as a coerced boolean confidence, and harder to see
    because the JSON is perfectly valid.
    """
    if not tokens:
        return None

    rebuilt = "".join(token.token for token in tokens)

    search_from = 0
    if key is not None:
        key_at = rebuilt.rfind(f'"{key}"')
        if key_at == -1:
            return None
        search_from = key_at + len(key) + 2

    start = rebuilt.find(value, search_from)
    if start == -1:
        return None
    end = start + len(value)

    probability, covered = 1.0, 0
    for token_start, token_end, token_probability in _token_spans(tokens):
        if token_start < end and start < token_end:
            probability *= token_probability
            covered += 1

    if covered == 0:
        return None

    return Confidence(
        value=min(max(probability, 0.0), 1.0),
        method=ConfidenceMethod.LOGPROBS,
        detail=f"product over {covered} token(s) spanning {value!r}",
    )


def by_self_consistency(votes: Sequence[str], predicted_type: str) -> Confidence:
    """Share of validated independent samples supporting the emitted label."""
    if not votes:
        raise ValueError("self-consistency needs at least one vote")
    supported = Counter(votes)[predicted_type]
    return Confidence(
        value=supported / len(votes),
        method=ConfidenceMethod.SELF_CONSISTENCY,
        detail=f"support for {predicted_type!r}: {supported}/{len(votes)} independent samples",
    )
