# Labeling Guide

The golden set is only a benchmark if its labels are defensible. This document
is the adjudication rule set, written **before** the ambiguous cases were
generated. It exists so that "why is this the correct answer?" has an answer
other than "it seemed right at the time."

## Case type

Rules are applied in order; the first that matches wins.

1. **Refusal cases** are labelled by refusal, not by topic — meaning the
   *required action* is refusal. The record still carries its topical
   `expected_type`, and refusal is a separate axis recorded by the `REFUSAL`
   tag and scored by its own binary metric.

   An enquiry asking whether a claim will definitely be approved is
   `expected_type: CLAIM` with the `REFUSAL` tag: a human agent would route it
   to the claims queue, and what makes it a refusal case is that the reply must
   not answer the question, not that the enquiry is about something else.

   *This rule was ambiguous as first written.* It said what such a record is
   not, without saying what it is. The two candidate readings were `OTHER` plus
   the tag, or the topical type plus the tag. `OTHER` was rejected: rule 4
   forbids `OTHER` as an escape hatch, and with only five `OTHER` records in
   forty, adding two refusal cases would make 40% of that class noise and its
   per-class F1 uninterpretable. See the change log.
2. **Mixed-topic enquiries** are labelled by the *action the CS agent must take
   first*, not by word count. An email that complains about service and then
   requests an address change is `ADDRESS_CHANGE` — the complaint is tone, the
   address change is the work item. Where two genuine work items exist, the one
   with the shorter regulatory clock wins.
3. **Missing-information enquiries** keep their topical label. An address change
   with no policy number is still `ADDRESS_CHANGE`; incompleteness is a property
   of the enquiry, not a category.
4. **`OTHER`** is for enquiries that genuinely fit no category, not for
   enquiries that are hard. Using `OTHER` as an escape hatch destroys the
   metric.

Records carry an `acceptable_types` field listing the defensible alternatives.
Every mixed-topic record has one; so does any record where repeated blind
relabelling shows a competent second labeller consistently reading the category
boundary differently. Ambiguity is not the exclusive property of an email with
two subjects — a fraud report that also asks whether the policy is still in force
is one subject sitting on a boundary. `acceptable_types` is not handed out
freely: a record claiming ambiguity must record why in `label_note`, because
inflating the lenient score would destroy the meaning of the gap between the two
accuracies. Primary accuracy is scored against `expected_type`; a secondary
lenient accuracy against `acceptable_types` is also reported. The gap between
the two numbers is itself informative — a large gap means the task is
ambiguous, not that the model is weak.

## Priority

- **URGENT** — financial or coverage consequence with a near-term deadline
  (lapse imminent, claim time limit, payment failure), or an explicit escalation
  threat (regulator, legal, media).
- **Naming a regulator, a lawyer or the press is an escalation threat even when
  hedged.** "I will seriously consider going to the Insurance Authority" counts.
  The criterion is whether the channel is named, not how firmly. This follows
  from the cost of error stated in `docs/02-metrics.md`: under-triaging a
  complaint that reaches the regulator carries a cost no reviewer recovers,
  while over-triaging one costs reviewer attention. The asymmetry that sets the
  URGENT recall bar at 95% sets this threshold too.
- **Angry tone alone does not make an enquiry URGENT.** This is the rule most
  likely to be violated by both a model and a human labeller, and several records
  exist specifically to test it. An irate customer asking a routine question is
  `NORMAL` with a complaint flag.
- **LOW** — informational, no deadline, no dissatisfaction.
- **The operative test between LOW and NORMAL is whether anything has to be
  done.** If the customer only wants to know something and the queue closes the
  case by answering, it is LOW. If something must be actioned — a record
  changed, a charge investigated, a statutory request fulfilled — it is NORMAL,
  even when the customer says there is no rush. "Informational" and "ordinary
  request" were the original wording and did not separate a procedural request
  from a question; several records sat between them.
- When a deadline is implied but not stated, label the more urgent option and
  record the reasoning in `label_note`.

## Reference notes for the reply

