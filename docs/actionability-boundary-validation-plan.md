# Actionability boundary validation: preregistered plan

Status: instrument v2 and dataset v4 frozen before any Judge score exists for
`data/actionability_boundary_set_v4.jsonl`.

The original `data/actionability_boundary_set.jsonl` is retained as v1. Its
first blind review produced 9/18 exact-band agreement while ordering all nine
minimal pairs correctly. Before any paid call, four ambiguous lower-side
replies were revised in v2; no Judge result was observed or used in that
revision.

The v2 blind review then achieved 12/18 exact-band agreement, 18/18 within one
band, quadratic-weighted kappa 0.829 and correct ordering for all nine pairs.
Its six disagreements exposed two repeated rubric ambiguities rather than six
independent label disputes. Before any paid boundary run, instrument v2 made
the existing control points explicit: a request for later instructions belongs
in 3–5, and a promise to contact without an observable trigger or date cannot
reach 9–10. This clarification changes the rubric fingerprint, so the earlier
24-row paid pilot remains historical evidence for instrument v1 and is not
silently treated as a validation of instrument v2.

After that clarification, a fresh blind review reached 15/18 exact-band
agreement, 18/18 within one band, kappa 0.914 and correct ordering for all nine
pairs. The final dataset v3 revises only the three remaining replies so their
intended missing control point is explicit. Dataset v1 and v2 remain preserved;
no paid boundary result existed during any revision.

The v3 adjudication found that three expected labels contradicted the rubric:
one hand-off already initiated a defined review, one result promise satisfied
the observable-status control point, and one high-band reply omitted a second
customer request. Dataset v4 rewrites those replies rather than changing labels
and collapsing the preregistered boundary pairs. Earlier versions remain
preserved and no paid boundary result was available during the change.

## Purpose

The first balanced pilot established broad four-band ordering but exposed a
tendency to promote 6–8 replies into 9–10. This follow-up tests the exact
transitions at 2/3, 5/6 and 8/9 with minimally different reply pairs.

The set contains 18 variants: three matched pairs at each boundary. Target
scores are 2, 3, 5, 6, 8 and 9, with three examples at each score. Paired
replies share one enquiry and differ only by the operational detail intended to
cross that boundary.

## Acceptance criteria

All conditions must hold; none may be waived after viewing results:

1. 18/18 Judge calls complete, with no failed or thinking-disabled retry.
2. Continuous scoring via logprobs is present for 18/18 calls.
3. Exact four-band agreement is at least 14/18 (77.8%).
4. Quadratic-weighted kappa is at least 0.80.
5. Every prediction is within one band of the frozen expected label.
6. At least two of three matched pairs at each boundary are ordered correctly:
   the upper-side reply must receive a strictly higher continuous score than its
   paired lower-side reply.

Failure of any condition keeps actionability experimental. Passing all
conditions supports, but does not automatically perform, promotion into the
production composite; that remains a separate reviewed decision.

## Blind review requirement

Before the paid run, an independent reviewer must receive only shuffled opaque
IDs, enquiry text, draft replies and the frozen rubric. The reviewer must not
see target scores, expected bands, pair membership, boundary-change notes or
results from the first pilot. Disagreements are adjudicated before the paid run
and preserved as a new labelled revision rather than silently overwritten.
