# CLAUDE.md

Context for Claude Code working in this repository.

## What this is

A one-week case study for an AI Developer role. Build an **Enquiry Triage &
Reply-Draft Agent** for a Hong Kong life insurer's customer-service team, plus
the evaluation harness that proves it works.

Deadline: **Mon 14 Sep 2026**. Budget: **10–15 hours total.**

## The single most important thing

The assessment is explicit: *"We are assessing judgement and engineering
discipline, not volume of output."*

The agent itself is ~300 lines. **The agent is not the deliverable.** The
deliverable is the evidence that we know whether the agent works. When a choice
comes up between building more surface area and making one thing measurable,
choose measurable.

## Read before writing code

1. `docs/01-architecture.md` — the two-stage design and why
2. `docs/04-scope.md` — the explicit not-doing list
3. `docs/02-metrics.md` — metric definitions and the pass/fail bar
4. `docs/03-data-spec.md` — dataset quotas
5. `data/labeling_guide.md` — how ambiguous cases are adjudicated

## Standing constraints

- **Python.** Pydantic for the output contract. DeepEval for the harness.
  Presidio for PII. No additional frameworks without an ADR entry.
- **Schema failures are loud.** A malformed model response raises, gets counted,
  and appears in the results table. It never silently becomes a default value or
  disappears from a denominator.
- **Nothing sends.** The human-in-the-loop CLI writes a decision field. There is
  no send path in this codebase at all.
- **Deterministic before probabilistic.** If a check can be done with a regex or
  a set comparison, it does not get an LLM judge. Every LLM judge call must be
  justifiable as "no cheaper check exists."
- **Latency is measured serially.** Quality evaluation runs concurrently;
  latency measurement runs single-threaded with the first call discarded.
  Never merge the two runs.
- **The golden set is frozen.** Once tagged, `data/golden.jsonl` changes only via
  an explicit commit that says so and re-tags. Regenerating it to make numbers
  look better is the one thing that invalidates the whole submission.

## Scope discipline

Before adding anything not in `docs/04-scope.md` under "In scope", stop and ask.
The default answer is no, and the correct home for a good idea that doesn't fit
is the "Next two weeks" section of the write-up. A rejected idea documented with
its reasoning scores better than an unfinished implementation.

## Language

All repository content is in English — code, comments, docs, commit messages.
The reviewers are in Hong Kong and the repo is read as a single artefact.

## Definition of done

- [ ] `pytest evals/` runs the full golden-set evaluation in one command
- [ ] Two models compared across both pipeline stages, with a composite score
- [ ] Calibration table with an honest statement of what n=40 can and cannot show
- [ ] Pass/fail bar stated per-metric with a cost-of-error justification
- [ ] Write-up covers architecture, metrics, comparison, safety, next steps
- [ ] README lets a stranger clone and reproduce every number in the write-up
