# Source-backed judge reference pack

This directory gives the judge a small, auditable set of Hong Kong insurance
and privacy facts. It is deliberately not a general-purpose RAG corpus.

## Files

- `source_manifest.json` records the publisher, canonical URL, scope and review
  date for each source.
- `reference_claims.jsonl` contains one paraphrased, source-linked claim per
  line. Small claims are easier to audit than copied web pages and keep a
  changed page from silently changing an evaluation.

Only first-party material from the Insurance Authority, the Privacy
Commissioner for Personal Data and the Insurance Complaints Bureau is admitted.
The loader enforces that domain allow-list.

## Evidence boundary

These references answer questions about Hong Kong-wide rules and general
insurance concepts. They do **not** establish any insurer's:

- product wording or the terms of an individual policy;
- app, portal, form, email or postal submission process;
- document checklist, service-level target or refund process; or
- CRM state, such as whether a request was registered or escalated.

The judge must treat a definite statement in one of those categories as
unsupported unless the evaluation case supplies the missing evidence. This is
why `domain correctness` is separate from `commitment groundedness`: a sentence
can make no promise and still state the law or a policy term incorrectly.

## Updating the pack

1. Use the original publisher, not a blog, search result or model summary.
2. Add or update the manifest entry and set `verified_on` to the date a person
   checked the canonical page.
3. Paraphrase only the minimum claim needed by the rubric. Add a section or page
   locator so another reviewer can find it.
4. Run `python3 -m pytest tests/test_reference_pack.py`.

The files are versioned rather than fetched during an evaluation. A live fetch
would make two runs depend on different evidence and would make an unavailable
website look like a model-quality change.

## Balanced validation data

`data/judge_validation_set.jsonl` is a controlled challenge set, separate from
the natural model outputs in `results/meta_eval_drafts.jsonl`. It contains four
counterfactual replies to each of six enquiries: one in every 0–2, 3–5, 6–8 and
9–10 domain-correctness band. Each row names its seeded faults and evidence IDs.

Do not combine its scores with the natural-output agreement figure. The natural
set estimates behaviour on this system's outputs; the balanced set tests whether
the judge can distinguish all four rubric bands, including whether it falsely
penalises careful answers.
