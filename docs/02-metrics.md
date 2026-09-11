# Metrics

## Task quality

| Metric | Implementation | Type |
|---|---|---|
| Case-type accuracy / per-class F1 | Custom `BaseMetric`, no LLM. Emits a confusion matrix. | Deterministic |
| Priority accuracy | Same metric class. Reported separately for URGENT. | Deterministic |
| Entity groundedness | Extract policy numbers, amounts, dates, names from draft; assert subset of enquiry entities. Detection reuses the recognizers in `src/redaction.py`, so one class of data has one detection path. | Deterministic |
| Commitment groundedness | `GEval` — does the draft promise anything the enquiry does not support? | Judge |
| Tone match | `GEval` with an explicit rubric; urgent = formal/efficient, routine = warm/helpful. | Judge |
| Summary quality | `GEval`, scored only for length discipline and factual containment. | Judge |
| Actionability | Experimental meta-evaluation only: does a safe reply give the customer a concrete path forward without substituting an invented SLA for a next step? It remains outside the 2x2 matrix until blind human validation. | Judge |
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

### Actionability is not commitment volume

`commitment groundedness` asks whether an undertaking is supported;
`actionability` asks whether the customer can move forward without guessing. A
reply that only says “we will check” can score well on commitment safety and
poorly on actionability. An invented three-day resolution can sound decisive
and still score poorly because unsafe certainty is not an executable path.

The experimental workflow freezes the human column before making its fifteen
judge calls. Until that agreement is measured, actionability is excluded from
`JUDGED_METRICS`, the draft composite and every hard bar. Promotion requires a
separate reviewed change and a deliberate rerun of the paid 2x2 comparison.

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

- **Latency** — median and p95, measured in a dedicated serial run, first call
  discarded. Reported per stage, not just end-to-end, since the two stages are
  independently swappable.
- **Cost per invocation** — token counts × published prices, computed per stage.
- **Failure counts** — schema validation failures, retry exhaustion, refusals to
  respond. Three separate counters. These never vanish into an accuracy
  denominator.

## Pass/fail bar

Thresholds are derived from cost of error, not from what sounds impressive.
They are deliberately asymmetric.

| Metric | Bar | Justification |
|---|---|---|
| Entity groundedness | ≥ 99% | A fabricated policy number or amount can reach a customer if a reviewer is moving fast. Near-zero tolerance. |
| URGENT recall | ≥ 95% | A missed urgent complaint at a licensed insurer carries regulatory and escalation cost. False positives merely waste reviewer attention. |
| Commitment groundedness | ≥ 98% | A fabricated SLA is a contractual exposure, not a quality defect. |
| Injection resistance | 2/2 | With two cases the metric is binary; any failure blocks. |
| Refusal correctness | 2/2 | Same. |
| Case-type accuracy | ≥ 80% | Every output is human-reviewed before use. Misclassification costs reviewer seconds, and the confidence score routes low-certainty cases to closer scrutiny. A high bar here would be optimising the cheap failure. |
| Schema failure rate | ≤ 2% | Above this the output contract is not load-bearing and the human queue becomes unreliable. |

The shape matters more than the numbers: **the bar is highest where a human
reviewer is least likely to catch the error**, and lowest where review is
reliable. Any threshold defended by comparison to a benchmark rather than to a
consequence has been set wrongly.

## Variance

LLM outputs are not reproducible even at temperature 0. Key metrics are run three
times and reported as mean ± standard deviation. If time runs short, a single
run is acceptable **provided the write-up says so** and does not present the
numbers as stable.
