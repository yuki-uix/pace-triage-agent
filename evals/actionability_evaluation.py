"""Blind validation workflow for the actionability judge.

The human column is completed before any judge output is created. This workflow
remains separate from the recorded 2x2 comparison so validation reruns cannot
silently change historical model-selection results.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import time

from deepeval.test_case import LLMTestCase

from evals.meta_evaluation import agreement, band_of, judge_band, label_progress


METRIC = "actionability"
DEFAULT_DRAFTS = pathlib.Path("results/meta_eval_drafts.jsonl")
DEFAULT_OUT = pathlib.Path(".local/actionability")


def load_drafts(path: pathlib.Path) -> list[dict[str, str]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    required = {"record_id", "enquiry", "draft_reply"}
    seen: set[str] = set()
    for row in rows:
        missing = required - row.keys()
        if missing:
            raise ValueError(f"actionability draft missing: {', '.join(sorted(missing))}")
        if row["record_id"] in seen:
            raise ValueError(f"duplicate actionability record: {row['record_id']}")
        seen.add(row["record_id"])
    return rows


def build_worksheet(rows: list[dict[str, str]], path: pathlib.Path) -> None:
    from evals.metrics.judged import ACTIONABILITY_RUBRIC

    lines = [
        "# Actionability: blind human worksheet",
        "",
        "Choose the rubric band before any judge score exists. Enter the score in",
        "`actionability_labels.jsonl`; this worksheet deliberately contains no",
        "judge output.",
        "",
        "Actionability rewards a concrete operational path. Whether a stated",
        "deadline or outcome is supported belongs to commitment groundedness.",
        "",
        "## Rubric",
        "",
    ]
    for band in ACTIONABILITY_RUBRIC:
        low, high = band.score_range
        lines.append(f"- **{low}-{high}** — {band.expected_outcome}")
    lines.append("")
    for row in rows:
        lines.extend([
            "---", "", f"## {row['record_id']}", "",
            "**Customer email**", "", "```", row["enquiry"].strip(), "```", "",
            "**Draft reply**", "", "```", row["draft_reply"].strip(), "```", "",
            "| dimension | your score 0-10 |", "|---|---:|",
            "| actionability | |", "",
        ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def prepare(drafts_path: pathlib.Path, out: pathlib.Path) -> int:
    rows = load_drafts(drafts_path)
    out.mkdir(parents=True, exist_ok=True)
    labels_path = out / "actionability_labels.jsonl"
    if labels_path.exists() and label_progress(str(labels_path)).completed:
        print(f"refusing to overwrite completed labels: {labels_path}")
        return 2
    labels_path.write_text("".join(
        json.dumps({"record_id": row["record_id"], "metric": METRIC,
                    "human": None}) + "\n"
        for row in rows
    ), encoding="utf-8")
    worksheet = out / "actionability_worksheet.md"
    build_worksheet(rows, worksheet)
    print(f"prepared {len(rows)} blind labels: {labels_path}")
    print(f"worksheet: {worksheet}")
    print("no judge was called and no judge output exists")
    return 0


def status(out: pathlib.Path) -> int:
    labels_path = out / "actionability_labels.jsonl"
    if not labels_path.exists():
        print("run the prepare phase first")
        return 2
    progress = label_progress(str(labels_path))
    print(f"actionability human labels: {progress.completed}/{progress.total} complete")
    if progress.missing:
        print("judge remains disabled until every label is complete")
        return 1
    print("labels complete; the paid score phase is now unlocked")
    return 0


def score(drafts_path: pathlib.Path, out: pathlib.Path,
          result_path: pathlib.Path | None = None) -> int:
    labels_path = out / "actionability_labels.jsonl"
    if not labels_path.exists():
        print("run the prepare phase first")
        return 2
    progress = label_progress(str(labels_path))
    if progress.missing:
        print(
            f"human labels are incomplete: {progress.completed}/{progress.total}; "
            "judge calls remain disabled to prevent anchoring"
        )
        return 1

    result_path = result_path or out / "actionability_result.json"
    if result_path.exists():
        print(f"refusing to overwrite paid result: {result_path}")
        return 2

    from evals.metrics.judged import actionability
    from src.generate import load_env
    from src.judge import DashScopeJudge

    rows = load_drafts(drafts_path)
    human_rows = {
        row["record_id"]: int(row["human"])
        for line in labels_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and (row := json.loads(line))
    }
    if set(human_rows) != {row["record_id"] for row in rows}:
        raise ValueError("actionability labels do not match the prepared drafts")

    load_env()
    judge = DashScopeJudge()
    items, failures = [], []
    total = len(rows)
    run_started = time.perf_counter()
    for index, row in enumerate(rows, start=1):
        item_started = time.perf_counter()
        print(f"[{index:02d}/{total}] {row['record_id']} scoring...", flush=True)
        try:
            # GEval stores mutable score/reason state. A fresh instance per case
            # prevents one paid result from leaking into the next case.
            metric = actionability(judge)
            metric.measure(LLMTestCase(
                input=row["enquiry"], actual_output=row["draft_reply"]
            ), _show_indicator=False)
            judge_score = float(metric.score)
            items.append({
                "record_id": row["record_id"],
                "human_score": human_rows[row["record_id"]],
                "human_band": band_of(human_rows[row["record_id"]], METRIC),
                "judge_score": judge_score,
                "judge_band": judge_band(judge_score, METRIC),
                "reason": metric.reason,
            })
            average = (time.perf_counter() - run_started) / index
            eta = average * (total - index)
            print(
                f"[{index:02d}/{total}] {row['record_id']} done: "
                f"score={judge_score:.3f}, {time.perf_counter() - item_started:.1f}s, "
                f"ETA~{eta:.0f}s",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001 - persisted, not hidden
            failures.append(f"{row['record_id']}: {type(exc).__name__}: {exc}")
            print(
                f"[{index:02d}/{total}] {row['record_id']} FAILED: "
                f"{type(exc).__name__}: {exc}", flush=True,
            )

    human_bands = [item["human_band"] for item in items]
    judge_bands = [item["judge_band"] for item in items]
    result: dict = {
        "metric": METRIC,
        "status": "experimental_meta_evaluation_only",
        "judge_model": judge.get_model_name(),
        "items": items,
        "failures": failures,
        "usage": judge.usage.as_dict(),
        "input_sha256": {
            drafts_path.as_posix(): hashlib.sha256(drafts_path.read_bytes()).hexdigest(),
            labels_path.as_posix(): hashlib.sha256(labels_path.read_bytes()).hexdigest(),
            "evals/metrics/judged.py": hashlib.sha256(
                pathlib.Path("evals/metrics/judged.py").read_bytes()
            ).hexdigest(),
        },
    }
    if items:
        summary = agreement(human_bands, judge_bands, METRIC)
        result["agreement"] = {
            "n": summary.n,
            "quadratic_weighted_kappa": summary.kappa,
            "spearman": summary.spearman,
            "exact_band_rate": summary.exact,
            "within_one_band_rate": summary.within_one,
        }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(f"result: {result_path}")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Blind validation for the actionability metric."
    )
    parser.add_argument("phase", choices=["prepare", "status", "score"])
    parser.add_argument("--drafts", type=pathlib.Path, default=DEFAULT_DRAFTS)
    parser.add_argument("--out-dir", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument("--result", type=pathlib.Path)
    args = parser.parse_args(argv[1:])

    if args.phase == "prepare":
        return prepare(args.drafts, args.out_dir)
    if args.phase == "status":
        return status(args.out_dir)
    return score(args.drafts, args.out_dir, args.result)


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv))
