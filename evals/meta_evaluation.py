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

from evals.metrics.flow import canonical_name
from sklearn.metrics import cohen_kappa_score
from scipy.stats import spearmanr

# The bands come from the rubrics in `evals/metrics/judged.py`. A human labels a
# band, not a decimal: asking a person for 0.73 invents a precision they do not
# have, and the judge's decimal is compared by banding it the same way.
BANDS: tuple[tuple[int, int], ...] = ((0, 2), (3, 5), (6, 8), (9, 10))
TONE_AND_SUMMARY_BANDS: tuple[tuple[int, int], ...] = (
    (0, 3), (4, 6), (7, 8), (9, 10),
)
METRICS: tuple[str, ...] = (
    "commitment groundedness", "tone match", "summary quality",
    "domain correctness",
)
KNOWN_METRICS: frozenset[str] = frozenset((*METRICS, "actionability"))


def bands_for(metric: str) -> tuple[tuple[int, int], ...]:
    if metric in {"tone match", "summary quality"}:
        return TONE_AND_SUMMARY_BANDS
    if metric in {"commitment groundedness", "domain correctness", "actionability"}:
        return BANDS
    raise ValueError(f"unknown metric: {metric}")


def band_of(score_out_of_ten: float,
            metric: str = "commitment groundedness") -> int:
    """Index of the rubric band a 0-10 score falls in."""
    for index, (low, high) in enumerate(bands_for(metric)):
        if low <= score_out_of_ten <= high:
            return index
    raise ValueError(f"score {score_out_of_ten} is outside 0-10")


def judge_band(normalised_score: float,
               metric: str = "commitment groundedness") -> int:
    """GEval returns 0-1; the rubric is 0-10."""
    return band_of(round(normalised_score * 10), metric)


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
        "Read `docs/05-human-labeling.md` before starting. It defines the "
        "closed-book boundary, practice examples and blind workflow.",
        "",
        "The judge's own scores are not shown here on purpose: seeing them first "
        "would anchor your judgement, and an anchored human column measures "
        "nothing.",
        "",
    ]
    from evals.metrics.judged import (
        COMMITMENT_RUBRIC, DOMAIN_RUBRIC, SUMMARY_RUBRIC, TONE_RUBRIC,
    )
    for metric, rubric in (("commitment groundedness", COMMITMENT_RUBRIC),
                           ("tone match", TONE_RUBRIC),
                           ("summary quality", SUMMARY_RUBRIC),
                           ("domain correctness", DOMAIN_RUBRIC)):
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


@dataclass(frozen=True)
class LabelProgress:
    total: int
    completed: int
    missing: tuple[tuple[str, str], ...]


def label_progress(path: str) -> LabelProgress:
    """Report progress without loading or exposing any judge score."""
    rows: dict[tuple[str, str], int | None] = {}
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        key = (row["record_id"], row["metric"])
        if key[1] not in KNOWN_METRICS:
            raise ValueError(f"unknown metric in human-label row: {key[1]}")
        if key in rows:
            raise ValueError(f"duplicate human-label row: {key[0]} {key[1]}")
        value = row.get("human")
        if value is not None and (not isinstance(value, int) or isinstance(value, bool)
                                  or not 0 <= value <= 10):
            raise ValueError(f"{key[0]} {key[1]}: {value} is not an integer 0-10")
        rows[key] = value
    missing = tuple(key for key, value in rows.items() if value is None)
    return LabelProgress(
        total=len(rows),
        completed=len(rows) - len(missing),
        missing=missing,
    )


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
    parser.add_argument("phase", choices=["prepare", "status", "score"])
    parser.add_argument("--size", type=int, default=15)
    parser.add_argument("--out-dir", default="results")
    args = parser.parse_args(argv[1:])

    out = pathlib.Path(args.out_dir)
    labels_path = out / "meta_eval_labels.jsonl"
    judge_path = out / "meta_eval_judge.json"

    if args.phase == "status":
        return _status(labels_path)
    if args.phase == "score":
        return _score(labels_path, judge_path)
    return _prepare(args.size, out, labels_path, judge_path)


