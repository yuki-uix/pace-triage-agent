# Enquiry Triage & Reply-Draft Agent — write-up

MyPace staff handle policy, servicing, premium, claim and complaint emails. The assistant returns case type, priority, confidence, summary and reply draft. Every draft awaits human acceptance, editing or rejection; nothing is sent.

**On the frozen production bars, it is not ready.** All four model combinations fail. Versioned machine results are in [`docs/`](docs/) and [`results/`](results/). The human-agreement aggregate is versioned; raw labels remain local by reviewer choice. Limitations — n=40, synthetic data, single-run variance and failed Judge validation — are recorded in [`docs/07-limitations.md`](docs/07-limitations.md).

**Evidence scope.** The 40-case matrix is the baseline; evidence-backed drafting has a separate five-case demo. Historical per-draft and Judge records are incomplete, so those semantic means cannot be independently reconstructed. New runs retain them. See [evidence coverage](docs/submission-evidence.md).

---

## 1. Architecture and key design decisions

**Two stages, separately modelled.** Triage and drafting are separate calls with independently configurable models. Fusing them would make model selection one all-or-nothing choice and collapse the comparison into "the bigger model won".

```text
email -> untrusted boundary -> triage -> schema/retry -> classification
email + classification [+ opt-in evidence] -> draft -> schema/retry -> pending review
stage traces -> full-field encryption -> append-only trace store
```

Across one 40-record pass per combination, the split exposed a role-level difference. Case-type accuracy was 0.875–0.900 with Flash Triage and 0.900 with Plus; urgent recall was 1.000 throughout. Drafting with Flash scored **0.500 on refusal correctness**, against **1.000** for Plus. A fused design would hide that distinction. These small stochastic runs do not establish model equivalence.

**Confidence is derived, not self-reported.** Historical calibration used emitted-label `logprobs`; the fallback counts independent samples supporting that label and rejects malformed samples. In the Flash run, **ENQ-034 at 0.2972** and **ENQ-033 at 0.5198** are misrouted `COMPLAINT`s; **ENQ-040 at 0.5461** was independently flagged as ambiguous. This is diagnostic evidence, not a deployment control.

**Groundedness is split.** Entity-level support is a set comparison and gets no LLM; commitment-level support for SLAs, outcomes and entitlements requires semantic judgement. Conflating them makes the cheap half impossible to audit.

**Nothing sends.** No transport exists in `src/`; a source-scanning test makes a new send path fail without anyone maintaining a file list.

**Rejected:** one call for all fields because it couples model selection and confidence; Ragas faithfulness because there is no baseline retrieval context; and an LLM refusal DAG where deterministic membership is sufficient.

---

## 2. Metric definitions and rationale

**Deterministic before probabilistic.** Judge calls are reserved for cases with no cheaper defensible check. Measures follow the two-stage failure modes:

| layer | measures | why |
|---|---|---|
| triage | case accuracy, per-class F1, priority accuracy, urgent recall | routing quality, with missed urgent cases separated from recoverable queue errors |
| draft facts | entity and commitment groundedness | detect invented identifiers, amounts, dates, SLAs, outcomes and entitlements |
| draft utility | tone, summary quality; actionability in a later shadow profile | measure reviewer/customer usefulness without treating specificity as evidence |
| safety/contract | refusal, injection, schema/retry/provider failures | keep boundary failures out of a soft quality average |
| decision support | ECE/Brier, median/p95 latency, cost | test whether confidence can route work and whether a candidate is operationally sensible |

Classification, entity groundedness, refusal and injection are set comparisons or regexes. Commitment, tone, summary and actionability require semantic judgement and use hand-written rubric bands and evaluation steps.

**The risk design is asymmetric because the business consequences are.** A false-positive urgent label consumes reviewer attention; a false negative may delay a regulatory, legal or coverage-sensitive case. A weak tone is visible and cheap to edit; a fabricated policy fact or SLA may look authoritative and escape a hurried review. Severity, exposure, detectability and recoverability therefore determine whether a failure becomes a high-weight objective or a non-compensable gate. The exact numerical bars are preregistered project risk assumptions, not regulatory standards or estimates derived from forty synthetic records.

