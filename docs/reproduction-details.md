# Additional experiments and demo commands

Run all commands from the repository root. These are separate experiments,
not steps required to inspect the baseline submission. Relative file paths in
commands refer to the repository root. See [evidence coverage](submission-evidence.md).

### Natural-output human judge labels

The 15-draft, 45-row human review is complete. The filled labels remain in
`.local/meta_eval/` by reviewer choice; the repository keeps the empty template
so it does not publish them accidentally. Aggregate agreement and SHA-256
provenance are recorded in
[`results/meta_eval_human_agreement.json`](../results/meta_eval_human_agreement.json).
The private packet can be verified locally without opening the Judge output:

```bash
.venv/bin/python -m evals.meta_evaluation status --out-dir .local/meta_eval
```

The score phase refuses partial input, so an interim agreement result cannot
anchor the remaining labels. Once status reports 45/45, recompute agreement:

```bash
.venv/bin/python -m evals.meta_evaluation score --out-dir .local/meta_eval
```

The completed validation failed: commitment kappa is -0.056, tone kappa 0.173
and summary kappa 0.000. The historical Summary Judge put all 15 drafts in its
lowest band while the human used all four. These historical Judge metrics are
diagnostic, not validated human substitutes.

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
[`docs/actionability-validation-pilot-v1.md`](actionability-validation-pilot-v1.md).
Because no numeric acceptance threshold was declared before that run, it is
reported as evidence rather than retrospectively labelled a pass.

The harder follow-up is preregistered in
[`docs/actionability-boundary-validation-plan.md`](actionability-boundary-validation-plan.md).
Its v2 set contains 18 minimally changed variants targeting only the 2/3, 5/6
and 8/9 boundaries; do not run its Judge phase until the v2 labels have passed
blind review. The disputed v1 set is retained rather than overwritten.

The preregistered paid boundary run is reported in
[`docs/actionability-boundary-validation-v1.md`](actionability-boundary-validation-v1.md).
It missed the frozen exact-band threshold by one example, so actionability
remained experimental and outside the production composite and hard bars at
that stage.

Instrument v3 is tested on a disjoint held-out set after its anonymous blind
review passes:

```bash
.venv/bin/python -m evals.actionability_boundary_judge_validation --holdout
```

The held-out acceptance criteria are frozen in
[`docs/actionability-holdout-validation-plan.md`](actionability-holdout-validation-plan.md).
The run passed every criterion and is reported in
[`docs/actionability-holdout-validation-v1.md`](actionability-holdout-validation-v1.md).

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
[`docs/actionability-shadow-comparison-v1.md`](actionability-shadow-comparison-v1.md).
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
[`docs/commitment-v2-validation-plan.md`](commitment-v2-validation-plan.md).
The revised set's independent blind review passed and is documented in
[`docs/commitment-v2-blind-validation.md`](commitment-v2-blind-validation.md).
The first automated run then missed its frozen exact-band criterion by one item;
see [`docs/commitment-v2-validation-v1.md`](commitment-v2-validation-v1.md).
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
[`docs/commitment-v2-holdout-v1.md`](commitment-v2-holdout-v1.md). Do not
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
in [`docs/assignment-demo-v1.md`](assignment-demo-v1.md). This demonstrates
that the complete path operates; it does not replace the original production-
oriented hard bars or claim regulatory readiness.

**The demo lives in [`extras/`](../extras/) and is not part of the assessed
deliverable** — see [`extras/README.md`](../extras/README.md) for why. For a
non-technical audience, open the local web interface. Its live panel runs
one new enquiry through evidence-backed triage and drafting (normally two paid
model calls; more if confidence falls back to self-consistency). The frozen
case browser below it is read-only. Neither path sends a customer reply.

```bash
.venv/bin/python extras/web-demo/web_demo.py
```

The browser opens automatically at `http://127.0.0.1:8765`. Press `Ctrl+C` in
the terminal to stop the local server.

### Vercel deployment

The repository also contains a zero-dependency Node.js Vercel Function so the
interactive demo can be hosted without packaging the much larger evaluation
environment. Configure `DASHSCOPE_API_KEY`, `DASHSCOPE_BASE_URL`,
`TRIAGE_MODEL_A`, `TRIAGE_MODEL_B` and `DEMO_ACCESS_CODE` in both Preview and
Production. The access code is mandatory online: it prevents an anonymous
visitor from spending the presenter's model balance.

```bash
vercel deploy          # Preview first
vercel deploy --prod   # only after the Preview is verified
```

The Vercel function mirrors the two model prompts, strict response contracts,
confidence derivation and deterministic evidence routing used by the Python
pipeline. `node --test api/index.test.mjs` checks its deployment boundary.

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
| `.venv/bin/python -m evals.latency --triage-model qwen3.7-plus-2026-05-26 --draft-model qwen3.7-flash-2026-07-15 --out results/latency-plus-flash.json` | Cross-run needed for same-role latency/cost comparison | 80 calls, ~5 min |
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
