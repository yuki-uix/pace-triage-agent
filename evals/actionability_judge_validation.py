"""Run the actionability judge against the balanced 24-variant challenge set."""

from __future__ import annotations

import hashlib
import json
import pathlib
import time

from deepeval.test_case import LLMTestCase

from evals.judge_validation import matrix
from evals.meta_evaluation import agreement, judge_band
from evals.metrics.judged import actionability
from src.actionability_validation import load_validation_set, validate_set
from src.generate import load_env
from src.judge import DashScopeJudge
from src.quotas import load_enquiries


DEFAULT_OUT = pathlib.Path(
    ".local/actionability_validation/actionability_judge_result.json"
)
PROVENANCE_FILES = (
    pathlib.Path("data/actionability_validation_set.jsonl"),
    pathlib.Path("evals/metrics/judged.py"),
    pathlib.Path(".local/actionability_validation/blind_agent_scores.jsonl"),
)


def input_sha256(
    paths: tuple[pathlib.Path, ...] = PROVENANCE_FILES,
) -> dict[str, str]:
    return {
        path.as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths if path.exists()
    }


def main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Score the balanced actionability challenge set."
    )
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv[1:])
    if args.out.exists():
        print(f"refusing to overwrite paid result: {args.out}")
        return 2

    rows = load_validation_set()
    problems = validate_set(rows)
    if problems:
        raise ValueError("invalid actionability validation set: "
                         + "; ".join(problems))

    load_env()
    judge = DashScopeJudge()
    enquiries = {row.id: row for row in load_enquiries()}
    scored, failures = [], []
    total = len(rows)
    run_started = time.perf_counter()

    for index, row in enumerate(rows, start=1):
        enquiry = enquiries[row.record_id]
        email = f"Subject: {enquiry.subject}\n\n{enquiry.body}"
        item_started = time.perf_counter()
        print(
            f"[{index:02d}/{total}] {row.variant_id} scoring "
            f"(expected band {row.expected_band})...",
            flush=True,
        )
        try:
            metric = actionability(judge)
            metric.measure(LLMTestCase(
                input=email, actual_output=row.draft_reply
            ), _show_indicator=False)
            score = float(metric.score)
            predicted_band = judge_band(score, "actionability")
            scored.append({
                "variant_id": row.variant_id,
                "record_id": row.record_id,
                "expected_band": row.expected_band,
                "judge_score": score,
                "judge_band": predicted_band,
                "reason": metric.reason,
            })
            elapsed = time.perf_counter() - item_started
            average = (time.perf_counter() - run_started) / index
            eta = average * (total - index)
            print(
                f"[{index:02d}/{total}] {row.variant_id} done: "
                f"score={score:.3f}, band={predicted_band}, "
                f"{elapsed:.1f}s, ETA~{eta:.0f}s",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001 - persisted, not hidden
            failures.append(f"{row.variant_id}: {type(exc).__name__}: {exc}")
            print(
                f"[{index:02d}/{total}] {row.variant_id} FAILED: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )

    expected = [item["expected_band"] for item in scored]
    predicted = [item["judge_band"] for item in scored]
    result: dict = {
        "metric": "actionability",
        "status": "experimental_balanced_validation",
        "judge_model": judge.get_model_name(),
        "input_sha256": input_sha256(),
        "expected_band_order": ["0-2", "3-5", "6-8", "9-10"],
        "confusion_matrix_rows_expected_columns_judge": matrix(
            expected, predicted
        ),
        "items": scored,
        "failures": failures,
        "usage": judge.usage.as_dict(),
    }
    if scored:
        summary = agreement(expected, predicted, "actionability")
        result["agreement"] = {
            "n": summary.n,
            "quadratic_weighted_kappa": summary.kappa,
            "spearman": summary.spearman,
            "exact_band_rate": summary.exact,
            "within_one_band_rate": summary.within_one,
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"scored {len(scored)}/{len(rows)} variants; results: {args.out}")
    if failures:
        print(f"{len(failures)} failure(s), all recorded")
        return 1
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv))
