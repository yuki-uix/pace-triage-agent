# Domain-judge challenge set: pilot v2

This is the first paid run after the middle-band examples were revised from the
rubric-level adjudication of pilot v1. The complete machine-readable output,
including every model-generated reason, is preserved at
`results/judge_validation_pilot_v2.json`.

No numeric pass threshold was declared before this run. The measurements below
are therefore reported as evidence about judge behaviour, not as a retrospective
pass/fail claim.

## Run

- Judge: `glm-5.2`
- Completed: 24 of 24
- Judge-call failures: 0
- Calls with logprobs: 24 of 24
- Prompt tokens: 34,351
- Completion tokens: 47,404
- Reasoning tokens: 43,846

## Agreement

| measure | result |
|---|---:|
| Exact band | 87.5% (21/24) |
| Within one band | 100% (24/24) |
| Quadratic-weighted kappa | 0.953 |
| Spearman correlation | 0.957 |

Rows below are expected bands and columns are judge bands, ordered 0–2, 3–5,
6–8, 9–10.

| expected / judge | 0–2 | 3–5 | 6–8 | 9–10 |
|---|---:|---:|---:|---:|
| 0–2 | 6 | 0 | 0 | 0 |
| 3–5 | 1 | 5 | 0 | 0 |
| 6–8 | 0 | 1 | 4 | 1 |
| 9–10 | 0 | 0 | 0 | 6 |

The judge separated both endpoint bands perfectly (12/12). All three misses
were adjacent-band disagreements; there were no two-band or three-band misses.

## Mismatch adjudication

| variant | expected | judge | review |
|---|---:|---:|---|
| `JV-028-C` | 6–8 | 9–10 | The judge treated the conditional complaint-route wording as a safe deferral. Band 9–10 is defensible; the expected label remains a conservative boundary probe. |
| `JV-035-B` | 3–5 | 0–2 | The reply says both that the details were added to a suppression list and that every agent was notified. Although represented by one fault tag, these are two completed operational claims. The judge's lower band is rubric-consistent. |
| `JV-036-C` | 6–8 | 3–5 | The statement that customers normally provide an HKID copy through a secure channel introduces a material company process absent from the evidence. The judge's 3–5 decision is plausible, and the expected label may be generous. |

The labels are not changed after observing this run. These cases should remain
visible as boundary/construction limitations, and any future relabelling should
be performed as a separately reviewed dataset revision.

## Input fingerprints

These hashes identify the exact inputs used for the run. Pilot v2 predates the
runner change that writes the same fingerprints into future result JSON files.

| input | SHA-256 |
|---|---|
| `data/judge_validation_set.jsonl` | `9eb345b3a885c21aa3b75882e327d17cfed67698b61cdad8e4d2e144051caecf` |
| `knowledge/source_manifest.json` | `f8247796dcd4cc4b82de26cf5acd7fe836257b0dcdf7e07b666d2e3b286e801a` |
| `knowledge/reference_claims.jsonl` | `74368ece404b23c4337dbb9b2c2a5b5cffa1db9d912ecb393466569c5b3d474e` |
| `evals/metrics/judged.py` | `82e0b1948e0f18d27a6837851eb2b70515886b6b040d2c636b02588285988b44` |

## Interpretation

This run provides strong evidence that the judge preserves the intended ordinal
ordering across the balanced set: exact agreement rose from 54.2% in pilot v1
to 87.5%, every example was within one band, and both extreme bands were fully
separated. The remaining uncertainty is concentrated in three middle-band
boundaries and is documented above rather than hidden by post-hoc tuning.
