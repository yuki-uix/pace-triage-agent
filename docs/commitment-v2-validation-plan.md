# Commitment groundedness v2: preregistered validation plan

Status: the evidence-aware instrument, its 24 controlled variants and these
thresholds are frozen before any paid Judge call.

## What is being tested

Version 1 can only ask whether the customer's email supports a commitment.
Version 2 receives the same selected evidence as the drafting model and permits
specific operational steps when a public rule or the synthetic internal service
contract supports them. It must still reject invented case state, fixed SLAs,
policy outcomes, contact details and completed actions.

`data/commitment_v2_validation_set.jsonl` contains six enquiries with one reply
in each 0–2, 3–5, 6–8 and 9–10 band. The cases cover address servicing, disputed
billing, a medical claim, a formal complaint, direct-marketing opt-out and
suspected fraud. Every row freezes the deterministic evidence IDs so a later
selector change fails validation instead of silently changing the instrument.

## Blind review comes first

Prepare the anonymous packet locally:

```bash
.venv/bin/python -m src.commitment_v2_validation
.venv/bin/python -m evals.prepare_commitment_v2_blind_review
```

Give the reviewer only `.local/commitment_v2_validation/blind_packet.jsonl` and
the four bands in `COMMITMENT_V2_RUBRIC`; do not reveal the source set or
`blind_key.json`. Save exactly one independent band and reason for every blind
ID in `.local/commitment_v2_validation/blind_agent_scores.jsonl`:

```json
{"blind_id":"CR-01","band":2,"reason":"Material steps are supported; one qualification is missing."}
```

The paid runner refuses to start until all 24 blind rows are present and valid.

## Acceptance criteria

All conditions must hold and may not be relaxed after results are visible:

1. 24/24 Judge calls complete with no failure or thinking-disabled retry.
2. All 24 calls provide logprobs for continuous scoring.
3. Judge exact four-band agreement is at least 20/24 (83.3%).
4. Judge quadratic-weighted kappa is at least 0.85.
5. Every Judge prediction is within one band of the frozen expected label.
6. The independent blind review also has at least 20/24 exact agreement, kappa
   at least 0.85 and every item within one band.

Only after the blind file is frozen may an authorised paid run be made:

```bash
.venv/bin/python -m evals.commitment_v2_judge_validation
```

The runner writes the complete result even when a threshold is missed and exits
non-zero unless every acceptance condition passes. It refuses to overwrite a
previous paid result.

Passing permits commitment v2 and evidence-backed drafting to enter a new,
explicit comparison profile. It does not replace commitment v1, change existing
hard bars, or make `--evidence-backed` the pipeline default. Those changes need
a fresh full matrix and review of the commitment/actionability interaction.
