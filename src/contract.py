"""Validation boundary between a model response and the rest of the system.

Every model response enters through `call_with_contract`. There is no other
door. The invariants this module exists to hold:

- A malformed response raises. It never becomes a default value, and it never
  disappears from a denominator.
- Schema failures and retry exhaustion are counted separately, because they
  mean different things: the first is a per-attempt format defect, the second
  is a case the pipeline could not produce output for at all.
- Repair is not attempted. The only leniency is unwrapping a markdown code
  fence, which is transport packaging rather than content.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Callable, TypeVar

from pydantic import BaseModel, ValidationError

DEFAULT_MAX_ATTEMPTS = 3

M = TypeVar("M", bound=BaseModel)

_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


class ContractError(Exception):
    """Base for every failure of the output contract."""


class SchemaValidationError(ContractError):
    """One response did not validate. Carries the raw payload for the trace."""

    def __init__(self, message: str, raw: str) -> None:
        super().__init__(message)
        self.raw = raw


class RetryExhaustedError(ContractError):
    """Every attempt failed. The case yields no output and is counted as such."""

    def __init__(self, attempts: int, failures: list[SchemaValidationError]) -> None:
        super().__init__(f"contract not satisfied after {attempts} attempt(s)")
        self.attempts = attempts
        self.failures = failures


@dataclass
class FailureCounters:
    """Three counters, reported separately and never merged.

    `schema_failures` counts attempts, so a case that fails twice and then
    succeeds contributes 2 here and 0 to `retry_exhaustions`. A case that
    exhausts its attempts contributes to both. They are not mutually
    exclusive and neither is a subset of an accuracy denominator.

    `provider_refusals` is the provider declining to answer at all, which is
    not the same event as the agent correctly refusing an out-of-bounds
    enquiry — that one is a task-quality metric, scored on the golden set.
    """

    schema_failures: int = 0
    retry_exhaustions: int = 0
    provider_refusals: int = 0
    raw_failures: list[str] = field(default_factory=list)

    def record_provider_refusal(self) -> None:
        self.provider_refusals += 1

    def as_dict(self) -> dict:
        return asdict(self)


def _unwrap(raw: str) -> str:
    match = _FENCE.match(raw)
    return match.group(1) if match else raw


def parse(raw: str, model_cls: type[M]) -> M:
    """Validate one raw response. Raises `SchemaValidationError` on any defect."""
    try:
        payload = json.loads(_unwrap(raw))
    except json.JSONDecodeError as exc:
        raise SchemaValidationError(f"response is not JSON: {exc}", raw) from exc

    if not isinstance(payload, dict):
        raise SchemaValidationError(
            f"response is a {type(payload).__name__}, expected a JSON object", raw
        )

    try:
        return model_cls.model_validate(payload)
    except ValidationError as exc:
        raise SchemaValidationError(
            f"{model_cls.__name__} contract violated: {exc}", raw
        ) from exc


def call_with_contract(
    call: Callable[[], str],
    model_cls: type[M],
    counters: FailureCounters,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> M:
    """Call the model until the response validates, or give up loudly.

    `call` is expected to raise on transport or provider errors; those are not
    contract failures and are deliberately not caught or counted here.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    failures: list[SchemaValidationError] = []
    for _ in range(max_attempts):
        raw = call()
        try:
            return parse(raw, model_cls)
        except SchemaValidationError as exc:
            counters.schema_failures += 1
            counters.raw_failures.append(exc.raw)
            failures.append(exc)

    counters.retry_exhaustions += 1
    raise RetryExhaustedError(max_attempts, failures)
