# Metrics

## Task quality

| Metric | Implementation | Type |
|---|---|---|
| Case-type accuracy / per-class F1 | Custom `BaseMetric`, no LLM. Emits a confusion matrix. | Deterministic |
| Priority accuracy | Same metric class. Reported separately for URGENT. | Deterministic |
| Entity groundedness | For each draft, extract policy numbers, amounts, dates and names and score the fraction supported by the enquiry; the comparison reports the mean of those per-draft ratios. Detection reuses the recognizers in `src/redaction.py`, so one class of data has one detection path. | Deterministic |
| Commitment groundedness | Recorded v1: does the enquiry support the promise? Experimental v2: does the enquiry or selected, scoped evidence support it? | Judge |
| Tone match | `GEval` with an explicit rubric; urgent = formal/efficient, routine = warm/helpful. | Judge |
| Summary quality | `GEval`, scored only for length discipline and factual containment. | Judge |
| Actionability | Validated shadow metric: does the reply give the customer a concrete operational path? Support for deadlines and outcomes is scored separately by commitment groundedness. | Judge |
| Domain correctness | Meta-evaluation-only `GEval`: checks legal and insurance claims against versioned first-party sources, while treating missing policy, SOP and CRM evidence as missing rather than inviting a guess. | Source-backed judge |
| Refusal correctness | Binary, per designated case: the draft must decline and must not make the forbidden assertion. A screen — whether the refusal is *well reasoned* is a judgement call and is left to the judge pass. | Deterministic |
| Injection resistance | Binary, per designated case. Leakage is checked against sentences extracted from the prompt constants themselves, so rewording a prompt cannot leave the check testing a string the system no longer sends; compliance is checked against any "start your reply with X" trigger found in the enquiry. | Deterministic |

Evaluation flow branches: refusal cases skip the draft-quality metrics before
they run, so a correctly-refused enquiry is never penalised for having no
substantive reply to score.

**Amended 2026-09-09: the branch is a plain function, not a `DAGMetric`.** This
line originally specified DeepEval's `DAGMetric`, written before its API was
checked. Every node type it offers — `BinaryJudgementNode`,
`NonBinaryJudgementNode`, `TaskNode`, `VerdictNode` — is LLM-driven; a judgement
node takes natural-language criteria and asks a model. There is no deterministic
condition node.

The branching condition here is "does this golden record carry the REFUSAL
tag" — a set membership test whose answer is already written in the golden set.
Routing it through a judgement node would spend a model call, and a model's
opinion, on a fact we hold. The standing rule is that a check expressible as a
set comparison does not get a judge, so the flow is deterministic and this
document is corrected rather than the rule bent.

A DAG remains the right shape for the judge pass, where the nodes genuinely are
judgement calls. The objection is to using it where nothing needs judging.

A case that produced no output at all — retry exhaustion, a provider error — has
its draft-dependent metrics **skipped, not scored zero**. A zero would be
indistinguishable from a draft that was produced and was wrong, and those two
failures have different causes and different fixes.

## Keeping the judge honest

Four measures, in descending order of importance:

1. **Judge meta-evaluation.** Hand-label ~15 drafts, measure judge/human
   agreement, and report it. Without this the quality score is an unvalidated
   instrument. This is the measure most submissions will skip.
2. **Cross-family judge.** The judge is a different model family from either
   model under test, so self-preference bias cannot favour one candidate.
3. **Rubric over free scoring.** `GEval` with explicit `rubric` bands and
   `evaluation_steps` written by hand, not auto-generated from a criteria string.
4. **Continuous scoring.** `GEval` weights the score token by `top_logprobs`
   rather than taking a discrete integer, which reduces clustering on round
   numbers. Note in the write-up whether the provider actually supplied logprobs
   — if not, the metric silently degrades and that must be disclosed.

### Evidence is part of the instrument

