# Actionability boundary validation v1

This is the paid run of the preregistered boundary plan in
`actionability-boundary-validation-plan.md`. The machine-readable output,
including every Judge reason and the evaluated acceptance criteria, remains at
`.local/actionability_boundary_validation_v5/judge_result.json`.

## Verdict

**The preregistered validation did not pass.** Exact band agreement was 13/18;
the frozen requirement was at least 14/18. The threshold is not relaxed after
the result and the labels are not changed in place.

## Run integrity

- Judge: `glm-5.2`
- Completed: 18 of 18
- Judge-call failures: 0
- Calls with logprobs: 18 of 18
- Prompt tokens: 19,961
- Completion tokens: 39,802
- Reasoning tokens: 37,369
- Thinking-disabled retries: 0

## Agreement

| measure | result | preregistered requirement | met |
|---|---:|---:|:---:|
| Exact band | 72.2% (13/18) | at least 77.8% (14/18) | no |
| Within one band | 100% (18/18) | 100% | yes |
| Quadratic-weighted kappa | 0.857 | at least 0.80 | yes |
| Spearman correlation | 0.870 | reported, no threshold | — |
| 2/3 pairs strictly ordered | 3/3 | at least 2/3 | yes |
| 5/6 pairs strictly ordered | 3/3 | at least 2/3 | yes |
| 8/9 pairs strictly ordered | 2/3 | at least 2/3 | yes |

Rows are expected bands and columns are Judge bands.

| expected / Judge | 0–2 | 3–5 | 6–8 | 9–10 |
|---|---:|---:|---:|---:|
| 0–2 | 2 | 1 | 0 | 0 |
| 3–5 | 0 | 5 | 1 | 0 |
| 6–8 | 0 | 1 | 3 | 2 |
| 9–10 | 0 | 0 | 0 | 3 |

## Mismatch diagnosis

| variant | expected | Judge | diagnosis |
|---|---:|---:|---|
| `AB-002-3` | 3–5 | 6–8 | The Judge treated receiving later instructions as a status transition, despite the 3–5 band explicitly covering a hand-off that cannot yet carry out the main request. This is a Judge boundary error. |
| `AB-008-2` | 0–2 | 3–5 | The reply names only unlocatable digital facilities and an unnamed form. Whether that counts as no usable first step or a weak hand-off remains genuinely close to the 2/3 boundary. |
| `AB-015-6` | 6–8 | 9–10 | The Judge inferred that the customer would receive the findings, although the reply never promises a result notification. This is a failure to enforce “customer-observable”. |
| `AB-021-6` | 6–8 | 3–5 | The reply lacks both a usable pre-notification route and a post-submission status. Under the clarified two-material-gap rule, the lower Judge band is defensible and the expected label is likely generous. |
| `AB-035-8` | 6–8 | 9–10 | Processing an opt-out internally is not observable to the customer. The Judge treated an internal action as a customer-visible completion state. |

The `ABP-035` pair tied at 0.900, so the Judge did not distinguish “process the
opt-outs” from an explicit confirmation that also states when scheduled
messages stop. The boundary still met its preregistered two-of-three ordering
minimum, but the tie is operationally important.

## Input fingerprints

| input | SHA-256 |
|---|---|
| `data/actionability_boundary_set_v4.jsonl` | `6dbd23bb5bff9225b5caf2d65d0044bddeead97e534b6226f67690a76c29be60` |
| `docs/actionability-boundary-validation-plan.md` | `746deef306990c39805de3d012c5ed3b95c5e9f41770f756529973c2902cb696` |
| `evals/metrics/judged.py` | `5e0e4dcc59e4a080be0d98f5a59108de2268361a20409168e14c2a20a82ddb24` |
| local blind scores | `fb9d7cf854db0159a258adb1a7baa92122940d72abc08fcb3cd0df2403bab11f` |

## Consequence

Actionability remains experimental and must not be added to the production
composite or hard bars. A future instrument revision should sharpen the phrase
“customer-observable”, separate instructions from actual task execution, and
ensure every independent customer request is counted before commissioning a
new preregistered validation. This failed result must remain visible rather
than being replaced by a tuned rerun.
