"""Judge meta-evaluation: measuring whether the judge agrees with a human.

Without this the quality scores are an unvalidated instrument. `docs/02-metrics.md`
calls it the measure most submissions will skip, and it is the reason the judge
numbers are worth anything at all.

**The labels must come from a person.** This module builds a worksheet and
computes agreement once it is filled in; it does not and must not produce the
human column itself. Scoring the drafts with a second model and reporting the
result as judge/human agreement would fabricate the one number that certifies
every other number in the write-up. A model-model agreement figure can be
computed too, and is labelled as exactly that.

Agreement is reported three ways because they answer different questions:

- **Quadratic-weighted kappa** over the rubric bands, which is the ordinal
  measure - being one band out should cost less than being three out.
- **Spearman correlation**, which asks whether the judge ranks drafts as the
  human does, independent of calibration.
- **Exact and within-one-band rates**, which are what a reader can picture.

A judge can rank well and score high, or agree on the extremes and disagree
throughout the middle. One number would hide that.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from statistics import mean

from sklearn.metrics import cohen_kappa_score
from scipy.stats import spearmanr

# The bands come from the rubrics in `evals/metrics/judged.py`. A human labels a
# band, not a decimal: asking a person for 0.73 invents a precision they do not
# have, and the judge's decimal is compared by banding it the same way.
BANDS: tuple[tuple[int, int], ...] = ((0, 2), (3, 5), (6, 8), (9, 10))
METRICS: tuple[str, ...] = ("commitment groundedness", "tone match", "summary quality")


def band_of(score_out_of_ten: float) -> int:
    """Index of the rubric band a 0-10 score falls in."""
    for index, (low, high) in enumerate(BANDS):
        if low <= score_out_of_ten <= high:
            return index
    raise ValueError(f"score {score_out_of_ten} is outside 0-10")


def judge_band(normalised_score: float) -> int:
    """GEval returns 0-1; the rubric is 0-10."""
    return band_of(round(normalised_score * 10))


@dataclass
class Agreement:
    metric: str
    n: int
    kappa: float
    spearman: float
    exact: float
    within_one: float

    def render(self) -> str:
        return (f"{self.metric:26} n={self.n:<3} "
                f"kappa={self.kappa:+.3f}  rho={self.spearman:+.3f}  "
                f"exact={self.exact:.0%}  within-1-band={self.within_one:.0%}")


def agreement(human_bands: list[int], judge_bands: list[int],
              metric: str) -> Agreement:
    if len(human_bands) != len(judge_bands):
        raise ValueError("human and judge label counts differ")
    if not human_bands:
        raise ValueError("no labels to compare")

    labels = list(range(len(BANDS)))
    kappa = cohen_kappa_score(human_bands, judge_bands, labels=labels,
                              weights="quadratic")
    rho = spearmanr(human_bands, judge_bands).statistic if len(human_bands) > 2 else float("nan")

    pairs = list(zip(human_bands, judge_bands))
    return Agreement(
        metric=metric,
        n=len(pairs),
        kappa=float(kappa),
        spearman=float(rho),
        exact=mean(1.0 if h == j else 0.0 for h, j in pairs),
        within_one=mean(1.0 if abs(h - j) <= 1 else 0.0 for h, j in pairs),
    )


def build_worksheet(rows: list[dict], path: str) -> str:
    """Write a worksheet for a person to fill in.

    Judge scores are deliberately absent from the worksheet. Showing them would
    anchor the labeller, and an anchored human column measures nothing.
    """
    lines = [
        "# Judge meta-evaluation worksheet",
        "",
        "Score each draft 0-10 on each dimension, using the bands below. Write "
        "your score in the `human` field of the matching row in the JSONL file "
        "next to this one.",
        "",
        "The judge's own scores are not shown here on purpose: seeing them first "
        "would anchor your judgement, and an anchored human column measures "
        "nothing.",
        "",
    ]
    from evals.metrics.judged import (
        COMMITMENT_RUBRIC, SUMMARY_RUBRIC, TONE_RUBRIC,
    )
    for metric, rubric in (("commitment groundedness", COMMITMENT_RUBRIC),
                           ("tone match", TONE_RUBRIC),
                           ("summary quality", SUMMARY_RUBRIC)):
        lines.append(f"## {metric}")
        lines.append("")
        for band in rubric:
            low, high = band.score_range
            lines.append(f"- **{low}-{high}** - {band.expected_outcome}")
        lines.append("")

    for row in rows:
        lines += [
            "---",
            "",
            f"### {row['record_id']}",
            "",
            "**Customer email**",
            "",
            "```",
            row["enquiry"].strip(),
            "```",
            "",
            "**Summary written for the reviewer**",
            "",
            f"> {row['summary'].strip()}",
            "",
            "**Draft reply**",
            "",
            "```",
            row["draft_reply"].strip(),
            "```",
            "",
            "| dimension | your score 0-10 |",
            "|---|---|",
        ]
        for metric in METRICS:
            lines.append(f"| {metric} | |")
        lines.append("")

    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def load_human_labels(path: str) -> dict[tuple[str, str], int]:
    """Read `{record_id, metric, human}` rows. Missing labels are simply absent."""
    labels: dict[tuple[str, str], int] = {}
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("human") is None:
            continue
        score = int(row["human"])
        if not 0 <= score <= 10:
            raise ValueError(f"{row['record_id']} {row['metric']}: {score} is not 0-10")
        labels[(row["record_id"], row["metric"])] = score
    return labels


def select(records, size: int = 15):
    """A spread across case types, excluding refusal records.

    Refusal records skip the draft-quality metrics by design (`flow.py`), so
    including them would produce worksheet rows with nothing to score. The
    selection is deterministic: the meta-evaluation set must not move between
    runs, or the agreement figure is not comparable with itself.
    """
    from src.dataset import Tag

    eligible = [r for r in records if Tag.REFUSAL not in r.tags]
    by_type: dict[str, list] = {}
    for record in sorted(eligible, key=lambda r: r.id):
        by_type.setdefault(record.expected_type.value, []).append(record)

    chosen, exhausted = [], False
    while len(chosen) < size and not exhausted:
        exhausted = True
        for case_type in sorted(by_type):
            if by_type[case_type] and len(chosen) < size:
                chosen.append(by_type[case_type].pop(0))
                exhausted = False
    return sorted(chosen, key=lambda r: r.id)


def main(argv: list[str]) -> int:
    """Two phases. `prepare` produces drafts, judge scores and a worksheet;
    `score` computes agreement once a person has filled the worksheet in."""
    import argparse

    parser = argparse.ArgumentParser(description="Judge meta-evaluation.")
    parser.add_argument("phase", choices=["prepare", "score"])
    parser.add_argument("--size", type=int, default=15)
    parser.add_argument("--out-dir", default="results")
    args = parser.parse_args(argv[1:])

    out = pathlib.Path(args.out_dir)
    labels_path = out / "meta_eval_labels.jsonl"
    judge_path = out / "meta_eval_judge.json"

    if args.phase == "score":
        return _score(labels_path, judge_path)
    return _prepare(args.size, out, labels_path, judge_path)


def _prepare(size: int, out: pathlib.Path, labels_path: pathlib.Path,
             judge_path: pathlib.Path) -> int:
    import os

    from openai import OpenAI

    from evals.metrics.judged import JUDGED_METRICS
    from src.contract import FailureCounters
    from src.generate import load_env
    from src.judge import DashScopeJudge
    from src.pipeline import PipelineConfig, StageConfig, run
    from src.quotas import load_records
    from deepeval.test_case import LLMTestCase

    load_env()
    client = OpenAI(api_key=os.environ["DASHSCOPE_API_KEY"],
                    base_url=os.environ["DASHSCOPE_BASE_URL"])
    config = PipelineConfig(StageConfig(os.environ["TRIAGE_MODEL_A"]),
                            StageConfig(os.environ["TRIAGE_MODEL_B"]))
    judge = DashScopeJudge()
    metrics = [build(judge) for build in JUDGED_METRICS]

    records = select(load_records(), size)
    counters = FailureCounters()
    rows, judge_scores = [], {}

    for record in records:
        item = run(client, config, record.id, record.subject, record.body, counters)
        enquiry = f"Subject: {record.subject}\n\n{record.body}"
        rows.append({"record_id": record.id, "enquiry": enquiry,
                     "summary": item.summary, "draft_reply": item.draft_reply})

        scored = LLMTestCase(input=enquiry, actual_output=item.draft_reply)
        summary_case = LLMTestCase(input=enquiry, actual_output=item.summary)
        for metric in metrics:
            metric.measure(summary_case if metric.__name__ == "summary quality"
                           else scored)
            judge_scores[f"{record.id}|{metric.__name__}"] = metric.score
        print(f"  {record.id} scored", flush=True)

    out.mkdir(parents=True, exist_ok=True)
    with open(labels_path, "w", encoding="utf-8") as handle:
        for row in rows:
            for metric in METRICS:
                handle.write(json.dumps({"record_id": row["record_id"],
                                         "metric": metric, "human": None}) + "\n")
    judge_path.write_text(json.dumps({
        "judge_model": judge.get_model_name(),
        "scores": judge_scores,
        "usage": judge.usage.as_dict(),
        "contract_failures": counters.as_dict(),
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    worksheet = build_worksheet(rows, str(out / "meta_eval_worksheet.md"))

    print(f"\n{len(rows)} drafts written to {worksheet}")
    print(f"judge scores: {judge_path}")
    print(f"label template (human: null): {labels_path}")
    print(f"continuous scoring rate: {judge.usage.continuous_scoring_rate:.0%} "
          f"of {judge.usage.calls} judge calls")
    print("\nFill in the human scores, then run: "
          "python -m evals.meta_evaluation score")
    return 0


def _score(labels_path: pathlib.Path, judge_path: pathlib.Path) -> int:
    if not labels_path.exists() or not judge_path.exists():
        print("run the prepare phase first", flush=True)
        return 2

    human = load_human_labels(str(labels_path))
    judged = json.loads(judge_path.read_text(encoding="utf-8"))["scores"]

    if not human:
        print("no human labels filled in yet; agreement cannot be computed.")
        print("This number must come from a person: scoring the drafts with a "
              "second model and calling it judge/human agreement would fabricate "
              "the one figure that certifies every other figure.")
        return 1

    print(f"judge: {json.loads(judge_path.read_text(encoding='utf-8'))['judge_model']}")
    print(f"{len(human)} human labels\n")
    for metric in METRICS:
        pairs = [(score, judged.get(f"{record_id}|{metric}"))
                 for (record_id, name), score in sorted(human.items())
                 if name == metric and judged.get(f"{record_id}|{metric}") is not None]
        if not pairs:
            print(f"{metric:26} no labels")
            continue
        print(agreement([band_of(h) for h, _ in pairs],
                        [judge_band(j) for _, j in pairs], metric).render())
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv))
