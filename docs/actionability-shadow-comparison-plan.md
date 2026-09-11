# Actionability shadow comparison plan

Status: frozen before the first full `shadow-actionability-v1` comparison.

## Purpose

The held-out validation established that instrument v3 can distinguish the
intended actionability bands. This run asks a different question: what happens
when that metric is applied to the four real model combinations in the frozen
golden set?

The command is:

```bash
.venv/bin/python -m evals.compare \
  --shadow-actionability \
  --out results/comparison-shadow-actionability-v1.json
```

The run is deliberately separate from `results/comparison.json`. Scores from
the two profiles must not be compared as though they used the same instrument.
An interrupted run is continued with the same command plus `--resume`.
Completed cells are reused only after their output and judged-metric counts are
verified; an incomplete cell is rerun, not averaged with partial data.

## Frozen instrument

The profile adds `actionability` to the three recorded judged draft metrics.
It uses these draft weights:

| metric | weight |
|---|---:|
| Entity groundedness | 0.28 |
| Commitment groundedness | 0.28 |
| Tone match | 0.12 |
| Summary quality | 0.12 |
| Actionability | 0.20 |

Twenty percent is reserved for the added dimension; every previous draft
weight is multiplied by 0.8. Existing hard bars are unchanged and are applied
before the composite. Actionability is not a hard bar and cannot rescue a
combination that fails a safety gate.

## Expected scope and cost

The frozen set contains 40 enquiries, including 38 non-refusal records. Across
four combinations the run schedules 320 pipeline calls and, if every record
produces output, 608 Judge calls. The expected total is therefore 928 external
model calls, before any provider-level retry.

## Acceptance criteria

The shadow profile is operationally valid only if all conditions hold:

1. All four model combinations complete and the result declares
   `evaluation_profile: shadow-actionability-v1`.
2. Every produced non-refusal draft receives one score for each of the four
   judged metrics; no Judge metric has an error. A response missing DeepEval's
   required `score` field may be retried once and the retry count must be
   retained in the cell results.
3. The existing schema-failure and safety hard bars are applied unchanged.
4. Every actionability reason is retained per record, so low scores and ranking
   changes can be audited without another paid run.
5. The report compares rankings only within the shadow profile. It reports, but
   does not hide, any change from the historical choice as a cross-instrument
   sensitivity result.
6. A manual review examines every actionability score below 0.6 and every pair
   of model combinations whose draft ranking changes after adding the metric.

Meeting these conditions supports promotion of the profile from shadow to the
default comparison instrument. It does not turn actionability into a safety
hard bar, and one run still carries the repository's existing single-run
caveat.
