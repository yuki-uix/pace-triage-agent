"""The output contract.

Both pipeline stages return JSON that must validate against one of these
models. Nothing downstream accepts a dict — the pending queue, the metrics and
the review CLI all take validated instances, so an unvalidated payload has
nowhere to go.

`extra="forbid"` is deliberate. A model that invents an extra field has not
followed the contract, and silently dropping the field would hide that.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StrictStr


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


class TriageDecision(BaseModel):
    """What the triage model is asked for — and confidence is not on the list.

    ADR-002 derives confidence rather than asking for it, so the model-facing
    contract cannot contain a `confidence` field: a model that supplied one
    would be answering a question we deliberately do not ask. `TriageOutput`
    below is this decision plus the confidence the pipeline computes.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_type: CaseType
    priority: Priority


class TriageOutput(BaseModel):
    """Stage 1. Short, fixed-format, high-frequency.

    `confidence` is derived rather than asked for (ADR-002), but it arrives
    here the same way regardless of which derivation was used, so the contract
    does not encode the method. The method is recorded in the trace.

    It is strictly typed. Pydantic's lax mode promotes `true` to 1.0, which
    would turn a malformed response into the highest possible confidence —
    the one value that most distorts the calibration table and the escalation
    gate. A confidence that is not a number is a schema failure.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_type: CaseType
    priority: Priority
    confidence: StrictFloat | StrictInt = Field(ge=0.0, le=1.0)


class DraftOutput(BaseModel):
    """Stage 2. Long-output, tone-sensitive, hallucination-costly."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: StrictStr = Field(min_length=1)
    draft_reply: StrictStr = Field(min_length=1)
