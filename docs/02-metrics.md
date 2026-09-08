# Metrics

## Task quality

| Metric | Implementation | Type |
|---|---|---|
| Case-type accuracy / per-class F1 | Custom `BaseMetric`, no LLM. Emits a confusion matrix. | Deterministic |
| Priority accuracy | Same metric class. Reported separately for URGENT. | Deterministic |
| Entity groundedness | Extract policy numbers, amounts, dates, names from draft; assert subset of enquiry entities. | Deterministic |
| Commitment groundedness | `GEval` — does the draft promise anything the enquiry does not support? | Judge |
| Tone match | `GEval` with an explicit rubric; urgent = formal/efficient, routine = warm/helpful. | Judge |
| Summary quality | `GEval`, scored only for length discipline and factual containment. | Judge |
| Refusal correctness | Binary, per designated case. | Deterministic |
| Injection resistance | Binary, per designated case. | Deterministic |

Evaluation flow is a `DAGMetric`: refusal cases branch out before draft
evaluation, so a correctly-refused enquiry is never penalised for having no
draft.

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
