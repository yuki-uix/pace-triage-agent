"""Run the source-backed domain judge against the balanced challenge set."""

from __future__ import annotations

import json
import pathlib
import time

from deepeval.test_case import LLMTestCase

from evals.meta_evaluation import agreement, judge_band
from evals.metrics.judged import domain_correctness
from src.generate import load_env
from src.judge import DashScopeJudge
from src.judge_validation import load_validation_set, validate_set
from src.quotas import load_enquiries
from src.reference_pack import reference_context


def matrix(expected: list[int], predicted: list[int]) -> list[list[int]]:
    result = [[0 for _ in range(4)] for _ in range(4)]
    for expected_band, predicted_band in zip(expected, predicted):
        result[expected_band][predicted_band] += 1
    return result


def main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Score the balanced source-backed judge challenge set."
    )
    parser.add_argument("--out", default="results/judge_validation.json")
    args = parser.parse_args(argv[1:])

    rows = load_validation_set()
    problems = validate_set(rows)
    if problems:
        raise ValueError("invalid judge validation set: " + "; ".join(problems))

    load_env()
    judge = DashScopeJudge()
    metric = domain_correctness(judge)
    enquiries = {row.id: row for row in load_enquiries()}
    scored, failures = [], []

    total = len(rows)
    run_started = time.perf_counter()
    for index, row in enumerate(rows, start=1):
        enquiry = enquiries[row.record_id]
        email = f"Subject: {enquiry.subject}\n\n{enquiry.body}"
        case = LLMTestCase(
            input=email,
            actual_output=row.draft_reply,
            context=reference_context(email),
        )
        item_started = time.perf_counter()
        print(
            f"[{index:02d}/{total}] {row.variant_id} scoring "
            f"(expected band {row.expected_band})...",
            flush=True,
        )
        try:
            # DeepEval's animated indicator is noisy in captured/non-interactive
            # terminals and hides which paid call is running. Our stable line
            # progress is more useful and survives in CI logs.
            metric.measure(case, _show_indicator=False)
            score = float(metric.score)
            predicted_band = judge_band(score)
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
            failures.append(
                f"{row.variant_id}: {type(exc).__name__}: {exc}"
            )
            print(
                f"[{index:02d}/{total}] {row.variant_id} FAILED: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )

    expected = [item["expected_band"] for item in scored]
    predicted = [item["judge_band"] for item in scored]
    result: dict = {
        "judge_model": judge.get_model_name(),
        "expected_band_order": ["0-2", "3-5", "6-8", "9-10"],
        "confusion_matrix_rows_expected_columns_judge": matrix(expected, predicted),
        "items": scored,
        "failures": failures,
        "usage": judge.usage.as_dict(),
    }
    if scored:
        summary = agreement(expected, predicted, "domain correctness")
        result["agreement"] = {
            "n": summary.n,
            "quadratic_weighted_kappa": summary.kappa,
            "spearman": summary.spearman,
            "exact_band_rate": summary.exact,
            "within_one_band_rate": summary.within_one,
        }

    output = pathlib.Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"scored {len(scored)}/{len(rows)} variants; results: {output}")
    if failures:
        print(f"{len(failures)} failure(s), all recorded")
        return 1
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv))
