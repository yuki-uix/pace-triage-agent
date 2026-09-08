"""The output contract.

Both pipeline stages return JSON that must validate against one of these
models. Nothing downstream accepts a dict — the pending queue, the metrics and
the review CLI all take validated instances, so an unvalidated payload has
nowhere to go.

`extra="forbid"` is deliberate. A model that invents an extra field has not
followed the contract, and silently dropping the field would hide that.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class CaseType(str, Enum):
    """Closed set. An unrecognised value is a schema failure, not an OTHER."""

    POLICY_QUERY = "POLICY_QUERY"
    PREMIUM_BILLING = "PREMIUM_BILLING"
    ADDRESS_CHANGE = "ADDRESS_CHANGE"
    CLAIM = "CLAIM"
    COMPLAINT = "COMPLAINT"
    OTHER = "OTHER"


class Priority(str, Enum):
    URGENT = "URGENT"
    NORMAL = "NORMAL"
    LOW = "LOW"


class TriageOutput(BaseModel):
    """Stage 1. Short, fixed-format, high-frequency.

    `confidence` is derived rather than asked for (ADR-002), but it arrives
    here the same way regardless of which derivation was used, so the contract
    does not encode the method. The method is recorded in the trace.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_type: CaseType
    priority: Priority
    confidence: float = Field(ge=0.0, le=1.0)


class DraftOutput(BaseModel):
    """Stage 2. Long-output, tone-sensitive, hallucination-costly."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: str = Field(min_length=1)
    draft_reply: str = Field(min_length=1)
