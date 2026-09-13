# Known limitations

Moved out of the write-up to keep Deliverable C inside its two-to-four page
limit. Linked from the write-up's opening, because these bound every number
in it.


**n=40**, six or seven records per class: one error moves per-class F1 by about
15 points. **The distribution is synthetic** — every enquiry was written from a
label specification, which is what makes the "no real PII" claim true by
construction and is also the largest threat to external validity. **Every
quality number is a single run**, and blind relabelling showed run-to-run noise
of the same order as the differences of interest, so differences on judged rows
cannot yet be separated from noise. **Judge validation is narrow**: rubric
boundaries, not the live output distribution. **Metric artifacts are a live
risk** — entity groundedness flagged three artifacts in six on real drafts, and
refusal correctness initially matched one of five plausible polite refusals, so
its failure mode was punishing correct behaviour. Both were found by running
metrics over real output rather than hand-written fixtures; metrics not yet
exercised that way should be assumed to have similar defects. **Chinese-script
names are not detected** by the English recognisers. Cost estimates use versioned
public list-price inputs; they exclude discounts, free quota, infrastructure,
review labour and failed-call cost, so they support comparison rather than a
production budget.

Process failures — including losing four hours to extrapolating wall-clock from
token volume, against a rule this repository states — are in
[`docs/06-process-notes.md`](docs/06-process-notes.md).
