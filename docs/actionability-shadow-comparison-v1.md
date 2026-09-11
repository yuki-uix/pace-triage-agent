# Actionability shadow comparison v1

This report applies the frozen `shadow-actionability-v1` profile to all four
model combinations in the 40-record golden set. Machine-readable results,
including per-record Judge reasons, are in
`results/comparison-shadow-actionability-v1.json`.

## Verdict

**The actionability metric passed its shadow operational check; the drafting
agent did not pass the production safety gate.** All four cells completed with
40/40 outputs and 38/38 applicable scores for each judged metric. However,
every cell breached entity and commitment groundedness, and both flash-draft
cells also failed refusal correctness.

No composite is published for a disqualified cell. Lowering a hard bar after
seeing the result would turn the gate into decoration.

## Run integrity

- Profile: `shadow-actionability-v1`
- Completed combinations: 4/4
- Produced outputs: 160/160
- Applicable actionability scores: 152/152
- Final-cell generation errors: 0
- Final-cell Judge errors: 0
- Cumulative Judge calls across the completed run and interrupted attempts: 773
- Calls returning logprobs: 769/773 (99.48%)
- Prompt tokens: 881,453
- Completion tokens: 2,125,162
- Reasoning tokens: 2,014,954
- Empty responses retried with thinking disabled: 4

The four empty initial responses did not become missing scores: their retry
responses supplied the final values. They remain disclosed because those extra
calls used a different reasoning setting.

## Matrix

| triage / draft | case type | urgent recall | entity groundedness | commitment groundedness | tone | summary | actionability |
|---|---:|---:|---:|---:|---:|---:|---:|
| flash / flash | 0.850 | 1.000 | 0.964 | 0.518 | 0.579 | 0.663 | 0.537 |
| flash / plus | 0.875 | 1.000 | 0.956 | 0.700 | 0.674 | 0.784 | 0.571 |
| plus / flash | 0.900 | 1.000 | 0.964 | 0.487 | 0.590 | 0.609 | 0.509 |
| plus / plus | 0.925 | 1.000 | 0.950 | 0.612 | 0.626 | 0.766 | 0.558 |

On the same generated outputs, adding actionability did not change draft
ranking:

| rank | combination | recorded-weight formula | shadow formula |
|---:|---|---:|---:|
| 1 | flash / plus | 0.799 | 0.753 |
| 2 | plus / plus | 0.755 | 0.716 |
| 3 | flash / flash | 0.705 | 0.672 |
| 4 | plus / flash | 0.688 | 0.652 |

These are sensitivity calculations, not publishable composites, because all
four cells are disqualified. The result supports the narrower engineering
finding that the draft model affects quality more than the triage model and the
plus draft is consistently better.

## Manual review of low actionability

Eighty-five of 152 replies scored below 0.6. Every one of their retained Judge
reasons was reviewed. The categories overlap because one reply commonly misses
several control points.

| recurring defect | low replies affected |
|---|---:|
| No customer-observable next status, trigger or usable timing | 78 |
| Hand-off only; customer still cannot perform the main request | 48 |
| Required input left unclear | 36 |
| Bare, unusable or placeholder channel | 28 |
| An independent request left unaddressed | 23 |

Fourteen enquiries were below 0.6 under every model combination: ENQ-004, 014,
015, 016, 017, 018, 023, 025, 026, 027, 032, 033, 034 and 037. This concentration
across models is evidence of a prompt/context limitation, not random Judge
noise. They are dominated by withdrawals, billing investigations, urgent
claims, complaint ownership and routing to another department—tasks that need
an insurer-specific service path the model was never given.

The reasons are mostly substantively sound. Typical failures include literal
placeholders such as `[Insert Phone Number]`, references to an unnamed portal or
form, `we will investigate` without stating how the customer learns the result,
and a hand-off that forces another round trip merely to obtain instructions.

## Why the safety failures need separate treatment

### Entity groundedness

The failures mix real fabrication with normalisation artifacts. Invented case
references and addresses such as `finance@example.com` are genuine defects.
Other flags are not: `3 Oct` becoming `3 October`, and `23 Jan` becoming
`23 January`, preserve an entity already present in the enquiry. A 0.99 hard
bar applied before canonical date normalisation therefore overstates some
failures. The detector must normalise equivalent dates before this score can be
used as a production gate.

### Commitment groundedness

The current Judge receives only the customer email and draft. It treats an
undertaking as supported only when the email already establishes it. As a
result, ordinary service actions—processing a valid request, sending a
confirmation, using a documented complaint timeline—can be penalised merely
because the customer did not state the insurer's operating procedure.

This is the main structural blocker. The repository's public reference pack
contains regulatory and general insurance facts, but deliberately contains no
insurer-specific form, channel, document checklist, SLA, refund procedure or
CRM state. The drafting prompt and commitment Judge therefore lack the exact
evidence needed to produce and recognise a concrete safe path. Actionability
rewards specificity while commitment groundedness rejects that specificity for
lack of supplied evidence.

The answer is not to merge the dimensions or weaken the 0.98 threshold. The
pipeline needs a versioned internal-service evidence contract, and both the
draft generator and commitment Judge must receive the relevant subset. Public
regulatory sources remain separate and cannot establish a fictional insurer's
operating procedure.

## Promotion decision

Actionability may remain in the shadow comparison profile. It must not yet
become the default production composite because the underlying drafts fail the
safety gate and the commitment gate lacks the evidence context required to
interpret operational promises fairly.

The next implementation milestone is evidence-backed drafting:

1. define a clearly labelled, versioned synthetic internal service catalogue
   for this case-study insurer;
2. route relevant catalogue entries into the drafting prompt;
3. give the same entries to commitment groundedness as evaluation context;
4. canonicalise equivalent date forms in entity groundedness;
5. validate the revised commitment instrument on controlled examples before
   paying for another full matrix.
