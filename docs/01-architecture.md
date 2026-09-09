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

**Exception to document, not implemented.** If data residency requirements
apply, the inference boundary would need redacting too, with placeholder
substitution and re-insertion after generation. That is discussed in the write-up
and deliberately not built: it costs draft quality, and the position is narrower
than it is usually stated. **PDPO section 33, the cross-border transfer
restriction, has never been brought into force**, so there is no statutory bar on
transferring personal data out of Hong Kong. What applies is the PCPD's
non-binding guidance, its 2022 recommended model contractual clauses, and the
data user's standing obligations under the data protection principles, which
follow the data to a processor wherever it sits. Inference for this case study
ran against a Beijing-region endpoint (ADR-007).

**The operator, and why the detection step was removed.** The first
implementation ran Presidio over each trace field and encrypted the entities it
found. Measured, it failed open: in a trace whose prompt was a system message
plus a delimited enquiry, the policy number, phone number, email address and
amount were all encrypted and the customer's name was not, because spaCy's NER
is context-sensitive and misses in a long prompt what it finds in a short
string. A compliance boundary that depends on a recall rate is not a boundary.

The gate is now structural rather than statistical: every field on the trace
entry that is not explicitly classified as non-sensitive is encrypted in full,
with the classification derived from the type so an unclassified new field fails
the tests instead of quietly reaching disk. Counts, timings, model names and the
confidence method stay readable, which is what debugging throughput needs;
reading content requires the key.

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

## ADR-007: Models under test, and the endpoint they run on

**Decision.** The two models under test are `qwen3.7-flash-2026-07-15` and
`qwen3.7-plus-2026-05-26`, served by Alibaba Cloud Model Studio. The dataset
generator is `kimi-k3` and the judge is `deepseek-v4-pro`.

**Why these two.** They are the cheap and mid tiers of the same generation. Same
generation matters: pairing the newest flash with an older plus would confound
the tier difference with a generation difference, and the comparison would
answer neither question.

**Why the dated snapshots rather than `qwen3.7-flash`.** The floating alias can
be repointed by the provider at any time. If that happened mid-experiment the
golden set would still be frozen, the code unchanged, and the numbers would move
with no error and no signal. Pinning the snapshot is what makes the frozen
golden set mean anything.

**Why these three families.** The spec requires the generator and the judge to
come from a different family than either model under test, so that shared priors
cannot inflate accuracy and self-preference cannot favour a candidate. Qwen,
Kimi and DeepSeek are three distinct families, and generator and judge differ
from each other as well, so the generator's priors do not leak into scoring.

**Rejected: `ZHIPU/GLM-5.3` as generator, `MiniMax/MiniMax-M3` as judge.** Both
appear in the account's model list but return
`400 The product is not activated`. The model list is not an entitlement list —
this was found by calling them, not by reading the catalogue.

**Endpoint and residency.** The account's key is a Beijing-region key: the
Singapore endpoint returns 401 and `https://dashscope.aliyuncs.com` returns 200.
Inference for this case study therefore runs in mainland China.

For this exercise nothing personal is at stake — the dataset is Faker-generated
and contains no real PII by construction. For a real Hong Kong insurer the
position is narrower than it is often stated: **PDPO section 33, the cross-border
transfer restriction, has never been brought into force**, so as of 2026 there is
no statutory bar on transferring personal data out of Hong Kong. The applicable
constraints are the PCPD's non-binding guidance and its 2022 recommended model
contractual clauses, plus the data user's standing obligations under the data
protection principles, which apply to a processor wherever it sits.

The honest statement for the write-up is therefore not "this is compliant" but:
inference ran against a mainland-China endpoint; a production deployment would
put the endpoint choice, the processor contract terms, and the redaction boundary
of ADR-004 in front of the insurer's compliance function before go-live.
Switching to a Singapore workspace was considered and rejected for now, because
the model catalogue is entitlement-scoped per account and re-verifying it would
invalidate the selection above.

## ADR-008: Thinking is disabled for triage, and the on/off gap is reported

**Decision.** Triage calls set `enable_thinking: false`. The comparison reports
both settings rather than quietly choosing one.

**Why.** Measured, not assumed. Five enquiries, one call each, `max_tokens=2048`:

| Model | Thinking | Output tokens (n=5) | Median | Range |
|---|---|---|---|---|
| `qwen3.7-flash-2026-07-15` | on | 391, 786, 210, 1266, 727 | 727 | 210-1266 |
| `qwen3.7-flash-2026-07-15` | off | 19, 19, 22, 22, 21 | 21 | 19-22 |
| `qwen3.7-plus-2026-05-26` | on | 472, 643, 650, 1205, 672 | 650 | 472-1205 |
| `qwen3.7-plus-2026-05-26` | off | 14, 19, 15, 17, 14 | 15 | 14-19 |

Three things follow, and the second is the one that matters.

1. Thinking costs roughly 35-43x the output tokens on a task whose entire answer
   is two enum values. Reasoning tokens bill as output.
2. **The cheap model does not think less.** Flash's median reasoning volume is
   *higher* than plus's, and its spread is wider. Flash is cheaper only by its
   per-token price, not by the tokens it emits, and at p95 it is the worse of
   the two. ADR-001 assumed a cheap model would be cheap at triage; that premise
   survives only with thinking off, and the write-up must say so.
3. With thinking on, the token count varies 6x across five ordinary enquiries.
   Any latency or cost figure quoted as a single number would be meaningless;
   `docs/02-metrics.md` already requires p95, and this is why.

**Cost.** Disabling thinking may cost classification accuracy on the ambiguous
records. That is measurable on the golden set and is reported, not assumed away.

**A trap this uncovered.** `glm-5.2` with `max_tokens=200` returned an empty
string and 200 reasoning tokens — the cap was consumed entirely by thinking. A
harness that treated an empty response as a soft failure would silently drop the
record. The output contract counts it as a schema failure instead, loudly.
