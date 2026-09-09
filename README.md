# Enquiry Triage & Reply-Draft Agent

> **Status: scaffold.** Implementation in progress. This README is filled in
> last, once every number in it can be reproduced from a clean checkout.

A triage and reply-drafting assistant for inbound life-insurance customer
enquiries, with the evaluation harness that determines whether it is fit to go
near a real CS team.

## Design in one paragraph

The pipeline is split into two independently-modelled stages: a cheap triage
step producing case type, priority and a derived confidence score, and a more
careful drafting step producing the summary and reply. Output is validated
against a Pydantic contract; malformed responses fail loudly and are counted.
Nothing is sent — drafts land in a pending queue for human accept/edit/discard.
Reasoning and rejected alternatives are recorded in [`docs/`](docs/).

## Quick start

```bash
# TODO: fill in once the pipeline runs
pip install -r requirements.txt
python -m spacy download en_core_web_lg
cp .env.example .env        # provider API keys
```

## Running the evaluation

```bash
# TODO
pytest evals/                    # full golden-set evaluation
python evals/latency.py          # serial latency run, measured separately
```

## Repository map

| Path | Contents |
|---|---|
| `src/` | Pipeline, schema, redaction, review CLI |
| `data/` | Synthetic enquiries, frozen golden set, labeling guide, provenance |
| `evals/` | Metrics, calibration, latency harness |
| `results/` | Raw evaluation output and summary tables |
| `docs/` | Architecture, metrics, data spec, scope |
| `writeup.md` | Deliverable C |

## Documents

- [Architecture and design decisions](docs/01-architecture.md)
- [Metric definitions and pass/fail bar](docs/02-metrics.md)
- [Dataset specification](docs/03-data-spec.md)
- [Scope and plan](docs/04-scope.md)
- [Labeling guide](data/labeling_guide.md)

## The golden set is frozen

`data/golden.jsonl` holds the answers and is frozen at tag **`golden-v1`**.

It changes only through a commit that says it is changing the golden set and
why, followed by a new tag. Every change is recorded in the change log at the
end of [`data/labeling_guide.md`](data/labeling_guide.md), with its reason.

**Regenerating it after seeing results is the one action that invalidates the
whole submission**, so the log records not just what changed but when relative
to the runs. Every label decided before the freeze was decided before any model
under test had been run against the set — there were no numbers to tune toward.

### Why there are two files

| File | Contents | Read by |
|---|---|---|
| `data/enquiries.jsonl` | `id`, `subject`, `body` — the email and nothing else | The pipeline |
| `data/golden.jsonl` | Expected labels, tags, reference notes, adjudication | The metrics |

The split is deliberate. The pipeline opens a file that does not contain the
answers, so "the model never sees the ground truth" is a property of the data
layout rather than a discipline someone has to keep. `load_records()` joins them
by id and raises if either side has an id the other lacks — a benchmark whose
halves have drifted apart is worse than no benchmark, and the failure is
otherwise silent, since the missing record simply never gets scored.

## Results

<!-- TODO: summary tables — task quality, calibration, operational, model comparison -->

## Known limitations

<!-- TODO: keep this section honest and specific. Sample size, synthetic data
     distribution, single-run variance, judge validation coverage. -->
