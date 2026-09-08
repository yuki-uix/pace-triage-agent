# Labeling Guide

The golden set is only a benchmark if its labels are defensible. This document
is the adjudication rule set, written **before** the ambiguous cases were
generated. It exists so that "why is this the correct answer?" has an answer
other than "it seemed right at the time."

## Case type

Rules are applied in order; the first that matches wins.

1. **Refusal cases** are labelled by refusal, not by topic. An enquiry asking
   whether a claim will definitely be approved is a refusal case, not
   `CLAIM`.
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

Mixed-topic records carry an `acceptable_types` field listing the defensible
alternatives. Primary accuracy is scored against `expected_type`; a secondary
lenient accuracy against `acceptable_types` is also reported. The gap between
the two numbers is itself informative — a large gap means the task is
ambiguous, not that the model is weak.

## Priority

- **URGENT** — financial or coverage consequence with a near-term deadline
  (lapse imminent, claim time limit, payment failure), or an explicit escalation
  threat (regulator, legal, media).
- **Angry tone alone does not make an enquiry URGENT.** This is the rule most
  likely to be violated by both a model and a human labeller, and several records
  exist specifically to test it. An irate customer asking a routine question is
  `NORMAL` with a complaint flag.
- **LOW** — informational, no deadline, no dissatisfaction.
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

All ambiguous records are labelled a second time, blind, by a different model
family, and Cohen's kappa is reported in the write-up. Low agreement on a record
is not a problem to hide — it is evidence that the record is genuinely ambiguous
and should be reported as such alongside the accuracy numbers.

## Change log

The golden set is frozen at tag `golden-v1`. Any change to labels after that tag
is recorded here with a date and reason.

| Date | Record | Change | Reason |
|---|---|---|---|
| — | — | Initial freeze | — |
