# Commitment groundedness v2: validation run 1

Status: failed the preregistered exact-band criterion. The instrument remains
experimental and no default or comparison profile is changed.

## Result

The authorised run used `glm-5.2` and completed all 24 cases:

- completed calls: 24/24, with no failure or thinking-disabled retry;
- calls with logprobs: 24/24;
- exact four-band agreement: 19/24 (79.2%; required at least 20/24);
- quadratic-weighted kappa: 0.929 (required at least 0.85);
- within-one-band agreement: 24/24.

The blind-review criteria also passed: 22/24 exact, kappa 0.969 and every item
within one band. Because the automated exact-band criterion missed, the overall
acceptance is **failed**. The raw result and all input fingerprints are preserved
in `results/commitment_v2_validation_v1.json`.

## Mismatches

| Variant | Expected | Judge | Interpretation |
|---|---:|---:|---|
| `CV2-009-C` | 2 | 3 | Judge treated the customer's proposed bank statement as a supported proof-of-address document. |
| `CV2-016-C` | 2 | 3 | Judge treated evidence submission and case logging as equivalent triggers for the reference. |
| `CV2-023-B` | 1 | 0 | The invented address plus assurance about originals was treated as a severe unsupported route/outcome. |
| `CV2-023-C` | 2 | 3 | Judge treated permission to begin intake as permission to begin assessment. |
| `CV2-040-B` | 1 | 0 | A soft recovery assurance was treated as an unsupported outcome because the evidence expressly says not to promise recovery. |

Two disagreements, `CV2-016-C` and `CV2-023-B`, were also independently flagged
by the fresh blind reviewer. That is evidence that those frozen expected labels
were weak, but changing them after seeing the Judge output would make a passing
result post hoc. This run therefore remains failed exactly as preregistered.

## Next decision

Do not rerun this set and do not relax 20/24. A subsequent validation must use a
separately frozen, disjoint holdout set. It should sharpen three boundaries:

1. a customer's proposed input versus an internally accepted input;
2. intake, case logging and substantive assessment as distinct states; and
3. a soft assurance about an outcome that the evidence explicitly withholds.

That holdout needs a new blind review before another paid Judge run. Only a pass
there can unblock an evidence-backed comparison profile.