def _prepare(size: int, out: pathlib.Path, labels_path: pathlib.Path,
             judge_path: pathlib.Path) -> int:
    import os

    from openai import OpenAI

    from evals.metrics.judged import META_EVALUATION_METRICS
    from src.contract import FailureCounters
    from src.generate import load_env
    from src.judge import DashScopeJudge
    from src.pipeline import PipelineConfig, StageConfig, run
    from src.quotas import load_records
    from src.reference_pack import reference_context
    from deepeval.test_case import LLMTestCase

    load_env()
    client = OpenAI(api_key=os.environ["DASHSCOPE_API_KEY"],
                    base_url=os.environ["DASHSCOPE_BASE_URL"])
    config = PipelineConfig(StageConfig(os.environ["TRIAGE_MODEL_A"]),
                            StageConfig(os.environ["TRIAGE_MODEL_B"]))
    judge = DashScopeJudge()
    metrics = [build(judge) for build in META_EVALUATION_METRICS]

    records = select(load_records(), size)
    counters = FailureCounters()
    rows, judge_scores = [], {}

    # One bad judge response must not cost the whole run. A record that fails
    # is recorded and skipped; losing fourteen paid-for drafts to the fifteenth
    # is the kind of failure that makes people avoid re-running an evaluation.
    problems: list[str] = []

    for record in records:
        enquiry = f"Subject: {record.subject}\n\n{record.body}"
        try:
            item = run(client, config, record.id, record.subject, record.body,
                       counters)
        except Exception as exc:  # noqa: BLE001 - recorded, never swallowed
            problems.append(f"{record.id}: pipeline: {type(exc).__name__}: {exc}")
            print(f"  {record.id} SKIPPED (pipeline)", flush=True)
            continue

        rows.append({"record_id": record.id, "enquiry": enquiry,
                     "summary": item.summary, "draft_reply": item.draft_reply})

        scored = LLMTestCase(input=enquiry, actual_output=item.draft_reply)
        summary_case = LLMTestCase(input=enquiry, actual_output=item.summary)
        domain_case = LLMTestCase(
            input=enquiry,
            actual_output=item.draft_reply,
            context=reference_context(enquiry),
        )
        for metric in metrics:
            try:
                name = canonical_name(metric.__name__)
                case = summary_case if name == "summary quality" else scored
                if name == "domain correctness":
                    case = domain_case
                metric.measure(case)
                judge_scores[f"{record.id}|{name}"] = metric.score
            except Exception as exc:  # noqa: BLE001
                problems.append(
                    f"{record.id}: {canonical_name(metric.__name__)}: "
                    f"{type(exc).__name__}: {exc}")
        print(f"  {record.id} scored", flush=True)

    out.mkdir(parents=True, exist_ok=True)

    # Machine-readable drafts, written alongside the human worksheet. The
    # worksheet is a document for a person; recovering data by parsing it is
    # brittle and was: a NOISY record contained a forwarded-email '---' rule,
    # which is also the worksheet's record separator, and a top-up script split
    # the wrong block. Anything a later step needs gets its own file.
    with open(out / "meta_eval_drafts.jsonl", "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

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
        "problems": problems,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    worksheet = build_worksheet(rows, str(out / "meta_eval_worksheet.md"))

    print(f"\n{len(rows)} drafts written to {worksheet}")
    if problems:
        print(f"{len(problems)} judge/pipeline problem(s), none hidden:")
        for problem in problems:
            print(f"  - {problem}")
    print(f"judge scores: {judge_path}")
    print(f"label template (human: null): {labels_path}")
    print(f"continuous scoring rate: {judge.usage.continuous_scoring_rate:.0%} "
          f"of {judge.usage.calls} judge calls")
    print("\nFill in the human scores, then run: "
          "python -m evals.meta_evaluation score")
    return 0


def _status(labels_path: pathlib.Path) -> int:
    if not labels_path.exists():
        print("run the prepare phase first", flush=True)
        return 2
    progress = label_progress(str(labels_path))
    print(f"human labels: {progress.completed}/{progress.total} complete")
    if progress.missing:
        missing_records = list(dict.fromkeys(record_id
                                             for record_id, _ in progress.missing))
        print("records still incomplete: " + ", ".join(missing_records))
        print("judge scores remain hidden")
        return 1
    print("label set complete; it is safe to run the score phase")
    return 0


def _score(labels_path: pathlib.Path, judge_path: pathlib.Path) -> int:
    if not labels_path.exists() or not judge_path.exists():
        print("run the prepare phase first", flush=True)
        return 2

    progress = label_progress(str(labels_path))
    if progress.missing:
        print(
            f"human labels are incomplete: {progress.completed}/{progress.total}; "
            "agreement remains hidden to prevent anchoring."
        )
        print("run the status phase to list incomplete records")
        return 1

    human = load_human_labels(str(labels_path))
    judged = json.loads(judge_path.read_text(encoding="utf-8"))["scores"]

    if not human:
        print("no human labels filled in yet; agreement cannot be computed.")
        print("This number must come from a person: scoring the drafts with a "
              "second model and calling it judge/human agreement would fabricate "
              "the one figure that certifies every other figure.")
        return 1

    missing_judge = [
        (record_id, metric)
        for record_id, metric in human
        if judged.get(f"{record_id}|{metric}") is None
    ]
    if missing_judge:
        print(f"judge output is missing {len(missing_judge)} prepared label(s)")
        for record_id, metric in missing_judge:
            print(f"  - {record_id}: {metric}")
        return 2

    print(f"judge: {json.loads(judge_path.read_text(encoding='utf-8'))['judge_model']}")
    print(f"{len(human)} human labels\n")
    labelled_metrics = [metric for metric in METRICS
                        if any(name == metric for _, name in human)]
    for metric in labelled_metrics:
        pairs = [(score, judged.get(f"{record_id}|{metric}"))
                 for (record_id, name), score in sorted(human.items())
                 if name == metric and judged.get(f"{record_id}|{metric}") is not None]
        if not pairs:
            print(f"{metric:26} no labels")
            continue
        print(agreement([band_of(h, metric) for h, _ in pairs],
                        [judge_band(j, metric) for _, j in pairs], metric).render())
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv))
