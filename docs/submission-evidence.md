# Submission evidence and limits

The assignment asks for code, synthetic inputs, a frozen golden set, evaluation
outputs and a short write-up. This index separates the experiments so that a
result from one prompt or Judge is not used to validate another.

| Experiment | Committed evidence | Scope and remaining gap |
|---|---|---|
| Baseline model selection | `results/comparison.json` | Four model combinations x 40 emails; aggregates, confusion matrices and gate breaches. Complete per-draft outputs and Judge scores/reasons from this historical run are absent. Summary means cannot be independently reconstructed. |
| Baseline calibration | `results/calibration.json` | Both models, individual predictions/confidences and reliability buckets. Historical runs used LOGPROBS, not the repaired fallback. |
| Baseline operations | `results/latency.json`, `results/latency-plus-flash.json` | Serial stage timings, token means and price metadata covering both models in both roles. No new live measurements accompany the code fix. |
| Natural-output Judge validation | `results/meta_eval_drafts.jsonl`, `results/meta_eval_judge.json`, `results/meta_eval_human_agreement.json` | Fifteen drafts and automated scores; aggregate human agreement and hashes. Raw human labels remain private, so independent recomputation needs the reviewer's packet. |
| Evidence-backed candidate | `results/assignment_demo_v1.json` | Five paired cases with drafts, scores, evidence IDs and human pair preferences. Not a held-out 40-case comparison; two preferred drafts still require edits. |
| Actionability shadow comparison | `docs/actionability-shadow-comparison-v1.md` | Separate prompt/metric profile; its machine result is not committed in this submission. Its table is supplementary and must not replace baseline evidence. |

## What changed after the recorded runs

The confidence fallback now counts support for the emitted case type, rather
than the largest vote count for any type. Every fallback response is validated;
malformed samples fail visibly. Python and the optional Node demo follow the
same rule. This fixes a counterexample where a CLAIM output received confidence
1.0 even though all independent votes said OTHER.

New baseline comparisons retain the generated summary, reply and stage trace
in `per_record`, alongside `judged_per_record` scores and reasons. The regression
entry point writes quality, calibration and serial operations to one fresh run
directory with source/data fingerprints. No historical number is relabelled as
a post-fix measurement.

## To close the remaining evidence gap

1. Recover the original baseline drafts and Judge records if the exact run was
   archived elsewhere. Verify their model, source version, IDs and aggregation
   before publishing them. A different shadow run is not a substitute.
2. Otherwise run the new baseline regression with explicit live execution and
   publish it as a new experiment. Preserve the historical report and report
   differences; do not describe the new output as recovered historical data.
3. Before promoting evidence-backed drafting, freeze its prompt/instrument and
   evaluate it on the full golden set, then a new blind holdout. Its five-case
   demo does not establish safety, calibration or model-selection superiority.

The current recommendation remains: no production release; Flash Triage / Plus
Draft is a conditional choice for the next validation run.
