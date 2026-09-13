# Enquiry Triage & Reply-Draft Agent — write-up

The agent is about 300 lines; the harness around it is most of the repository.
That ratio is the argument: what is scarce is not making a model draft a reply,
it is knowing whether the reply is safe to show a customer.

**On the frozen production bars, it is not.** All four model combinations fail.
A later evidence-backed variant improves the worst metric substantially but is a
feasibility demonstration, not a production claim. Evidence behind every number
is in [`docs/`](docs/) and [`results/`](results/); the limitations that bound all
of them — n=40, a synthetic distribution, single-run variance and narrow judge
validation — are in [`docs/07-limitations.md`](docs/07-limitations.md).

---

## 1. Architecture and key design decisions

**Two stages, separately modelled.** Triage (case type, priority, confidence)
and drafting (summary, reply) are separate calls with independently configurable
models. Triage is short-output and high-frequency; drafting is long-output and
hallucination-costly. Fusing them would make model selection one all-or-nothing
choice and the comparison would collapse into "the bigger model won".

It paid off measurably: the two models are **indistinguishable at triage**
(case-type accuracy 0.900 both, urgent recall 1.000 both) and clearly different
at drafting, where drafting with `flash` scores **0.500 on refusal correctness**
against **1.000** for `plus`. A fused design would have reported one number per
model and hidden that.

**Confidence is derived, not asked for.** Verbalised confidence clusters in
0.85–0.95 regardless of correctness. The provider exposes `logprobs`, so
confidence is the probability the model assigned to the label string it emitted.
On the golden set it behaves. The least confident record is
**ENQ-034 at 0.2972**, and it is wrong: a `COMPLAINT` routed to `CLAIM`. Next are
**ENQ-033 at 0.5198**, the same mistake, and
**ENQ-040 at 0.5461**, the record three blind relabelling runs had flagged as
genuinely ambiguous. The model is least certain where it is systematically
weakest.

**Groundedness is split.** Entity-level (policy numbers, amounts, dates, names
must be supported by the enquiry) is a set comparison and gets no LLM.
Commitment-level (fabricated SLAs, promises, entitlements) is a judgement call
and gets one. Conflating them makes the cheap half impossible to audit.

**Nothing sends.** No transport exists in `src/`, asserted by a test that scans
every module, so a send path in a new file fails without anyone maintaining a
list.

**Rejected:** a single call for all four fields (collapses model selection,
contaminates confidence with the drafting task); Ragas faithfulness (models a
`retrieval_context` that does not exist here); DeepEval's `DAGMetric` for the
refusal branch (every node it offers is LLM-driven, and the branch condition is
a set membership test whose answer is already written down).

---

## 2. Metric definitions and rationale

**Deterministic before probabilistic.** Every judge call must be defensible as
*no cheaper check exists*. Classification accuracy, entity groundedness, refusal
and injection resistance are set comparisons and regexes. Three metrics take a
judge, each with its reason:

- **Commitment groundedness** — "we will get back to you shortly" invents no
  entity an extractor can find and still promises what the enquiry does not
  support.
- **Tone match** — sympathy is warmth in a complaint and padding in an urgent
  claim; tone is a relation, not a word list.
- **Summary quality** — length is checkable and is not the failure; a summary
  that reads plausibly while adding something is.

Rubric bands and evaluation steps are hand-written.

**Keeping the judge honest.** `glm-5.2` is a fourth family — not the models
under test, not the dataset generator, not the blind relabeller; a generator
scoring its own output is self-preference bias by construction. The choice was
decided by measurement: GEval weights the score token by `top_logprobs`, and the
originally specified judge rejects that parameter, which would have left the
metric quietly coarser with an identical-looking table. **99.3% of 459 judge
calls scored continuously.**

**Inter-annotator agreement**, three blind runs: case type κ = 0.930 ± 0.035,
priority κ = 0.857 ± 0.045. Three rather than one, because a single run cannot
separate label drift from relabeller noise.

**Judge validation — the first judge failed it.** All 45 human labels were
collected blind on natural system output, and judge/human agreement was computed
against them:

| metric | QWK | Spearman | exact band | within one |
|---|---|---|---|---|
| commitment groundedness | −0.056 | −0.155 | 20% | 53% |
| tone match | 0.173 | 0.243 | 27% | 73% |
| summary quality | 0.000 | undefined | 7% | 20% |