**Judge validity.** `glm-5.2` is separate from candidates, generator and relabeller, and supports GEval's `top_logprobs` score weighting. **99.3% of 459 Judge calls scored continuously.**

Three blind relabelling runs produced case-type κ = 0.930 ± 0.035 and priority κ = 0.857 ± 0.045, exposing run noise.

**The first Judge failed validation.** Forty-five blind human labels covered fifteen natural drafts and three metrics. Judge/human QWK was −0.056 for commitment, 0.173 for tone and 0.000 for summary; summary placed every draft in the bottom band while the human used all four. Historical semantic scores are therefore diagnostic only. Domain correctness (21/24, κ 0.953) and Actionability holdout (17/18, κ 0.970) later passed their named validations. Commitment v2 did not pass either preregistered exact-band gate: 19/24 development and 13/18 holdout, despite κ 0.929/0.865 and every miss being within one band. Constructed boundaries test ordering, not agreement on natural output. Aggregates and hashes are in [`results/meta_eval_human_agreement.json`](results/meta_eval_human_agreement.json).

---

## 3. Model comparison and recommendation

The comparison pins dated `qwen3.7-flash-2026-07-15` and `qwen3.7-plus-2026-05-26` snapshots to prevent silent model drift.

| triage / draft | case | urgent | entity | commitment | tone | summary |
|---|---:|---:|---:|---:|---:|---:|
| flash / flash | 0.900 | 1.000 | 0.972 | 0.519 | 0.652 | 0.627 |
| flash / plus | 0.875 | 1.000 | 0.948 | 0.638 | 0.682 | 0.775 |
| plus / flash | 0.900 | 1.000 | 0.977 | 0.465 | 0.639 | 0.600 |
| plus / plus | 0.900 | 1.000 | 0.943 | 0.732 | 0.635 | 0.739 |

Priority accuracy, used in Triage fitness, was 0.900 / 0.950 / 0.875 / 0.925 in the same row order.

**Fitness is hierarchical and gated.** Triage weights urgent recall / case type / priority at 0.45 / 0.30 / 0.25 because urgent false negatives are least recoverable. Draft weights entity / commitment / tone / summary at 0.35 / 0.35 / 0.15 / 0.15 because false facts and promises are harder to catch than prose defects. The overall split is 40% Triage / 60% Draft because Draft creates customer-facing text:

The preregistered bars are: case accuracy ≥0.80, urgent recall ≥0.95, entity groundedness ≥0.99, commitment groundedness ≥0.98, refusal and injection 2/2, and schema failures ≤2%.

| triage / draft | quality fitness | release gate |
|---|---:|---|
| flash / flash | 0.806 | DISQUALIFIED |
| flash / plus | 0.844 | DISQUALIFIED |
| plus / flash | 0.790 | DISQUALIFIED |
| plus / plus | 0.856 | DISQUALIFIED |

All four miss entity and commitment gates; both Flash Draft cells also miss refusal correctness.

The assignment's scalar fitness is this weighted task-quality composite. Calibration, latency and cost remain explicit constraints and tie-breakers: converting seconds, yuan and groundedness into one cardinal utility would require business valuations not supplied here. Hard bars apply before ranking, so a cheap or fluent model cannot compensate for an unsafe reply. All four cells are disqualified; no release-eligible fitness is reported. Because the original semantic Judges failed human validation, the values remain diagnostic.

`COMPLAINT` is the most persistent weak class: recall was 0.571 in both Flash Triage passes and 0.714 in both Plus passes. `OTHER` also fell to 0.667 in three cells.

### Recommendation

**Do not ship any current combination.** For the next validation run, use Flash for Triage and Plus for Drafting as the challenger: Flash has lower Triage latency without a stable measured quality disadvantage, while Plus passed both refusal probes. An opt-in evidence-backed variant improved commitment scores on five paired demo/regression cases but reduced actionability on one; it is not an independent Agent holdout or proof of optimisation ([details](docs/assignment-demo-v1.md)). A natural-output Judge pass, a repeated comparison or a material price change could change this choice.

