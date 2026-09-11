# Scope

This is a one-week assignment with a 10–15 hour budget, assessed on judgement
and engineering discipline. It is not an attempt to build the best possible
system. The binding constraint is time, and the failure mode is an ambitious
half-finished repository.

The reasoning below is not just internal planning — the rejected list is the raw
material for the write-up's "trade-offs I rejected" and "next two weeks"
sections. Nothing here is wasted.

## In scope — load-bearing, do not cut

These are the items the assessment actually turns on.

- Pydantic output contract with loud, counted failures
- Two-stage pipeline with injectable models
- 40-record synthetic dataset with the quotas in `03-data-spec.md`
- Frozen, tagged golden set
- `data/labeling_guide.md` — the adjudication rules for ambiguous cases
- Deterministic entity-level groundedness metric
- Judge meta-evaluation against ~15 hand-labelled drafts
- Calibration table with honest confidence intervals
- Asymmetric pass/fail bar with cost-of-error justification
- Injection and refusal cases as scored assertions
- Serial latency measurement, separate from quality runs
- One-command re-run
- Review CLI (accept / edit / discard against a JSONL queue)
- Write-up, including the rejected alternatives
- README that lets a stranger reproduce every number

## Out of scope — deliberately not built

Each of these is defensible in the write-up as a decision. None is defensible as
an unfinished directory.

| Not building | Why | Where it goes instead |
|---|---|---|
| Web UI | The brief permits a CLI. A UI consumes hours and demonstrates nothing being assessed. | — |
| General RAG / real policy knowledge base | The original task has no real insurer corpus. Issue #32 adds only a small, versioned synthetic service contract with deterministic routing; broad retrieval and real policy terms remain out of scope. | Next two weeks |
| Multi-turn conversation | The task is single-email triage. | Next two weeks |
| Fine-tuning | Cannot be justified or evaluated at n=40. | Next two weeks |
| Embedding-based second-opinion classifier | Genuinely good for calibration — disagreement between an independent classifier and the LLM is better-calibrated than self-reported confidence. Cannot be built and validated in the budget. | Next two weeks — as the primary proposal |
| Conformal prediction for the confidence gate | Correct answer to small-sample calibration, wrong answer to a six-day deadline. | Next two weeks |
| Production observability stack (Langfuse, Phoenix) | Trace files on disk are sufficient at this scale. | Safety/governance section |
| Docker / deployment | Not assessed. A working `requirements.txt` is. | — |
| More than two models | The brief is explicit: a rigorous comparison of two modest models beats a sloppy comparison of five frontier ones. | — |
| Chasing dataset size beyond ~50 | Larger n costs evaluation budget and does not reach significance anyway. | Stated as a limitation |
| Metrics dashboard | The summary tables in the write-up are the dashboard. | — |

## Degradation order

If time runs out, cut in this order. Cutting from the top costs the least.

1. Variance runs — drop to a single run, disclose it
2. Summary quality judge — entity + commitment groundedness carry the section
3. Second and third noise dimensions in the dataset
4. Cost modelling precision — published list prices are fine
5. Review CLI polish — a bare JSONL editor is acceptable

Never cut: the labeling guide, the judge meta-evaluation, the asymmetric bar, or
the rejected-alternatives section. Those four are where judgement is visible.

## Plan

| Day | Work |
|---|---|
| Mon 8 – Tue 9 | Schema, 40 records, golden set frozen and tagged, labeling guide. Dull, and it gates everything downstream. Also the only phase independent of model availability. |
| Wed 10 – Thu 11 | Two-stage pipeline, Presidio at the logging boundary, DeepEval metrics, one full evaluation pass. |
| Fri 12 | Model comparison matrix and calibration. Keep buffer — rate limits and format surprises always appear here. |
| Sat 13 | Write-up and review CLI. The write-up goes last because the real conclusion is only known after the runs; anything drafted earlier gets rewritten. |
| Sun 14 | README, cleanup, one final full re-run from a clean checkout. |

The review CLI is twenty minutes: a JSONL pending queue plus accept/edit/discard
writing back a decision field. Do keep the reviewer's edited text — "reviewer
corrections flow back as new golden samples" is the most natural first item in
the next-two-weeks section, and it costs one extra field.
