"""Run the preregistered actionability boundary validation."""

from __future__ import annotations

import hashlib
import json
import pathlib
import time
from collections import defaultdict

from deepeval.test_case import LLMTestCase

from evals.judge_validation import matrix
from evals.meta_evaluation import agreement, judge_band
from evals.metrics.judged import actionability
from src.actionability_boundary_validation import (
    BOUNDARIES,
    load_validation_set,
    validate_set,
)
from src.generate import load_env
from src.judge import DashScopeJudge
from src.quotas import load_enquiries


DEVELOPMENT_OUT = pathlib.Path(
    ".local/actionability_boundary_validation_v5/judge_result.json"
)
HOLDOUT_OUT = pathlib.Path(".local/actionability_holdout_v1/judge_result.json")


def paths_for_run(holdout: bool) -> dict[str, pathlib.Path]:
    if holdout:
        return {
            "dataset": pathlib.Path("data/actionability_boundary_holdout_v1.jsonl"),
            "plan": pathlib.Path("docs/actionability-holdout-validation-plan.md"),
            "blind_scores": pathlib.Path(
                ".local/actionability_holdout_v1/blind_agent_scores.jsonl"
            ),
            "out": HOLDOUT_OUT,
        }
    return {
        "dataset": pathlib.Path("data/actionability_boundary_set_v4.jsonl"),
        "plan": pathlib.Path("docs/actionability-boundary-validation-plan.md"),
        "blind_scores": pathlib.Path(
            ".local/actionability_boundary_validation_v5/blind_agent_scores.jsonl"
        ),
        "out": DEVELOPMENT_OUT,
    }


def input_sha256(
    paths: tuple[pathlib.Path, ...],
) -> dict[str, str]:
    return {
        path.as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths if path.exists()
    }


def pair_ordering(items: list[dict]) -> dict:
    by_pair: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        by_pair[item["pair_id"]].append(item)

    details, by_boundary = [], defaultdict(list)
    for pair_id, pair in sorted(by_pair.items()):
        if len(pair) != 2:
            continue
        lower, upper = sorted(pair, key=lambda item: item["target_score"])
        ordered = upper["judge_score"] > lower["judge_score"]
        boundary = (lower["target_score"], upper["target_score"])
        details.append({
            "pair_id": pair_id,
            "boundary": list(boundary),
            "lower_score": lower["judge_score"],
            "upper_score": upper["judge_score"],
            "strictly_ordered": ordered,
        })
        by_boundary[boundary].append(ordered)
    counts = {
        f"{lower}/{upper}": {
            "ordered": sum(by_boundary[(lower, upper)]),
            "total": len(by_boundary[(lower, upper)]),
        }
        for lower, upper in BOUNDARIES
    }
    return {"pairs": details, "by_boundary": counts}


def acceptance(result: dict) -> dict:
    summary = result.get("agreement", {})
    ordering = result["pair_ordering"]["by_boundary"]
    criteria = {
        "all_18_calls_completed": len(result["items"]) == 18
        and not result["failures"],
        "no_thinking_disabled_retry": (
            result["usage"]["thinking_disabled_retries"] == 0
        ),
        "continuous_scoring_18_of_18": result["usage"]["with_logprobs"] == 18,
        "exact_band_at_least_14_of_18": (
            summary.get("exact_band_rate", 0) >= 14 / 18
        ),
        "quadratic_weighted_kappa_at_least_0_80": (
            summary.get("quadratic_weighted_kappa", 0) >= 0.80
        ),
        "every_prediction_within_one_band": (
            summary.get("within_one_band_rate", 0) == 1.0
        ),
        "at_least_two_of_three_pairs_ordered_per_boundary": all(
            value["total"] == 3 and value["ordered"] >= 2
            for value in ordering.values()
        ),
    }
    return {"passed": all(criteria.values()), "criteria": criteria}


def main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the preregistered actionability boundary validation."
    )
    parser.add_argument(
        "--holdout", action="store_true",
        help="use the untouched held-out enquiries and instrument-v3 plan",
    )
    parser.add_argument("--out", type=pathlib.Path)
    args = parser.parse_args(argv[1:])
    paths = paths_for_run(args.holdout)
    output = args.out or paths["out"]
    if output.exists():
        print(f"refusing to overwrite paid result: {output}")
        return 2

    rows = load_validation_set(str(paths["dataset"]))
    problems = validate_set(rows)
    if problems:
        raise ValueError("invalid boundary set: " + "; ".join(problems))

    load_env()
    judge = DashScopeJudge()
    enquiries = {row.id: row for row in load_enquiries()}
    items, failures = [], []
    total = len(rows)
    run_started = time.perf_counter()

    for index, row in enumerate(rows, start=1):
        enquiry = enquiries[row.record_id]
        email = f"Subject: {enquiry.subject}\n\n{enquiry.body}"
        item_started = time.perf_counter()
        print(
            f"[{index:02d}/{total}] {row.variant_id} scoring "
            f"(target {row.target_score}, expected band {row.expected_band})...",
            flush=True,
        )
        try:
            metric = actionability(judge)
            metric.measure(LLMTestCase(
                input=email, actual_output=row.draft_reply
            ), _show_indicator=False)
            score = float(metric.score)
            predicted_band = judge_band(score, "actionability")
            items.append({
                "variant_id": row.variant_id,
                "pair_id": row.pair_id,
                "record_id": row.record_id,
                "target_score": row.target_score,
                "expected_band": row.expected_band,
                "judge_score": score,
                "judge_band": predicted_band,
                "reason": metric.reason,
            })
            average = (time.perf_counter() - run_started) / index
            eta = average * (total - index)
            print(
                f"[{index:02d}/{total}] {row.variant_id} done: "
                f"score={score:.3f}, band={predicted_band}, "
                f"{time.perf_counter() - item_started:.1f}s, ETA~{eta:.0f}s",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001 - persisted, not hidden
            failures.append(f"{row.variant_id}: {type(exc).__name__}: {exc}")
            print(
                f"[{index:02d}/{total}] {row.variant_id} FAILED: "
                f"{type(exc).__name__}: {exc}", flush=True,
            )

    expected = [item["expected_band"] for item in items]
    predicted = [item["judge_band"] for item in items]
    result: dict = {
        "metric": "actionability",
        "status": (
            "preregistered_heldout_validation" if args.holdout
            else "preregistered_boundary_validation"
        ),
        "judge_model": judge.get_model_name(),
        "input_sha256": input_sha256((
            paths["dataset"], paths["plan"],
            pathlib.Path("evals/metrics/judged.py"), paths["blind_scores"],
        )),
        "items": items,
        "failures": failures,
        "usage": judge.usage.as_dict(),
        "confusion_matrix_rows_expected_columns_judge": matrix(
            expected, predicted
        ),
    }
    if items:
        summary = agreement(expected, predicted, "actionability")
        result["agreement"] = {
            "n": summary.n,
            "quadratic_weighted_kappa": summary.kappa,
            "spearman": summary.spearman,
            "exact_band_rate": summary.exact,
            "within_one_band_rate": summary.within_one,
        }
    result["pair_ordering"] = pair_ordering(items)
    result["acceptance"] = acceptance(result)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"scored {len(items)}/{len(rows)} variants; results: {output}")
    print(f"preregistered acceptance passed: {result['acceptance']['passed']}")
    return 1 if failures else 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv))
