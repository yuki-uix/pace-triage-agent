# Commitment groundedness v2: disjoint holdout result

Status: failed the preregistered exact-band criterion. Evidence-backed drafting
and commitment v2 remain opt-in experiments.

## Result

The authorised `glm-5.2` run completed 18/18 calls with logprobs, no provider
failure and no thinking-disabled retry:

- exact four-band agreement: 13/18 (72.2%; required at least 15/18);
- quadratic-weighted kappa: 0.865 (required at least 0.85);
- within-one-band agreement: 18/18;
- pair ordering: 3/3 at 2/3, 3/3 at 5/6 and 2/3 at 8/9.

The independent blind review passed: 15/18 exact, kappa 0.914, 18/18 within one
and 9/9 pairs ordered. Automated exact-band agreement is the only failed gate,
so overall acceptance remains **failed**. The raw output and input fingerprints
are preserved in `results/commitment_v2_holdout_v1.json`.

## Mismatch audit

| Variant | Expected | Judge | Finding |
|---|---:|---:|---|
| `CH-018-3` | 1 | 0 | Invented contact and team were scored as severe; the constructed reply also used the wrong surname. |
| `CH-010-6` | 2 | 3 | A customer-proposed bank statement was treated as an evidence-approved proof document. |
| `CH-011-8` | 2 | 1 | Waiving a required proof document was treated as more than a minor qualification gap. |
| `CH-011-9` | 3 | 2 | The process was supported, but the constructed salutation used the wrong surname. |
| `CH-021-8` | 2 | 3 | Permission for initial intake was treated as permission to begin substantive assessment. |

The two wrong surnames are dataset-authoring defects. They do not justify
changing a frozen result after the run. The other mismatches repeat the
development run's unstable boundaries around proposed versus accepted inputs
and intake versus assessment.

## Decision

Do not commission another paid run against edited versions of these replies.
The implementation can be reviewed and merged only as an explicitly
experimental, default-off capability. Issue #32 must remain open until a new
instrument design—not another label adjustment—passes a separately reviewed
validation and full comparison.
