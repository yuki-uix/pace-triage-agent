# Assignment demo v1

This five-case paired demo is the final proof-of-concept check for the
evidence-backed drafting path. It is intentionally not another 40-case, 2x2
model comparison. Its question is narrower: can the repository run one frozen
email through triage, scoped evidence selection, drafting, provenance capture,
automated scoring and human review without changing tools between stages?

## Frozen cases

| ID | Purpose |
|---|---|
| `ENQ-009` | noisy routine address-change request |
| `ENQ-021` | medical-claim process question |
| `ENQ-030` | angry complaint with several requested outcomes |
| `ENQ-024` | refusal boundary: requested guarantee of claim approval |
| `ENQ-012` | prompt injection inside a real servicing request |

The records in `data/assignment_demo_v1.jsonl` are verbatim copies. Their IDs,
source paths and SHA-256 fingerprints were frozen in
`data/assignment_demo_v1_manifest.json` before generation.

## Commands

Validate the frozen inputs and inspect selected evidence without model calls:

```bash
.venv/bin/python -m evals.assignment_demo --validate-only
```

Run the paired demo. This makes normal pipeline and Judge calls, writes after
each variant, and refuses to overwrite the result:

```bash
.venv/bin/python -m evals.assignment_demo
```

If a provider failure interrupts the run, use:

```bash
.venv/bin/python -m evals.assignment_demo --resume
```

Completed generation and individual Judge scores are reused. A Judge failure
does not force the two pipeline stages to run again.

After generation, fill the five JSONL rows in
`.local/assignment_demo_v1/review.jsonl`. `preferred` must be `baseline`,
`evidence_backed` or `tie`, and every selection needs a one-sentence `reason`.
Then rerun `--resume`; no completed paid work is repeated and the Markdown
report is finalised.

## Result status

Results are pending the explicitly authorised paid run. The runner writes
`results/assignment_demo_v1.json` and `results/assignment_demo_v1.md`. The final
report must show regressions and ties as well as improvements; five synthetic
cases demonstrate execution and inspectability, not an error rate or production
safety.
