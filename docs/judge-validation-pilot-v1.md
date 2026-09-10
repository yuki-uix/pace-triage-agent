# Domain-judge challenge set: pilot v1

This records the first paid run before the middle-band examples were revised.
It is a pilot diagnosis, not the reported validation result.

## Run

- Judge: `glm-5.2`
- Completed: 24 of 24
- Judge-call failures: 0
- Calls with logprobs: 24 of 24
- Prompt tokens: 34,278
- Completion tokens: 44,099
- Reasoning tokens: 40,265

## Agreement

| measure | result |
|---|---:|
| Exact band | 54.2% (13/24) |
| Within one band | 95.8% (23/24) |
| Quadratic-weighted kappa | 0.811 |
| Spearman correlation | 0.881 |

Rows below are expected bands and columns are judge bands, ordered 0–2, 3–5,
6–8, 9–10.

| expected / judge | 0–2 | 3–5 | 6–8 | 9–10 |
|---|---:|---:|---:|---:|
| 0–2 | 6 | 0 | 0 | 0 |
| 3–5 | 6 | 0 | 0 | 0 |
| 6–8 | 1 | 2 | 2 | 1 |
| 9–10 | 0 | 0 | 1 | 5 |

## Adjudication

All six intended 3–5 examples contained multiple unsupported claims, which the
rubric itself places in 0–2. Three intended 6–8 examples also carried errors
more severe than their target band. Those are construction defects in the
challenge set, not evidence that the judge should be relabelled as correct.

Two mismatches remain useful judge probes: `JV-009-C` tests whether a disclaimer
causes the judge to overlook an unsupported industry generalisation, and
`JV-035-D` exposed a claim outside the original reference pack. The next dataset
revision preserves the former and removes the latter from the high-band reply.

The raw output remains local at `results/judge_validation.json` and is ignored
because it contains verbose model-generated reasons. This compact record keeps
the reproducible numbers and the human adjudication without presenting the
pilot as a passed validation.
