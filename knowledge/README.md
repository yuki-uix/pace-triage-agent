# Source-backed judge reference pack

This directory gives the judge a small, auditable set of Hong Kong insurance
and privacy facts. It is deliberately not a general-purpose RAG corpus.

## Files

- `source_manifest.json` records the publisher, canonical URL, scope and review
  date for each source.
- `reference_claims.jsonl` contains one paraphrased, source-linked claim per
  line. Small claims are easier to audit than copied web pages and keep a
  changed page from silently changing an evaluation.
- `service_catalogue_manifest.json` identifies the version and scope of a
  synthetic internal operating contract for the fictional Harbourview Life
  case study.
- `service_catalogue.jsonl` contains its atomic, topic-routed service rules.

Only first-party material from the Insurance Authority, the Privacy
Commissioner for Personal Data and the Insurance Complaints Bureau is admitted.
The loader enforces that domain allow-list.

The service catalogue is a different source class. It is deliberately
synthetic, is not evidence about a real insurer, and exists so the drafting
experiment can make useful process commitments without pretending that a
public regulator specifies an insurer's intake channels. The combined context
keeps the public and internal headings separate and records every selected ID.

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

For a service-rule change, also update the catalogue version when compatibility
changes and run both `tests/test_service_catalogue.py` and
`tests/test_draft_evidence.py`. Validation-set rows freeze their selected IDs,
so a routing change must be reviewed rather than silently accepted.

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

The first run and the reasons for revising the middle-band constructions are
recorded in `docs/judge-validation-pilot-v1.md`. Dataset changes are made from
the rubric-level adjudication documented there, not by copying the judge's
predicted bands into the expected labels.

The rerun is preserved as `results/judge_validation_pilot_v2.json`; its summary,
input fingerprints and mismatch adjudication are in
`docs/judge-validation-pilot-v2.md`. Future runner outputs include the input
SHA-256 values automatically so a paid result can be tied to the exact dataset,
reference pack and judge rubric that produced it.
