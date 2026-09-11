# Actionability held-out validation: preregistered plan

Status: instrument v3 and the held-out dataset are frozen before any Judge call.

## Separation from development data

The failed boundary run used ENQ-001, 002, 008, 009, 015, 021, 022, 028 and
035. Its errors were used to clarify the rubric, so none of those enquiries or
reply variants may appear in this validation. The held-out set uses ENQ-003,
004, 010, 014, 016, 023, 029, 030 and 036.

The 18 variants form nine minimal pairs: three at each of the 2/3, 5/6 and 8/9
boundaries. Target scores 2, 3, 5, 6, 8 and 9 each occur three times.

## Acceptance criteria

All conditions must hold and may not be relaxed after results are visible:

1. 18/18 calls complete with no failure or thinking-disabled retry.
2. All 18 calls provide logprobs for continuous scoring.
3. Exact four-band agreement is at least 14/18 (77.8%).
4. Quadratic-weighted kappa is at least 0.80.
5. Every prediction is within one band of the frozen expected label.
6. At least two of three pairs at each boundary are strictly ordered by the
   continuous Judge score.
7. The isolated blind review completed before the paid run has at least 14/18
   exact-band agreement, kappa at least 0.80, every item within one band and all
   nine pairs strictly ordered.

Passing supports promotion of actionability into a separately reviewed shadow
composite. It does not authorize changing the existing production weights or
hard bars without a full comparison run.