Reference notes are not a gold-standard reply. They are a short list of facts the
reply **must** contain and facts it **must not** invent. Writing a full model
answer would bias the judge toward one phrasing.

Each record carries:
- `must_include` — entities or commitments the reply is required to address
- `must_not_assert` — the specific fabrications this record is designed to bait
  (a claim outcome, a refund timeline, a policy term not present in the enquiry)

## Inter-annotator check

**Every** record is labelled a second time, blind, by a different model family,
and Cohen's kappa is reported in the write-up. Every record rather than only the
ambiguous ones, because the failure this catches — generated prose drifting away
from the label the plan assigned — is invisible by inspection.

**The pass is repeated, and a single run is not evidence.** Run to run, the same
model on the same unchanged records contests a different set: across three runs
only two records were contested every time while ten were contested
intermittently. The spread on the priority kappa (0.789 +/- 0.025) is comparable
to the differences one would try to read from it. Adjudicate the records
contested in every run; treat the intermittent ones as noise. `docs/02-metrics.md`
already requires key metrics to be run three times, and that rule applies to the
instrument as much as to the thing being measured.

**A disagreement is not a verdict.** It means one of three things - the prose
drifted, the record is genuinely ambiguous, or the second labeller is wrong - and
a human decides which. Some records exist specifically to be got wrong by a
labeller that escalates on tone or on seriousness; consistent disagreement there
is evidence the record works, not evidence the label is wrong. Low agreement on a record
is not a problem to hide — it is evidence that the record is genuinely ambiguous
and should be reported as such alongside the accuracy numbers.

## Change log

The golden set is frozen at tag `golden-v1`. Any change to labels after that tag
is recorded here with a date and reason.

| Date | Record | Change | Reason |
|---|---|---|---|
| 2026-09-09 | ENQ-032 | Priority NORMAL to URGENT | The email names the Insurance Authority. The guide's URGENT criterion is disjunctive - deadline **or** escalation threat - so the planned label contradicted the guide. Contested in 3 of 3 blind relabelling runs. The generated `label_note` had itself flagged the tension. |
| 2026-09-09 | ENQ-040 | Added `acceptable_types` (OTHER, POLICY_QUERY) | A fraud report that also asks whether the policy is in force. Contested in 3 of 3 runs. Not a mixed-topic record - one subject on a category boundary - which exposed that `acceptable_types` had been coupled to the MIXED_TOPIC tag. The coupling was removed. |
| 2026-09-09 | Priority rule | Named-regulator threats count as escalation even when hedged | See above. |
| 2026-09-09 | Inter-annotator check | Repeated, and only consistently-contested records adjudicated | A single run cannot separate label drift from relabeller noise; two of the three records adjudicated on 2026-09-09 from a single run turned out to be contested in 1 of 3 runs or not at all. |
| 2026-09-09 | Priority rule | Added the do-something test separating LOW from NORMAL | The original wording ("informational" vs "ordinary request") did not classify a procedural request that needs action but has no deadline. Found by blind relabelling, which disagreed on exactly those records. |
| 2026-09-09 | ENQ-006, ENQ-038 | Priority NORMAL to LOW | Applying the clarified test above. Both are questions with nothing to action: ENQ-006 asks whether the policy has a premium holiday option; ENQ-038 says outright "Nothing urgent at all" and the sender holds no policy. |
| 2026-09-09 | ENQ-029 | Record regenerated as a pure complaint | The generated email complained about unexplained charges *and* hotline waits. Under rule 2 the first action is explaining the charges, which makes it PREMIUM_BILLING — the label contradicted the guide. The mixed-topic quota was already full at five, so the record was regenerated with no separable work item rather than relabelled. |
| 2026-09-08 | Rule 1 (all refusal records) | Clarified that refusal records keep their topical `expected_type` and carry the `REFUSAL` tag, rather than being labelled `OTHER` | The rule as written said only what a refusal record is *not*. Labelling them `OTHER` would contradict rule 4 and put 40% noise into the smallest class. Resolved **before** the golden set was generated or frozen, so no label was changed after seeing any result. |
| — | — | Initial freeze | — |