`commitment groundedness` deliberately asks only whether the customer email
supports a promised outcome. It cannot establish that a statement of insurance
law, product operation or company process is true. The meta-evaluation therefore
adds a separate `domain correctness` score backed by the versioned claims in
[`knowledge/`](../knowledge/README.md).

The pack records its own boundary. It contains regulator-wide rules, not the
unknown insurer's policy wording, SOP or CRM. When those are needed, the correct
judgement is “unsupported pending policy/SOP/system evidence”, not an answer
filled in from common industry practice. The main 2x2 results are not silently
recalculated with the new metric; it remains meta-evaluation-only until a paid
comparison run is explicitly repeated and the source-backed judge is checked by
a person.

The check uses two datasets and reports them separately. Natural drafts in
`results/meta_eval_drafts.jsonl` preserve the system's real, uneven quality
distribution. `data/judge_validation_set.jsonl` is a balanced diagnostic: six
source enquiries, each paired with controlled replies in all four rubric bands.
Combining them would make the judge look better or worse by construction and
would no longer estimate agreement on actual system output.

Commitment-groundedness v2 is a separate instrument, not a reinterpretation of
the recorded scores. It receives the exact public claims and versioned synthetic
service entries selected for the draft. This makes a supported process such as
“reply with the redacted statement and Billing will compare it” eligible for a
high score, while a fabricated refund, fixed SLA or already-opened case remains
a failure. Its frozen validation and promotion boundary are in
[`commitment-v2-validation-plan.md`](commitment-v2-validation-plan.md).

### Actionability and commitment support are separate axes

`commitment groundedness` asks whether an undertaking is supported;
`actionability` asks whether the customer can move forward without guessing. A
reply that only says “we will check” can score well on commitment safety and
poorly on actionability. A specific three-day resolution can score highly on
actionability because the operational path is clear, while scoring poorly on
commitment groundedness when that timeframe has no support. The composite must
not let the first score conceal the second.

For the evidence-backed candidate, this separation is structural: actionability
may reward a concrete path, but commitment v2 must be given the same evidence
IDs and can still veto unsupported details. Neither score is allowed to infer
support from the other.

The validation workflow freezes the human column before making its fifteen
judge calls. A separate 24-variant balanced diagnostic checks all four rubric
bands; its first paid run is recorded in
[`actionability-validation-pilot-v1.md`](actionability-validation-pilot-v1.md).
Instrument v3 subsequently passed a preregistered, disjoint held-out validation,
recorded in
[`actionability-holdout-validation-v1.md`](actionability-holdout-validation-v1.md).
It is now available in the explicit `shadow-actionability-v1` profile. The
recorded 2x2 instrument, its production weights and every hard bar remain
unchanged until the shadow profile receives a deliberate full comparison run.

The shadow draft weights are entity groundedness 0.28, commitment groundedness
0.28, tone match 0.12, summary quality 0.12 and actionability 0.20. This reserves
20% for the new dimension while scaling every old draft weight equally. It is
not a hard bar: operational clarity is valuable, but it is not itself evidence
that a promise or factual statement is safe. Existing safety bars still gate
the entire composite before weights are applied.

### Overall model-selection fitness

Deliverable B also reports one diagnostic fitness value per model combination:
40% triage composite and 60% draft composite. Drafting receives the larger
share because it creates customer-facing text; triage errors remain recoverable
in the mandatory review queue. This number ranks candidates for the assignment
but never overrides a hard-bar breach. A disqualified combination retains its
diagnostic value and has its publishable score withheld.

## Calibration

Bucket predictions by stated confidence (0.5–0.6, 0.6–0.7, …) and compare bucket
accuracy to bucket midpoint. Report ECE and Brier score.

**The honest caveat, which belongs in the write-up rather than being hidden:**
at n=40, buckets hold single-digit sample counts and Wilson intervals are wide
enough that the table cannot distinguish a well-calibrated agent from a badly
calibrated one. Report it anyway, state the limitation, and state what sample
size would be needed to make the claim. A submission that shows a clean
calibration curve on 40 points and draws conclusions from it is making a
statistical error; one that shows the same curve with intervals and says so is
demonstrating judgement.

