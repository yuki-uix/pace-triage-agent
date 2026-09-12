# Enquiry Triage & Reply-Draft Agent

A triage and reply-drafting assistant for inbound life-insurance customer
enquiries, with the evaluation harness that determines whether it is fit to go
near a real CS team.

**The recorded baseline is not production-ready; the assignment proof of
concept works.** All four historical model combinations fail the production-
oriented bars in [`docs/02-metrics.md`](docs/02-metrics.md). A later five-case,
evidence-backed candidate completed the full generate-score-review path with no
runtime failure, improved mean commitment groundedness from 0.270 to 0.734 and
passed the separate `assignment-poc-v1` interpretation. The distinction is the
deliverable: feasibility is demonstrated without relabelling it as deployment
approval.

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

The assignment candidate uses the cheaper configured model for triage, the
careful model for drafting, and the evidence-backed prompt. It writes drafts to
a queue and never sends them:

```bash
.venv/bin/python -m src.pipeline \
  --dataset data/assignment_demo_v1.jsonl \
  --evidence-backed \
  --out results/pending_queue.jsonl

.venv/bin/python -m src.review \
  --queue results/pending_queue.jsonl
```

Review decisions are persisted after every item. `accept` keeps the model draft,
`edit` stores the corrected reply separately as `reviewer_text`, and `discard`
retains the rejected output for audit. None of these actions transmits a reply.

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

### Completing the human judge labels

The existing meta-evaluation packet contains 15 natural drafts and 45 empty
human labels for commitment groundedness, tone match and summary quality. These
dimensions do not require insurance expertise: they are scored against the
customer email and the situation it describes. Read
[`docs/05-human-labeling.md`](docs/05-human-labeling.md), complete
`results/meta_eval_labels.jsonl` without opening the judge output, and check
progress without revealing agreement:

```bash
.venv/bin/python -m evals.meta_evaluation status
```

The status command exits non-zero while rows remain empty. The score phase also
refuses partial input, so an interim agreement result cannot anchor the remaining
labels. Once status reports 45/45, compute agreement for free:

```bash
.venv/bin/python -m evals.meta_evaluation score
```

Domain correctness is a separate, source-dependent judgement. Its balanced
validation is recorded in `docs/judge-validation-pilot-v2.md`; do not add domain
labels to the older 45-row packet unless a new source-backed prepare run is
deliberately commissioned.

### Validating actionability

Actionability asks whether a reply gives the customer a concrete operational
path: what to do, what is needed, through which route or owner, and what happens
next. It does not decide whether a deadline, completed action or promised
outcome is supported; commitment groundedness scores that separately. Its
validation workflow creates no judge output until all human labels are
complete:

```bash
# Free: create a 15-row blind worksheet and null human-label template locally.
.venv/bin/python -m evals.actionability_evaluation prepare

# Free: check progress without calling or revealing the judge.
.venv/bin/python -m evals.actionability_evaluation status

# Paid: unlocked only after 15/15 labels; makes 15 judge calls.
.venv/bin/python -m evals.actionability_evaluation score
```

Outputs default to `.local/actionability/`, outside the versioned evaluation
artefacts. The score phase refuses to overwrite an existing paid result; use
`--result` with a new path for a deliberate rerun.

The original 15-row packet is a pilot, not a balanced judge challenge set. A
separate 24-variant set covers six enquiries at every actionability band without
overwriting the pilot:

```bash
# Free: validate the 24-row contract and 6/6/6/6 band balance.
.venv/bin/python -m src.actionability_validation

# Paid: 24 calls after the expected bands have passed blind review.
.venv/bin/python -m evals.actionability_judge_validation
```

The expected bands received 24/24 agreement from an isolated blind Agent review.
The first Judge run is recorded in
[`docs/actionability-validation-pilot-v1.md`](docs/actionability-validation-pilot-v1.md).
Because no numeric acceptance threshold was declared before that run, it is
reported as evidence rather than retrospectively labelled a pass.

The harder follow-up is preregistered in
[`docs/actionability-boundary-validation-plan.md`](docs/actionability-boundary-validation-plan.md).
Its v2 set contains 18 minimally changed variants targeting only the 2/3, 5/6
and 8/9 boundaries; do not run its Judge phase until the v2 labels have passed
blind review. The disputed v1 set is retained rather than overwritten.

The preregistered paid boundary run is reported in
[`docs/actionability-boundary-validation-v1.md`](docs/actionability-boundary-validation-v1.md).
It missed the frozen exact-band threshold by one example, so actionability
remained experimental and outside the production composite and hard bars at
that stage.

Instrument v3 is tested on a disjoint held-out set after its anonymous blind
review passes:

```bash
.venv/bin/python -m evals.actionability_boundary_judge_validation --holdout
```

The held-out acceptance criteria are frozen in
[`docs/actionability-holdout-validation-plan.md`](docs/actionability-holdout-validation-plan.md).
The run passed every criterion and is reported in
[`docs/actionability-holdout-validation-v1.md`](docs/actionability-holdout-validation-v1.md).

Actionability is therefore usable through an explicit shadow profile. This
does not overwrite the historical 2x2 comparison or relax any hard bar:

```bash
.venv/bin/python -m evals.compare \
  --shadow-actionability \
  --out results/comparison-shadow-actionability-v1.json
```

The default `evals.compare` command continues to use the recorded instrument.
Treat the shadow weights as a frozen candidate until the full matrix has been
run and reviewed; do not compare its composite directly with the old profile's
composite because the instruments differ.

The completed run and its manual low-score review are recorded in
[`docs/actionability-shadow-comparison-v1.md`](docs/actionability-shadow-comparison-v1.md).
Actionability passed shadow operation, but every model combination missed an
existing safety bar; this is evidence against deploying the current drafting
pipeline, not a reason to publish an ungated composite.

