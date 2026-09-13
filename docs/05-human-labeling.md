# Human labeling without insurance expertise

This guide is for the 15-draft judge meta-evaluation in
`results/meta_eval_worksheet.md`. Its purpose is to let a general reviewer label
three properties consistently without pretending to know insurance law or an
insurer's internal process.

The current packet has 45 rows: 15 drafts multiplied by commitment groundedness,
tone match and summary quality. Those are the only rows to fill. Domain
correctness is deliberately separate because it requires the source pack and a
subject-matter review; the balanced domain-judge validation is recorded in
`docs/judge-validation-pilot-v2.md`.

## Blind-review rule

Before all 45 labels are frozen:

- read the customer email, generated summary, draft reply and rubric only;
- do not open `results/meta_eval_judge.json` or the judged result tables;
- do not run the `score` phase;
- do not ask another model to choose a score;
- use external material only to understand an unfamiliar word, never to decide
  whether an insurance statement is true.

Explanations of vocabulary are allowed. A suggested score is not: it would make
the human column partly model-generated and inflate apparent agreement.

## Score a band, not a precise decimal

Agreement is computed over four rubric bands. Choose the band first, then enter
the representative integer below. This avoids inventing a distinction between,
for example, 7 and 8 that the analysis never uses.

| metric | worst | weak | good | strongest |
|---|---:|---:|---:|---:|
| commitment groundedness | 1 | 4 | 7 | 10 |
| tone match | 1 | 5 | 7 | 10 |
| summary quality | 1 | 5 | 7 | 10 |

The underlying commitment bands are 0–2, 3–5, 6–8 and 9–10. Tone and summary
use 0–3, 4–6, 7–8 and 9–10. The scoring code uses these metric-specific
boundaries.

## Commitment groundedness

Question: **what does the reply cause the customer to believe the insurer will
do, deliver or decide?**

1. Underline every outcome, entitlement, deadline and claimed completed action
   in the reply.
2. Check whether the email itself establishes that commitment. A customer asking
   for something does not establish that the insurer has agreed to it.
3. Ignore whether the insurance explanation is technically correct. That belongs
   to domain correctness.
4. Generic acknowledgements and an unqualified statement that a team will review
   the request are not outcome commitments. A promised result or timeframe is.

Examples:

- “We have updated both policies and confirmation will arrive tomorrow” after a
  customer merely asks how to update them: worst band (enter 1). It invents a
  completed action and a deadline.
- “We will look into your request and help resolve it” with no prior undertaking:
  weak band (enter 4). It implies an unsupported successful outcome, but gives no
  definite decision or date.
- “We will review the documents you described; the wording could sound like
  acceptance”: good band (enter 7). Review is a generic next step, but the phrasing
  is slightly ambiguous.
- “Thank you for your enquiry. The relevant team will review the information; no
  outcome or timing can be confirmed from the details provided”: strongest band
  (enter 10).

## Tone match

Question: **does the register fit the customer's situation?**

1. Decide whether the email is urgent, consequential, upset/confused, or routine.
2. For urgency, look for an efficient opening and direct next steps; penalise
   sympathy or promotional padding that delays the useful content.
3. For routine enquiries, look for calm warmth; penalise brusque commands or a
   cold form-letter register.
4. Do not score factual correctness, promises, grammar or length by themselves.

Examples:

- A customer says surgery is tomorrow; the reply opens with several cheerful
  paragraphs and “take your time”: worst band (enter 1).
- A routine address enquiry receives a polite but mechanical form letter: weak
  band (enter 5).
- An upset customer receives a clear, respectful reply with one slightly canned
  phrase: good band (enter 7).
- An urgent deadline receives a concise, formal response led by what the customer
  should do next: strongest band (enter 10).

## Summary quality

Question: **could a reviewer triage the case from at most two sentences without
learning anything the customer did not say?**

1. Check every summary claim against the email.
2. Check that the request and any deadline or consequence are present.
3. Check that it is no more than two sentences.
4. Ignore elegance and ignore facts found only in the draft reply.

Examples:

- The email disputes a missed payment and asks for correction; the summary says
  only “Customer asks about a policy”: worst band (enter 1), because it omits the
  actionable request.
- The summary is accurate but leaves the reviewer unable to tell what response is
  needed, or exceeds two sentences: weak band (enter 5).
- It captures the request and deadline but omits a secondary question: good band
  (enter 7).
- It is one or two sentences, contains only email facts, and includes the request
  plus any deadline: strongest band (enter 10).

## Workflow

1. Read the practice examples above before opening the real worksheet.
2. Label one record at a time across all three dimensions. Treat the dimensions
   independently; a factually dubious reply can still have excellent tone.
3. Write the representative integer into the matching `human` field in
   `results/meta_eval_labels_template.jsonl` (the versioned copy is the blank
   template; the filled one is kept locally).
4. Check progress at any time without exposing judge output:

   ```bash
   .venv/bin/python -m evals.meta_evaluation status
   ```

5. If uncertain, record a private note and choose the closest band. Do not inspect
   the judge to break a tie.
6. Only after status reports that every row is complete, run:

   ```bash
   .venv/bin/python -m evals.meta_evaluation score
   ```

The score command refuses an incomplete label set. This is an experimental
control, not an inconvenience: once agreement is visible, later labels are no
longer blind.
