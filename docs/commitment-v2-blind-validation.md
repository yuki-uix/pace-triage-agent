# Commitment groundedness v2: blind validation

The independent review happened before any paid Judge call. Reviewers received
only the shuffled enquiry, reply, selected evidence and the frozen v2 rubric;
the expected bands, author rationale and private key were withheld.

## Development review

The first frozen construction (`dd3f1db`) did not pass:

- exact band agreement: 14/24 (58.3%);
- quadratic-weighted kappa: 0.789;
- within-one-band agreement: 22/24 (91.7%).

The mismatches exposed a construction error: several B- and C-band replies
contained unsupported fixed SLAs even though the 0–2 rubric explicitly treats a
fixed unsupported timeframe as a severe failure. No Judge output was available.
The rubric and preregistered thresholds were left unchanged. Ten replies were
rewritten in `2aef70b` so band B contains softer assurances or invented routes
and band C contains only a limited qualification gap.

## Fresh blind review of the revised set

A different reviewer, with no access to the first scores or the revision diff,
reviewed a newly shuffled packet. The revised set passed every preregistered
blind criterion:

- exact band agreement: 22/24 (91.7%; required at least 20/24);
- quadratic-weighted kappa: 0.969 (required at least 0.85);
- within-one-band agreement: 24/24 (required 24/24).

The local score file is intentionally not committed. Its SHA-256 is
`d620ed2c8c83148588bf13d54a842d8222e65e0c57664f0427c1e449f0ba7a21`;
the paid runner includes that file, the blind key, both evidence packs, the
dataset, the rubric and the preregistered plan in its input fingerprints.

## Boundary

This establishes that the expected labels are independently intelligible. It
does not validate the automated Judge. The 24-call Judge run remains blocked
until explicitly authorised, and commitment v2 remains experimental until that
run passes all criteria in
[`commitment-v2-validation-plan.md`](commitment-v2-validation-plan.md).
