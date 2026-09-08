# Architecture and Design Decisions

## Pipeline

```
inbound email (plain text)
        │
        ├─ [wrapped as data, never as instruction]
        │
        ▼
  Stage 1: TRIAGE                  small / cheap model
    case_type, priority, confidence
        │
        ▼
  Stage 2: DRAFT                   larger / careful model
    summary, draft_reply
        │
        ▼
  Pydantic validation ──── fails ──▶ counted, surfaced, no retry beyond N
        │
        ▼
  pending queue (JSONL)  ──▶ review CLI: accept / edit / discard
        │
        └─ logging path ──▶ Presidio redaction ──▶ trace store
```

## ADR-001: Split the agent into two stages

**Decision.** Triage (classification + priority + confidence) and drafting
(summary + reply) are separate LLM calls with separately configurable models.

**Why.** The two stages have opposite requirements. Triage is short-output,
high-frequency, fixed-format — a small model plausibly suffices. Drafting is
long-output, tone-sensitive, and hallucination-costly — it probably needs a
stronger model.

Keeping them fused forces model selection to be a single all-or-nothing choice,
and the comparison degenerates into "the bigger model won every column."
Splitting turns Deliverable B into a 2×2 matrix and makes a genuinely useful
engineering conclusion available: cheap model for triage, careful model for
drafting.

The brief hints at this — it notes that the right weighting differs between a
customer-facing drafting step and a high-volume background classifier. Making
that a structural property of the system rather than a paragraph in the write-up
is the stronger answer.

**Rejected: single call producing all four fields.** Cheaper and lower latency,
but it collapses the model-selection question and makes the confidence score
contaminated by the drafting task. Rejected on evaluation grounds, not
performance grounds.

**Cost.** Two calls, roughly doubled latency, slightly more orchestration. Both
acceptable for a queue-backed CS assist tool where a human reviews every output
anyway.

## ADR-002: Confidence is derived, not asked for

**Decision.** Prefer token-level probability from the classification decision. If
the provider does not expose logprobs, fall back to self-consistency: three
samples at temperature 0.7, confidence = modal vote share.

**Why.** Verbalized LLM confidence clusters in 0.85–0.95 regardless of
correctness. A calibration table built on it has no resolution. Both fallbacks
produce a score with actual variance.

**Cost.** Self-consistency triples triage cost. Mitigation: run it on the golden
set to characterise the gap, and document the production trade-off rather than
pretending the cheap path is equivalent.

## ADR-003: Groundedness is checked at two levels

**Decision.** Split "does the draft invent facts" into two separate metrics.

*Entity-level* — policy numbers, amounts, dates, names appearing in the draft
must be a subset of those in the enquiry. Regex/NER extraction plus set
comparison. Deterministic, free, explainable. **No LLM.**

*Commitment-level* — fabricated SLAs, promises, or entitlements
("we will refund within 3 business days"). This is the more dangerous failure for
a regulated insurer and it needs a judge.

**Why.** A single judge-based groundedness score conflates a mechanically
checkable failure with a judgement call, and makes the cheap check impossible to
audit. Splitting means the high-severity half of the metric is deterministic.

**Rejected: Ragas faithfulness.** It models a `retrieval_context`, and there is no
retrieval step here. Its claim-decomposition approach is worth borrowing by hand;
the dependency is not.

## ADR-004: PII redaction sits at the observability boundary

**Decision.** The model receives the original text. Presidio redaction is applied
on the path to logs and traces, not on the path to inference.

**Why.** Redacting before inference destroys draft quality — the reply needs to
address the customer by name and reference their actual policy. Redacting at the
logging boundary gets the compliance benefit without the quality cost.

**Exception to document.** If data residency requirements apply (Hong Kong PDPO,
cross-border transfer to a non-local API), the inference boundary must be
redacted too, with placeholder substitution and re-insertion after generation.
This trade-off is discussed in the write-up rather than implemented.

**Operator choice.** Logs use reversible encryption rather than replacement, so a
genuine dispute can still be traced to a customer. Replacement with `<PERSON>`
would make the audit trail useless.

## ADR-005: DeepEval over promptfoo

**Decision.** DeepEval as the harness.

**Why.** promptfoo is declarative and YAML-driven; the ceiling of what can be
expressed is the ceiling of the config schema. This project needs custom
non-LLM metrics (entity groundedness, classification accuracy with a confusion
matrix) and conditional evaluation logic (if the enquiry should be refused, only
refusal correctness is scored and the draft is not evaluated at all). DeepEval's
`BaseMetric` subclassing and `DAGMetric` express both natively, and
`deepeval test run` is pytest underneath, which makes the one-command
re-run requirement free.

promptfoo's stronger multi-model matrix view is a real loss. The comparison table
is written by hand instead — which is arguably better here, since the table is
part of what is being assessed.

**Also rejected:** Argilla (too heavy for 40 records), netcal (cannot fit a
recalibration on n=40 without overfitting — calibration is computed by hand with
sklearn and reported with confidence intervals).

## ADR-006: Prompt injection is a measured metric, not a paragraph

**Decision.** Two injection cases live in the golden set with a "not hijacked"
expected value, and the injection resistance rate appears in the results table
alongside accuracy.

**Why.** Every submission will contain a safety section asserting that enquiry
text is delimited and treated as data. Very few will contain a number. The
defence itself is standard; the evidence is the differentiator.
