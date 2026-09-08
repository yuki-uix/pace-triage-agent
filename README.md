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
| `data/` | Synthetic enquiries, frozen golden set, labeling guide |
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

## Results

<!-- TODO: summary tables — task quality, calibration, operational, model comparison -->

## Known limitations

<!-- TODO: keep this section honest and specific. Sample size, synthetic data
     distribution, single-run variance, judge validation coverage. -->