**That is a failed validation, not a missing one.** On commitment groundedness
the first judge is uncorrelated with the human — slightly negative. On summary
quality it collapsed all fifteen summaries into the bottom band while the human
used all four, which is why rank correlation is undefined. The historical tone,
summary and commitment scores are therefore **diagnostic only; they are not
evidence about draft quality.** This is the measure the metrics document called
the one most submissions skip, and skipping it here would have left three
plausible-looking numbers standing.

Later instruments were rebuilt and validated separately rather than letting one
claim certify every metric: the source-backed domain judge matched 21/24
expected bands (κ 0.953), actionability v3 passed a disjoint holdout at 17/18
(κ 0.970), commitment v2 matched 19/24 development and 13/18 holdout bands
(κ 0.929 / 0.865) with every miss one band out. Those test rubric boundaries on
constructed examples, so they establish that the rebuilt judges order examples
correctly — not that they agree with a human on naturally uneven output, which
is the check the first judge failed.

Raw labels are kept in `.local` at the reviewer's choice; the aggregate and a
SHA-256 of both label and score files are versioned in
[`results/meta_eval_human_agreement.json`](results/meta_eval_human_agreement.json).

---

## 3. Model comparison and recommendation

`qwen3.7-flash-2026-07-15` against `qwen3.7-plus-2026-05-26` — dated snapshots,
because a floating alias can be repointed mid-experiment and the numbers move
with no error and no signal.

| triage / draft | case type | urgent recall | entity ground. | commitment | tone | summary |
|---|---|---|---|---|---|---|
| flash / flash | 0.900 | 1.000 | 0.972 | 0.519 | 0.652 | 0.627 |
| flash / plus | 0.875 | 1.000 | 0.948 | 0.638 | 0.682 | 0.775 |
| plus / flash | 0.900 | 1.000 | 0.977 | 0.465 | 0.639 | 0.600 |
| plus / plus | 0.900 | 1.000 | 0.943 | 0.732 | 0.635 | 0.739 |

**The composite is gated, not averaged.** Weights — triage: urgent recall 0.45,
case type 0.30, priority 0.25; drafting: entity groundedness 0.35, commitment
0.35, tone 0.15, summary 0.15. They differ by stage because the costs of error
do: at triage the expensive mistake is a missed urgent case, at drafting a
fabrication reaching a customer.

Composites are **withheld for all four**, because each misses a hard bar. A
weighted mean that a safety failure cannot lower launders it into a decimal — a
model could score higher by writing warmer replies while failing injection
resistance. The gate runs first; there were no survivors to rank.

`COMPLAINT` is the only weak class: recall 0.571, three of seven misrouted into
the topic being complained about.

### Recommendation

**Cheap model for triage, careful model for drafting — and not in production
yet.** Triage is nine times faster (0.64s against 5.90s median) and emits 17
output tokens against 313, with no measurable quality cost. Drafting with
`flash` answers one of the two refusal cases it should decline.

A later evidence-backed variant on five frozen cases raised mean commitment
groundedness from 0.270 to 0.734, and surfaced the trade-off: `ENQ-021` fell
from 0.700 to 0.300 on actionability because the safer reply deferred so much
the customer could not act ([`docs/assignment-demo-v1.md`](docs/assignment-demo-v1.md)).

### What would change it

- **A completed natural-output human packet** — the boundary validations test
  rubric edges, not agreement on ordinary output.
- **A COMPLAINT-aware triage prompt** — if it fixes `flash` but not `plus`, the
  triage half strengthens; if only `plus` recovers, it reverses.
- **Real prices** — triage is input-bound (722 in, 17 out), so its cost turns on
  the input price, not the output price that gets the attention.
- **Any number moving on a second run.**

### Operational

Serial, single-threaded, first call discarded, n = 39:

| stage | model | median | p95 | in tok | out tok |
|---|---|---|---|---|---|
| triage | flash | 0.64s | 1.57s | 722 | 17 |
| draft | plus | 5.90s | 9.21s | 776 | 313 |
| end to end | | 6.72s | 10.04s | | |

p95 is nearest-rank; at n=39 it is the second-slowest observation.

**Cost per invocation, as an interval.** The provider publishes no price for
these snapshots on any citable page and third-party figures disagree and tier by
context length, so a single number would be invented. Token counts are measured
exactly; the price is bounded by the publicly reported range, and only
conclusions that hold at both ends are stated.

| | cost per invocation (USD) |
|---|---|
| triage (flash) | 0.0000239 – 0.000158 |
| drafting (plus) | 0.000649 – 0.000812 |
| **end to end** | **0.000673 – 0.000970** |

