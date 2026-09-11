# Actionability held-out validation v1

This is the paid run of the preregistered, disjoint held-out plan in
`actionability-holdout-validation-plan.md`. The machine-readable output,
including every Judge reason and evaluated acceptance criterion, remains local
at `.local/actionability_holdout_v1/judge_result.json`.

## Verdict

**Instrument v3 passed every preregistered acceptance criterion.** It is
eligible for an explicitly selected shadow composite. This result does not
change the recorded 2x2 comparison, its production weights or its hard bars.

## Run integrity

- Judge: `glm-5.2`
- Completed: 18 of 18
- Judge-call failures: 0
- Calls with logprobs: 18 of 18
- Prompt tokens: 23,222
- Completion tokens: 41,162
- Reasoning tokens: 38,391
- Thinking-disabled retries: 0

The held-out enquiries (ENQ-003, 004, 010, 014, 016, 023, 029, 030 and 036)
do not overlap the development boundary enquiries.

## Agreement

| measure | result | preregistered requirement | met |
|---|---:|---:|:---:|
| Exact band | 94.4% (17/18) | at least 77.8% (14/18) | yes |
| Within one band | 100% (18/18) | 100% | yes |
| Quadratic-weighted kappa | 0.970 | at least 0.80 | yes |
| Spearman correlation | 0.963 | reported, no threshold | — |
| 2/3 pairs strictly ordered | 3/3 | at least 2/3 | yes |
| 5/6 pairs strictly ordered | 3/3 | at least 2/3 | yes |
| 8/9 pairs strictly ordered | 3/3 | at least 2/3 | yes |

Rows are expected bands and columns are Judge bands.

| expected / Judge | 0–2 | 3–5 | 6–8 | 9–10 |
|---|---:|---:|---:|---:|
| 0–2 | 3 | 0 | 0 | 0 |
| 3–5 | 0 | 6 | 0 | 0 |
| 6–8 | 0 | 1 | 5 | 0 |
| 9–10 | 0 | 0 | 0 | 3 |

The isolated blind review completed before the paid run also passed its frozen
gate: 18/18 exact-band agreement, quadratic-weighted kappa 1.000, every item
within one band and all nine pairs strictly ordered.

## The one mismatch

`AB-014-6` was labelled 6–8 and scored 0.5 (3–5). The response says no action
is required and identifies the billing team, but evidence and its reply channel
are only conditional, and it never says when or how the customer will receive
the review result. The Judge counted these as two material control-point gaps.
This is adjacent-band disagreement, does not reverse its minimal pair, and is a
defensible strict reading rather than evidence of a broken instrument.

## Input fingerprints

| input | SHA-256 |
|---|---|
| `data/actionability_boundary_holdout_v1.jsonl` | `6d0575dd171c6c701ac0f23ac21b9e445cd78ecf9dfbab471cd818edd29a1028` |
| `docs/actionability-holdout-validation-plan.md` | `f29da694a6c7c6e8c33be08028edf48595f8d0a177c7cba951b66085e7b56431` |
| `evals/metrics/judged.py` | `71622a48bf1c0d0cd95834983687527bb79631e404ad6f9787f6f91c96b3d2d0` |
| local blind scores | `08f3f4ef1e91c6e030b6d2503a45a9b560527d910f3861f3a2dcb0e7b74187d0` |

## Consequence

The metric is no longer experimental-only. It may be run in the
`shadow-actionability-v1` comparison profile, with the recorded profile kept
stable for historical reproducibility. Promotion beyond shadow status requires
one full matrix run under the frozen shadow profile and review of whether the
new dimension changes model ranking or exposes systematic low-actionability
cases.
