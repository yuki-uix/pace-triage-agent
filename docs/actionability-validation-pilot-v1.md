# Actionability judge challenge set: pilot v1

This is the first paid run of the 24-variant balanced actionability diagnostic.
The machine-readable output, including every Judge reason, remains local at
`.local/actionability_validation/actionability_judge_result.json`.

No numeric acceptance threshold was declared before this run. The measurements
are therefore evidence about Judge behaviour, not a retrospective pass/fail
claim.

## Independent review before the paid run

An isolated Agent received only an opaque, shuffled packet containing the
enquiry and draft reply, plus the actionability rubric. It could not read the
expected bands, variant IDs, user labels, Judge output or private blind key.
After unblinding, all 24 assigned bands matched the provisional expected bands.
This confirms that the broad band anchors are unambiguous to that reviewer; it
does not substitute for independent human annotation.

## Run

- Judge: `glm-5.2`
- Completed: 24 of 24
- Judge-call failures: 0
- Calls with logprobs: 24 of 24
- Prompt tokens: 21,249
- Completion tokens: 33,310
- Reasoning tokens: 30,663
- Thinking-disabled retries: 0

## Agreement

| measure | result |
|---|---:|
| Exact band | 83.3% (20/24) |
| Within one band | 100% (24/24) |
| Quadratic-weighted kappa | 0.941 |
| Spearman correlation | 0.947 |

Rows are expected bands and columns are Judge bands, ordered 0–2, 3–5, 6–8,
9–10.

| expected / Judge | 0–2 | 3–5 | 6–8 | 9–10 |
|---|---:|---:|---:|---:|
| 0–2 | 6 | 0 | 0 | 0 |
| 3–5 | 1 | 5 | 0 | 0 |
| 6–8 | 0 | 0 | 3 | 3 |
| 9–10 | 0 | 0 | 0 | 6 |

Both endpoint bands were separated perfectly. All four misses were adjacent;
there were no two-band or three-band errors. Three of the four disagreements
were 6–8 examples promoted into 9–10, indicating that the Judge is generous at
the upper-middle boundary.

## Mismatch adjudication

| variant | expected | Judge | review |
|---|---:|---:|---|
| `AV-001-B` | 3–5 | 0–2 | “Get in touch” is circular because the customer already emailed. The blind reviewer treated the partial explanation and offer of review as enough for 3–5; the Judge's 0–2 decision is also rubric-defensible. Keep the conservative expected label visible rather than relabelling after the run. |
| `AV-008-C` | 6–8 | 9–10 | The submission route is complete, but “the team will review” is not a customer-facing completion or missing-document notification. The expected 6–8 label remains the better fit to the stated high-band requirement. |
| `AV-015-C` | 6–8 | 9–10 | The reply says the team will call “in the afternoon” but supplies neither a date nor a triggering completion event. The Judge treated the customer's preferred time of day as sufficient timing; the expected label remains a deliberate boundary probe. |
| `AV-021-C` | 6–8 | 9–10 | The claim route is strong, but the pre-admission contact channel and post-submission status are absent. The Judge overlooked those omissions; the expected 6–8 label remains appropriate. |

## Input fingerprints

| input | SHA-256 |
|---|---|
| `data/actionability_validation_set.jsonl` | `3c37d2bb8e0092273a1154aadc2ea67bbd0c8509b571fa96a636eb3c032df6f2` |
| `evals/metrics/judged.py` | `4349a9456201816d6fe7e91f1f889ec5e51a39a066c09d8208a5838bce581e62` |
| `.local/actionability_validation/blind_agent_scores.jsonl` | `108c076293266f35b20eeb56d674f351549803470a56018b8dd03e75cfe39e68` |

## Interpretation

The run provides strong evidence that the Judge preserves the intended ordinal
ordering on clear band anchors: weighted agreement is high, every example is
within one band, endpoint separation is perfect and continuous scoring worked
on every call. The main weakness is upper-middle calibration, not catastrophic
misclassification.

The set is intentionally easy to interpret and therefore does not establish
production reliability by itself. A stronger follow-up should predeclare its
acceptance threshold, add difficult examples around the 2/3, 5/6 and 8/9 score
boundaries, and obtain labels from an independent human reviewer. Until then,
actionability remains experimental and outside the production composite and
hard bars.

After this run, a separate unpaid boundary review exposed ambiguous wording at
the 3–5/6–8 and 6–8/9–10 transitions. The rubric was clarified as instrument
v2, changing its fingerprint. Consequently, this paid result remains evidence
for instrument v1 and must not be presented as validation of the current v2
instrument.
