# Enquiry Triage & Reply-Draft Agent

A triage and reply-drafting assistant for inbound life-insurance customer
enquiries, with the evaluation harness that determines whether it is fit to go
near a real CS team.

**It is not.** All four model combinations fail the bars in
[`docs/02-metrics.md`](docs/02-metrics.md). That result, and the evidence behind
it, is the deliverable — the agent is about 300 lines and was never the point.

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

## Reproducing every number

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

### Running the balanced judge validation

Run these commands from the repository root after completing Quick start and
setting `DASHSCOPE_API_KEY`, `DASHSCOPE_BASE_URL` and `JUDGE_MODEL` in `.env`:

```bash
cd /path/to/pace-triage-agent

# Free: validate the challenge-set contract, evidence IDs and 6/6/6/6 balance.
.venv/bin/python -m src.judge_validation

# Paid: 24 judge calls. The output path is explicit and may be changed.
.venv/bin/python -m evals.judge_validation \
  --out results/judge_validation.json
```

The paid command exits non-zero if any judge call fails, but still records every
successful item and every failure in the output file. It does not overwrite
`results/meta_eval_judge.json` or the 2x2 comparison.

**The paid runs.** Each writes to `results/` and each is the source of exactly
one table in the write-up.

| Command | Produces | Cost |
|---|---|---|
| `.venv/bin/python -m src.quotas data/enquiries.jsonl` | Dataset quota check | free |
| `.venv/bin/python -m src.judge_validation` | Validate the balanced, source-backed judge challenge set | free |
| `.venv/bin/python -m src.generate --out data/enquiries.jsonl` | Regenerates the dataset — **do not run**, see the freeze rule below | ~40 calls |
| `.venv/bin/python -m src.relabel --runs 3` | `results/relabel.json` — inter-annotator agreement | 120 calls |
| `.venv/bin/python -m evals.compare` | `results/comparison.json` — the 2×2 matrix, confusion matrices, judge reasons | ~800 calls, ~57 min |
| `.venv/bin/python -m evals.calibration` | `results/calibration.json` — reliability buckets, ECE, Brier | 80 calls, ~2 min |
| `.venv/bin/python -m evals.latency` | `results/latency.json` — **serial**, never merged with a quality run | 80 calls, ~5 min |
| `.venv/bin/python -m evals.meta_evaluation prepare` | Worksheet + judge scores, including source-backed domain correctness | ~90 calls |
| `.venv/bin/python -m evals.meta_evaluation score` | Judge/human agreement — **needs a person to fill the worksheet first** | free |
| `.venv/bin/python -m evals.judge_validation` | Four-band challenge-set matrix for the source-backed domain judge | 24 calls |
| `.venv/bin/python -m src.pipeline --traces results/traces.jsonl` | Fills the pending queue | 80 calls |
| `.venv/bin/python -m src.review` | Review the pending queue | free |

`RUN_LIVE_EVAL=1 .venv/bin/python -m pytest evals/` regenerates the matrix before
checking it. That is the hour-long path.

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

All four disqualified on entity groundedness (bar 0.99) and commitment
groundedness (bar 0.98). Composites are withheld rather than reported: a
weighted mean that a safety failure cannot lower launders that failure into a
decimal.

**The models are indistinguishable at triage** (0.900 both, urgent recall 1.000
both) **and are not at drafting** — drafting with flash scores 0.500 on refusal
correctness against 1.000 for plus. That is the recommendation the two-stage
split was built to make available, and the first evidence for it.

`COMPLAINT` is the only weak class: recall 0.571, three of seven misrouted into
the topic being complained about.

### Latency and cost

Serial, single-threaded, first call discarded, n=39.

| stage | model | median | p95 | in tok | out tok |
|---|---|---|---|---|---|
| triage | flash | 0.64s | 1.57s | 722 | 17 |
| draft | plus | 5.90s | 9.21s | 776 | 313 |
| end to end | | 6.72s | 10.04s | | |

p95 is nearest-rank; at n=39 it is the second-slowest observation, not a fitted
quantile. Cost per call is **not** reported: the provider publishes no price for
these snapshots on any citable page, so `data/model_prices.json` is a template
and the harness prints `no price` rather than a zero that would read as an
answer.

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
| `data/` | Enquiries, frozen golden set, balanced judge-validation set, labeling guide, provenance, price template |
| `knowledge/` | Versioned first-party regulatory sources and atomic reference claims for the judge |
| `evals/` | Metrics, comparison, calibration, latency, meta-evaluation |
| `results/` | The numbers this README cites |
| `docs/` | Architecture and ADRs, metrics, data spec, scope |
| `writeup.md` | Deliverable C |

## Documents

- [Architecture and design decisions](docs/01-architecture.md)
- [Metric definitions and pass/fail bar](docs/02-metrics.md)
- [Dataset specification](docs/03-data-spec.md)
- [Scope and plan](docs/04-scope.md)
- [Labeling guide](data/labeling_guide.md)

## Known limitations

**Every quality number is a single run.** Blind relabelling has already shown
run-to-run noise of the same order as the differences of interest on a judged
quantity, so differences on the judged rows cannot yet be separated from noise.

**The judge is not validated.** Commitment groundedness — the worst-looking
number here — is a judge score no human has checked. Spot-checking its reasons
shows they are specific and real in kind, but whether the judge is stricter than
a reviewer is exactly what judge/human agreement answers, and those labels do
not exist yet. Until they do, that row says the judge objects, not that the
drafts are wrong.

**n=40.** The dataset is synthetic, generated from a label specification rather
than drawn from a real inbox, and no distribution check against real enquiries
has been done. Per-class F1 on six or seven records per class moves 15 points on
a single error.

**Confidence saturates.** 32–36 of 40 records score above 0.9, so a confidence
gate routes four to eight cases for closer scrutiny rather than offering a graded
curve.

**Chinese-script personal names are not detected** by the entity recognisers,
which run an English model.
