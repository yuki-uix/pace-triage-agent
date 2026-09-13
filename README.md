# Enquiry Triage & Reply-Draft Agent

A triage and reply-drafting assistant for inbound life-insurance customer
enquiries, with the evaluation harness that determines whether it is fit to go
near a real CS team.

**The submission evaluates a working prototype and recommends against production
release.** The frozen baseline compares two models on 40 enquiries; all four
triage/draft combinations fail the stated safety bars. A separate evidence-backed
candidate has only a five-case paired demo. It is not the version validated by
the full matrix, and its improved scores do not establish deployment readiness.

Start with [the write-up](writeup.md), then the baseline results below.
[Evidence coverage](docs/submission-evidence.md) identifies the available raw
outputs and the historical records that cannot be reconstructed from aggregates.

## Design in one paragraph

The pipeline is split into two independently-modelled stages: a cheap triage
step producing case type, priority and a derived confidence score, and a more
careful drafting step producing the summary and reply. Output is validated
against a Pydantic contract; malformed responses fail loudly and are counted.
Nothing is sent — drafts land in a pending queue for human accept/edit/discard.
Reasoning and rejected alternatives are recorded in [`docs/`](docs/).

## Quick start

Python 3.13. There is no bare `python` on most machines, so every command below
names the interpreter explicitly.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m spacy download en_core_web_lg
cp .env.example .env
```

Then fill in `.env`:

| Variable | What it is |
|---|---|
| `DASHSCOPE_API_KEY` | Alibaba Cloud Model Studio key. **Region-scoped**: a Beijing key returns 401 against the Singapore endpoint and vice versa. |
| `DASHSCOPE_BASE_URL` | The endpoint matching that key. |
| `TRIAGE_MODEL_A` / `TRIAGE_MODEL_B` | The two models under test. Dated snapshots, never floating aliases — an alias can be repointed mid-experiment and the numbers move with no error. |
| `GENERATOR_MODEL` | Wrote the dataset. A different family from both models under test. |
| `RELABEL_MODEL` | Blind second-opinion labeller. Different again. |
| `JUDGE_MODEL` | Quality judge. Must support `logprobs`, or GEval silently degrades to an integer score. |
| `TRACE_ENCRYPTION_KEY` | 16, 24 or 32 characters. Traces are refused without it rather than written in the clear. |
| `DEEPEVAL_PER_TASK_TIMEOUT_SECONDS` | The judge reasons before answering and exceeds the default. |

## Run the agent locally

The assessed baseline uses the cheaper configured model for triage and the
careful model for drafting. This command makes provider calls for the 40
synthetic enquiries, writes drafts to a queue and never sends them:

```bash
.venv/bin/python -m src.pipeline \
  --dataset data/enquiries.jsonl \
  --out results/pending_queue.jsonl

.venv/bin/python -m src.review \
  --queue results/pending_queue.jsonl