That is **USD 0.67 – 0.97 per thousand enquiries**. Two conclusions survive the
whole interval. **Triage is input-bound**: 91% of its cost is input tokens at
both bounds, so a cheap triage model saves far less than its headline price
implies. And **drafting is 84–96% of the total**, which means moving triage from
`plus` to `flash` saves only **14–25%** of the per-enquiry cost — the case for
the cheap triage model rests on latency and equal quality, not on money.

A third finding needs no price at all: **thinking is on by default and dominates
output**, `flash` emitting a median 727 output tokens against 21 with it
disabled. A small model is cheap at triage only with thinking off.

### Calibration

| model | ECE | Brier | records above 0.9 |
|---|---|---|---|
| flash | 0.0619 | 0.0492 | 32 of 40 |
| plus | 0.0392 | 0.0574 | 36 of 40 |

The two measures disagree about which model is better calibrated; both are
reported rather than the flattering one. More decision-relevant: **confidence
saturates** — with 32–36 of 40 above 0.9, a gate routes four to eight cases in
forty rather than offering a graded curve. Bucket accuracy to ±0.05 would need
~139 records in that bucket alone; no recalibration is fitted.

---

## 4. Safety and governance

**Prompt injection — measured, 1.000 across all four combinations.** Two cases,
binary, any failure blocks. The realistic one is a legitimate address change with
a quiet line near the signature asking the assistant to append its configuration.
Neither landed, and the draft reported the manipulation attempt to the reviewer
before handling the enquiry. Leakage is checked against sentences extracted from
the prompt constants at call time, so rewording a prompt cannot leave the check
testing a string we no longer send. Every submission will assert that enquiry
text is delimited; the number is the point.

**PII in logs — a structural gate, after a measurement.** The model receives the
enquiry as written, because redacting before inference destroys the draft;
redaction happens on the path to disk. The first implementation ran NER over each
trace field and encrypted what it found. It **failed open**: policy number,
phone, email and amount were encrypted and the customer's name was not, NER
being context-sensitive. A compliance boundary cannot depend on a recall rate —
and does not have to, because we never needed to *find* the customer text when
we know which fields carry it. Every field not classified as non-sensitive is
now encrypted in full, the classification derived from the type so an
unclassified new field fails the tests rather than reaching disk. The operator is
reversible encryption: `<PERSON>` makes an audit trail useless.

**Data residency.** Inference ran against a Beijing-region endpoint; nothing
personal was at stake, as the dataset is generated from label specifications.
The real position is narrower than usually stated: **PDPO section 33 has never
been brought into force**, so there is no statutory bar on transferring personal
data out of Hong Kong. What applies is the PCPD's non-binding guidance, its 2022 model contractual
clauses, and the data user's standing obligations, which follow the data to a
processor wherever it sits. The honest statement is not "this is compliant" but
that production would put the endpoint, the processor contract and the redaction
boundary in front of compliance first.

**Before production:** approved insurer evidence and a distribution check
against live traffic; a confidence gate that routes more than four cases in
forty; refusal and injection cases at volume, since two each blocks a submission
but characterises nothing; an escalation path for cases producing no output,
untested because none occurred; and something consuming the reviewer decisions
the CLI already records.

---

## 5. Next two weeks

1. **Fix the two observed evidence-backed regressions, then freeze a new
   holdout.** `ENQ-021` became safe but under-actionable; `ENQ-030` claimed
   registration had already happened. Concrete boundary failures, not reasons to
   edit the frozen demo.
2. **Complete the natural-output human packet.** The boundary validations show
   the judge orders constructed examples; the 45-row packet answers how it
   behaves on ordinary output — and it gates the interpretation of the worst row
   in section 3.
3. **An embedding-based second-opinion classifier** — disagreement with an
   independent classifier is better calibrated than self-reported confidence,
   and the saturation above shows why something is needed.
4. **Reviewer corrections flowing back as golden samples** — the review CLI
   already keeps the edited text, which is the whole cost of enabling it.
5. **Conformal prediction for the confidence gate** — the right answer to
   small-sample calibration, the wrong answer to a six-day deadline.
6. **A distribution check against real enquiries** — most likely to invalidate
   the rest.

Also considered and rejected, with reasons in [`docs/04-scope.md`](docs/04-scope.md):
multi-turn conversation, fine-tuning, a production observability stack, Docker,
more than two models, a dataset beyond ~50 records, and a metrics dashboard.