### Operational

Serial, single-threaded, first successful call discarded, n = 39 per stage:

| stage | model | median | p95 | in tok | out tok |
|---|---|---|---|---|---|
| triage | flash | 0.64s | 1.57s | 722 | 17 |
| triage | plus | 1.25s | 1.91s | 722 | 15 |
| draft | flash | 4.91s | 8.89s | 776 | 347 |
| draft | plus | 5.90s | 9.21s | 776 | 313 |

**Cost per invocation.** Alibaba Cloud's published China (Beijing) list prices, verified 13 September 2026, are CNY 0.20 / 0.80 per million input/output tokens for Flash and CNY 2 / 8 for Plus:

| triage / draft | estimated CNY / enquiry |
|---|---:|
| flash / flash | 0.000591 |
| flash / plus | 0.004216 |
| plus / flash | 0.001997 |
| plus / plus | 0.005623 |

The Flash/Plus run measured end-to-end median 6.72s and p95 10.04s. Prices exclude discounts, free quota, infrastructure, review labour and failed calls.

### Calibration

`flash` ECE 0.0619 / Brier 0.0492; `plus` ECE 0.0392 / Brier 0.0574. They disagree on which is better calibrated, and 32–36 of 40 confidence values exceed 0.9. Confidence therefore does not drive the queue. Full buckets are in [`results/calibration.json`](results/calibration.json).

---

## 4. Safety and governance

Safety here is an allocation of authority and failure action, not only a set of technical filters. Customer text has no authority to change system instructions; the model has no authority to invent insurer policy or commit the company; and the Agent has no authority to contact a customer. A business owner must decide what evidence is approved, which failures require escalation, what a reviewer may release and what residual risk is acceptable. The implementation makes parts of that policy executable:

| risk | business decision | implemented control and evidence | residual gap |
|---|---|---|---|
| prompt injection | an enquiry is untrusted data, but a legitimate request containing an attack still needs service | delimited input, explicit authority boundary and **1.000 across all four combinations** on two frozen probes | two cases characterise nothing; no production output monitor |
| unsupported facts or commitments | no model may create an insurer rule, completed action, SLA or outcome without authority | scoped evidence IDs, entity/commitment checks and mandatory review | evidence coverage is not checked before generation; no claim-level runtime block |
| PII in traces | retain auditability without a readable secondary customer store | every content-bearing trace field is encrypted; adding an unclassified field fails tests | queue policy plus trace-key ownership, rotation and decryption audit are missing |
| malformed/no output | failure must be visible rather than silently defaulted | strict schema, retry, separate failure counters and recorded no-output cases | no production alert or owned escalation SLA |
| accidental release | only a person may decide what reaches a customer | no send transport; accept/edit/discard pending queue | any future transport integration requires a new release-boundary review |

Entity-level NER originally missed a customer name, so traces now encrypt whole content fields rather than trust probabilistic detection. The model still sees the original email; provider and data-residency choices are therefore business and compliance decisions too. This case study uses synthetic data and a Beijing endpoint. Real traffic would still require approved insurer evidence, processor/endpoint review, queue and retention controls, larger safety sets, an evidence-gap escalation path and risk-owner sign-off.

---

## 5. Next two weeks

1. **Build an evidence-gated Draft Plan.** Mark supported and missing topics; require each fact, action and commitment to cite enquiry or approved evidence before prose is rendered. Missing support routes to review or a safe fallback.
2. **Run a controlled Agent experiment.** Freeze Triage and metric versions, compare paired baseline/candidate deltas, repair COMPLAINT routing, validate semantic Judges on natural output, then test on a new blind Agent holdout.
3. **Close the operating loop.** Track reviewer decisions, edit time and critical corrections; add provider/schema/evidence alerts, owned escalation, queue access and retention controls, approved insurer evidence and a privacy-approved sample of real enquiry shapes.

Further scope exclusions and rationale are in [`docs/04-scope.md`](docs/04-scope.md).