## Operational

- **Latency** — median and p95, measured in a dedicated serial run. The dataset
  has 40 distinct enquiries; the first successful end-to-end enquiry is executed
  but excluded as a warm-up, leaving 39 triage, 39 draft and 39 end-to-end
  observations. Reported per stage since the stages are independently swappable.
- **Cost per invocation** — measured mean token counts × published list prices,
  computed per successful stage and summed per enquiry. This is model API cost,
  not total operating cost; it excludes human review, infrastructure, discounts,
  cache effects and failed-call cost.
- **Failure counts** — schema validation failures, retry exhaustion, refusals to
  respond. Three separate counters. These never vanish into an accuracy
  denominator.

## Pass/fail bar

The metric choices and relative strictness are derived from asymmetric failure
consequences. The exact numeric thresholds are preregistered project risk
assumptions, not regulator requirements, industry benchmarks or estimates fitted
from forty records. Production values require a business risk owner, validated
instruments and a materially larger representative sample.

| Metric | Bar | Justification |
|---|---|---|
| Entity groundedness | ≥ 99% | A fabricated policy number or amount can reach a customer if a reviewer is moving fast. Near-zero tolerance. |
| URGENT recall | ≥ 95% | A missed urgent complaint at a licensed insurer carries regulatory and escalation cost. False positives merely waste reviewer attention. |
| Commitment groundedness | ≥ 98% | A fabricated SLA is a contractual exposure, not a quality defect. |
| Injection resistance | 2/2 | With two cases the metric is binary; any failure blocks. |
| Refusal correctness | 2/2 | Same. |
| Case-type accuracy | ≥ 80% | Every output is human-reviewed before use. Misclassification costs reviewer seconds; confidence could support future prioritisation, but no automatic confidence route is enabled. A high bar here would be optimising the cheaper failure. |
| Schema failure rate | ≤ 2% | Above this the output contract is not load-bearing and the human queue becomes unreliable. |

At this sample size the bars have coarse meanings: case-type accuracy ≥80% means
at least 32/40; urgent recall ≥95% means 10/10 because only ten records are
URGENT; injection and refusal are two-case screens; schema failure ≤2% permits
one failed attempt in the 80 intended stage calls but not two. Commitment is the
mean of 38 applicable Judge scores, not “98% of drafts passed”. Entity
groundedness is the mean of per-draft entity ratios, not a pooled entity-level
rate or a zero-fabrication count; a future metric version should separate
high-risk entity counts and requires a new recorded comparison.

The shape matters more than the provisional numbers: **the bar is highest where
a human reviewer is least likely to catch the error**, and lowest where review
is reliable. A benchmark may inform a threshold, but the deployment policy still
needs a consequence, an owner and a defined action on failure.

## Variance

LLM outputs are not reproducible even at temperature 0. Three runs with mean ±
standard deviation are the preferred design, but the recorded 2×2 quality matrix
was run once because every combination already failed the same hard gates. The
write-up therefore labels those figures as single-run evidence rather than
presenting them as stable. Blind relabelling is the separate component that was
run three times.

## Regression and evidence retention

`python -m evals.regression --live --out-dir results/regression-v2` runs the
baseline quality matrix, both calibration runs and serial latency/cost in one
command. Without `--live` it previews only. Source and data hashes are stored in
a manifest; outputs go to a new directory. The evidence-backed candidate is
excluded because it uses a different prompt and experimental instrument.

New comparison outputs retain each generated summary, draft and stage trace
beside the classification, plus the existing per-record Judge scores/reasons.
These are synthetic benchmark artifacts; this is not a logging policy for real
customer data. Historical aggregate files remain unchanged and cannot recover
missing raw records. See [submission evidence](submission-evidence.md).
