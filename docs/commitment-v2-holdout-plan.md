# Commitment groundedness v2: disjoint holdout plan

Status: frozen before blind review and before any holdout Judge call.

The first 24-item automated run missed its exact-band threshold and may now be
used only as development evidence. This holdout uses nine different enquiries:
ENQ-010, 011, 014, 018, 021, 024, 029, 036 and 039. None of the six development
enquiries or their reply variants appears here.

The 18 variants form nine minimal pairs: three at each 2/3, 5/6 and 8/9
boundary. Target scores 2, 3, 5, 6, 8 and 9 each occur three times. The set
specifically tests customer-proposed versus accepted inputs, intake versus case
logging or assessment, and soft assurances about outcomes evidence withholds.

## Acceptance criteria

All conditions must hold and may not be relaxed after results are visible:

1. 18/18 calls complete with no failure or thinking-disabled retry.
2. All 18 calls provide logprobs.
3. Exact four-band agreement is at least 15/18 (83.3%).
4. Quadratic-weighted kappa is at least 0.85.
5. Every prediction is within one band.
6. At least two of three pairs at each boundary are strictly ordered by the
   continuous Judge score.
7. The pre-Judge blind review has at least 15/18 exact agreement, kappa at least
   0.85, every item within one band and at least two ordered pairs per boundary.

Prepare locally, then give only the packet and frozen v2 rubric to a fresh
reviewer:

```bash
.venv/bin/python -m src.commitment_v2_holdout
.venv/bin/python -m evals.prepare_commitment_v2_holdout_review
```

No paid holdout run is authorised by preparing or reviewing this packet.