```

Review decisions are persisted after every item. `accept` keeps the model draft,
`edit` stores the corrected reply separately as `reviewer_text`, and `discard`
retains the rejected output for audit. None of these actions transmits a reply.

## Check recorded results or run a fresh regression

**Free, and the one to start with.** Checks the recorded results against the
pass/fail bars:

```bash
.venv/bin/python -m pytest evals/
```

Four tests are `xfail` on purpose — they are the bars the agent misses. They are
strict, so if the agent ever clears them the suite fails and someone has to come
and say so.

The unit tests, also free:

```bash
.venv/bin/python -m pytest tests/
```

### Fresh baseline regression (paid)

After setup, this single command runs the full 2x2 quality matrix, both models'
calibration, and two separate serial latency/cost runs covering both roles:

```bash
.venv/bin/python -m evals.regression --live --out-dir results/regression-v2
```

Omit `--live` to preview the commands without contacting a provider. Choose a
new directory for each run; existing directories are refused. The manifest
records source/data hashes and each step's status. A process failure stops later
steps and leaves completed outputs intact. `complete` means the measurements
finished, not that the agent passed the release bars; inspect `breaches` in the
new comparison file. Historical results and the golden set are not overwritten.

The free `pytest evals/` command above checks historical files only. It does not
measure a prompt change. The fresh regression may take over an hour and makes
roughly 1,040 baseline provider/Judge calls before retries or confidence fallback.
It does not evaluate the evidence-backed candidate.

### Evidence-backed candidate (separate five-case demo)

```bash
.venv/bin/python -m evals.assignment_demo --validate-only
```

This free command validates the demo inputs. The recorded paired outputs are in
[results/assignment_demo_v1.json](results/assignment_demo_v1.json). For paid demo
runs, Judge validation, private human-label workflows and optional web deployment,
see [additional experiment commands](docs/reproduction-details.md).

## Results

One run, not three. Repeating would have measured the same disqualification
three times; the caveat travels inside `results/comparison.json`.

### The 2×2 matrix

| triage / draft | case type | urgent recall | entity ground. | commitment | tone | summary |
|---|---|---|---|---|---|---|
| flash / flash | 0.900 | 1.000 | 0.972 | 0.519 | 0.652 | 0.627 |
| flash / plus | 0.875 | 1.000 | 0.948 | 0.638 | 0.682 | 0.775 |
| plus / flash | 0.900 | 1.000 | 0.977 | 0.465 | 0.639 | 0.600 |
| plus / plus | 0.900 | 1.000 | 0.943 | 0.732 | 0.635 | 0.739 |

The assignment-facing diagnostic fitness weights triage 40% and drafting 60%:
drafting receives the larger share because its text is customer-facing. It does
not override the safety gate.

| triage / draft | diagnostic fitness | release gate |
|---|---:|---|
| flash / flash | 0.806 | DISQUALIFIED |
| flash / plus | 0.844 | DISQUALIFIED |
| plus / flash | 0.790 | DISQUALIFIED |
| plus / plus | 0.856 | DISQUALIFIED |

All four miss entity groundedness (bar 0.99) and commitment groundedness (bar
0.98), so their publishable scores remain withheld. Diagnostic fitness supports
comparison for the assignment; it cannot launder a safety failure into a pass.

**The models are indistinguishable at triage** (0.900 both, urgent recall 1.000
both) **and are not at drafting** — drafting with flash scores 0.500 on refusal
correctness against 1.000 for plus. That is the recommendation the two-stage
split was built to make available, and the first evidence for it.

`COMPLAINT` is the only weak class: recall 0.571, three of seven misrouted into
the topic being complained about.

### Latency and cost

Serial, single-threaded, first successful call discarded, n=39 per stage. The
two runs use the same 40 enquiries.

| stage | model | median | p95 | in tok | out tok |
|---|---|---|---|---|---|
| triage | flash | 0.64s | 1.57s | 722 | 17 |
| triage | plus | 1.25s | 1.91s | 722 | 15 |
| draft | flash | 4.91s | 8.89s | 776 | 347 |
| draft | plus | 5.90s | 9.21s | 776 | 313 |

p95 is nearest-rank; at n=39 it is the second-slowest observation, not a fitted
quantile.

Costs use Alibaba Cloud Model Studio's published China (Beijing) list prices,
verified 2026-09-13. The calculation excludes free quota, limited-time, batch
and cache discounts.

| combination | estimated CNY / enquiry |
|---|---:|
| flash / flash | 0.000591 |
| flash / plus | 0.004216 |
| plus / flash | 0.001997 |
| plus / plus | 0.005623 |

The recommended Flash/Plus run measured end-to-end median 6.72s and p95 10.04s.
Prices are inputs; token counts and timings are measured API results. Source,
region and pricing basis are versioned in
[`data/model_prices.json`](data/model_prices.json).

### Calibration

| model | ECE | Brier | records in the 0.9–1.0 bucket |
|---|---|---|---|
| flash | 0.0619 | 0.0492 | 32 of 40 |
| plus | 0.0392 | 0.0574 | 36 of 40 |

The two measures disagree about which model is better calibrated. The widest
bucket interval spans 0.79 on n=1. Claiming a bucket accuracy to ±0.05 would
need about 139 records in that bucket alone, against 40 in total.

### Inter-annotator agreement

Cohen's kappa over three blind relabelling runs: case type 0.930 ± 0.035,
priority 0.857 ± 0.045.

## The golden set is frozen

`data/golden.jsonl` holds the answers and is frozen at tag **`golden-v1`**.

It changes only through a commit that says it is changing the golden set and
why, followed by a new tag, with a row added to the change log at the end of
[`data/labeling_guide.md`](data/labeling_guide.md).

**Regenerating it after seeing results is the one action that invalidates the
whole submission**, so the rule is a gate rather than a paragraph: both files are
hashed into `data/provenance.json` and `tests/test_freeze.py` asserts the hashes.
Changing the set fails the suite until someone updates the hash — which is the
explicit commit the rule asks for. Every label was decided before any model under
test had been run against the set.

### Why there are two data files

| File | Contents | Read by |
|---|---|---|
| `data/enquiries.jsonl` | `id`, `subject`, `body` — the email and nothing else | The pipeline |
| `data/golden.jsonl` | Expected labels, tags, reference notes, adjudication | The metrics |

The pipeline opens a file that does not contain the answers, so "the model never
sees the ground truth" is a property of the layout rather than a discipline
someone has to keep.

## Repository map

| Path | Contents |
|---|---|
| `src/` | Pipeline, schema, contract, redaction, trace store, review CLI |
| `data/` | Enquiries, frozen golden set, balanced judge-validation set, labeling guide, provenance, cited price input |
| `knowledge/` | Versioned public regulatory evidence plus a separately labelled synthetic internal service contract |
| `evals/` | Metrics, comparison, calibration, latency, meta-evaluation |
| `results/` | The numbers this README cites |
| `docs/` | Architecture and ADRs, metrics, data spec, scope |
| `writeup.md` | Deliverable C |

## Documents

- [Architecture and design decisions](docs/01-architecture.md)
- [Metric definitions and pass/fail bar](docs/02-metrics.md)
- [Dataset specification](docs/03-data-spec.md)
- [Scope and plan](docs/04-scope.md)
- [Human-labeling guide](docs/05-human-labeling.md)
- [Labeling guide](data/labeling_guide.md)

## Known limitations

**Every quality number is a single run.** Blind relabelling has already shown
run-to-run noise of the same order as the differences of interest on a judged
quantity, so differences on the judged rows cannot yet be separated from noise.

**Judge validation is instrument-specific.** The original 45-row natural-draft
worksheet was fully labelled (45/45); the filled rows remain private by reviewer
choice, while aggregate agreement and input hashes are published in
`results/meta_eval_human_agreement.json`. That review found poor agreement, so
the historical tone, summary and commitment rows must not be presented as
human-validated. Later source-backed and evidence-aware instruments do have
balanced challenge sets, disjoint holdout checks and blind reviews. Commitment
v2 missed its production-oriented exact-band gate but passed the explicitly
narrower assignment PoC interpretation; those results do not retroactively
validate the historical metrics.

**n=40.** The dataset is synthetic, generated from a label specification rather
than drawn from a real inbox, and no distribution check against real enquiries
has been done. Per-class F1 on six or seven records per class moves 15 points on
a single error.

**Confidence saturates.** 32–36 of 40 records score above 0.9, so a confidence
gate routes four to eight cases for closer scrutiny rather than offering a graded
curve.

**Chinese-script personal names are not detected** by the entity recognisers,
which run an English model.