### Evidence-backed drafting candidate

Issue #32 adds an opt-in drafting path backed by two source classes: versioned
public regulatory claims and a versioned synthetic internal service catalogue
for this fictional case study. The selected IDs are stored with each pending
draft, and the full evidence context is present in the encrypted trace. Existing
pipeline behaviour remains the default:

```bash
# Opt-in candidate; this makes normal triage and drafting provider calls.
.venv/bin/python -m src.pipeline \
  --evidence-backed \
  --traces results/evidence-backed-traces.jsonl
```

The matching commitment-groundedness v2 Judge is still experimental. Before
any paid run, validate and prepare its local blind packet:

```bash
# Free.
.venv/bin/python -m src.commitment_v2_validation
.venv/bin/python -m evals.prepare_commitment_v2_blind_review

# Paid only after all 24 blind scores are complete and frozen.
.venv/bin/python -m evals.commitment_v2_judge_validation
```

The exact preregistered thresholds and local score format are in
[`docs/commitment-v2-validation-plan.md`](docs/commitment-v2-validation-plan.md).
The revised set's independent blind review passed and is documented in
[`docs/commitment-v2-blind-validation.md`](docs/commitment-v2-blind-validation.md).
The first automated run then missed its frozen exact-band criterion by one item;
see [`docs/commitment-v2-validation-v1.md`](docs/commitment-v2-validation-v1.md).
Commitment v2 therefore remains experimental pending a disjoint holdout. It does
not alter the historical matrix or default pipeline.

The disjoint boundary holdout and its blind review are now frozen. Its paid
runner is a separate, explicitly authorised step:

```bash
.venv/bin/python -m src.commitment_v2_holdout
.venv/bin/python -m evals.commitment_v2_holdout_validation
```

The automated holdout missed the exact-band criterion despite passing every
other gate. The result is recorded in
[`docs/commitment-v2-holdout-v1.md`](docs/commitment-v2-holdout-v1.md). Do not
promote the candidate or rerun edited versions of the same replies.

### Assignment end-to-end demo

The final coursework proof of concept uses five frozen cases rather than
rerunning the full 2x2 matrix. It pairs baseline and evidence-backed drafts,
retains evidence IDs, applies identical scoring dimensions and prepares a short
human pair review:

```bash
# Free input/provenance check.
.venv/bin/python -m evals.assignment_demo --validate-only

# Paid paired run; use --resume after a provider interruption.
.venv/bin/python -m evals.assignment_demo
```

The case selection, review format, exact outputs and limitations are documented
in [`docs/assignment-demo-v1.md`](docs/assignment-demo-v1.md). This demonstrates
that the complete path operates; it does not replace the original production-
oriented hard bars or claim regulatory readiness.

For a non-technical audience, open the local web interface. Its live panel runs
one new enquiry through evidence-backed triage and drafting (normally two paid
model calls; more if confidence falls back to self-consistency). The frozen
case browser below it is read-only. Neither path sends a customer reply.

```bash
.venv/bin/python -m src.web_demo
```

The browser opens automatically at `http://127.0.0.1:8765`. Press `Ctrl+C` in
the terminal to stop the local server.

If a provider or quota failure interrupts the matrix, preserve the output file
and resume it. Complete cells are verified and reused; partial cells are rerun,
and prior usage accounting is retained:

```bash
.venv/bin/python -m evals.compare \
  --shadow-actionability \
  --resume \
  --out results/comparison-shadow-actionability-v1.json
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

Progress is printed as two stable lines per item: one before the request and one
after it with the score, predicted band, elapsed time and approximate ETA.
DeepEval's animated indicator is disabled because captured terminals render it
as repeated `You're running...` fragments rather than useful progress.

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
| `.venv/bin/python -m evals.meta_evaluation status` | Blind human-label progress; never reads judge scores | free |
| `.venv/bin/python -m evals.meta_evaluation score` | Judge/human agreement — requires every prepared human row | free |
| `.venv/bin/python -m evals.actionability_evaluation prepare/status` | Blind actionability worksheet and progress | free |
| `.venv/bin/python -m evals.actionability_evaluation score` | Actionability judge/human agreement | 15 calls |
| `.venv/bin/python -m evals.compare --shadow-actionability` | Full 2×2 matrix with validated actionability profile | ~928 calls, expected to exceed the recorded run time |
| `.venv/bin/python -m evals.judge_validation` | Four-band challenge-set matrix for the source-backed domain judge | 24 calls |
| `.venv/bin/python -m src.commitment_v2_validation` | Validate evidence IDs and the balanced commitment-v2 set | free |
| `.venv/bin/python -m evals.commitment_v2_judge_validation` | Preregistered evidence-aware commitment Judge validation | 24 calls |
| `.venv/bin/python -m evals.commitment_v2_assignment_report results/commitment_v2_holdout_v1.json` | Regrade the existing paid holdout against the coursework PoC profile | free |
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
judge/human worksheet remains unlabelled in the repository, so the historical
tone, summary and commitment rows must not be presented as human-validated.
Later source-backed and evidence-aware instruments do have balanced challenge
sets, disjoint holdout checks and blind reviews. Commitment v2 missed its
production-oriented exact-band gate but passed the explicitly narrower
assignment PoC interpretation; those results do not retroactively validate the
historical metrics.

**n=40.** The dataset is synthetic, generated from a label specification rather
than drawn from a real inbox, and no distribution check against real enquiries
has been done. Per-class F1 on six or seven records per class moves 15 points on
a single error.

**Confidence saturates.** 32–36 of 40 records score above 0.9, so a confidence
gate routes four to eight cases for closer scrutiny rather than offering a graded
curve.

**Chinese-script personal names are not detected** by the entity recognisers,
which run an English model.
