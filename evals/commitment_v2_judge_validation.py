"""Run the preregistered evidence-aware commitment validation."""

from __future__ import annotations

import hashlib
import json
import pathlib
import time

from deepeval.test_case import LLMTestCase

from evals.judge_validation import matrix
from evals.meta_evaluation import agreement, judge_band
from evals.metrics.judged import commitment_groundedness_v2
from src.commitment_v2_validation import load_validation_set, validate_set
from src.draft_evidence import draft_evidence
from src.generate import load_env
from src.judge import DashScopeJudge
from src.quotas import load_enquiries


DEFAULT_DIR = pathlib.Path(".local/commitment_v2_validation")
DEFAULT_OUT = DEFAULT_DIR / "judge_result.json"
BLIND_KEY = DEFAULT_DIR / "blind_key.json"
BLIND_SCORES = DEFAULT_DIR / "blind_agent_scores.jsonl"
PROVENANCE_FILES = (
    pathlib.Path("data/commitment_v2_validation_set.jsonl"),
    pathlib.Path("docs/commitment-v2-validation-plan.md"),
    pathlib.Path("evals/metrics/judged.py"),
    pathlib.Path("knowledge/source_manifest.json"),
    pathlib.Path("knowledge/reference_claims.jsonl"),
    pathlib.Path("knowledge/service_catalogue_manifest.json"),
    pathlib.Path("knowledge/service_catalogue.jsonl"),
    BLIND_KEY,
    BLIND_SCORES,
)


def input_sha256(paths: tuple[pathlib.Path, ...] = PROVENANCE_FILES) -> dict[str, str]:
    return {path.as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths if path.exists()}


def load_blind_review(
    key_path: pathlib.Path = BLIND_KEY,
    scores_path: pathlib.Path = BLIND_SCORES,
) -> dict:
    if not key_path.exists() or not scores_path.exists():
        raise ValueError("complete the blind review before starting the paid Judge run")
    key_document = json.loads(key_path.read_text(encoding="utf-8"))
    current_source = pathlib.Path("data/commitment_v2_validation_set.jsonl")
    if key_document.get("source_sha256") != hashlib.sha256(current_source.read_bytes()).hexdigest():
        raise ValueError("blind key was prepared from a different validation dataset")
    key = key_document["items"]
    scores = [json.loads(line) for line in scores_path.read_text(encoding="utf-8").splitlines()
              if line.strip()]
    expected_ids = {item["blind_id"] for item in key}
    if len(scores) != 24 or {item.get("blind_id") for item in scores} != expected_ids:
        raise ValueError("blind_agent_scores.jsonl must contain each of the 24 blind ids once")
    if any(type(item.get("band")) is not int or item["band"] not in range(4)
           or not str(item.get("reason", "")).strip() for item in scores):
        raise ValueError("each blind score needs band 0-3 and a non-empty reason")
    if len({item["blind_id"] for item in scores}) != 24:
        raise ValueError("blind score ids are not unique")
    score_by_id = {item["blind_id"]: item["band"] for item in scores}
    expected = [item["expected_band"] for item in key]
    predicted = [score_by_id[item["blind_id"]] for item in key]
    summary = agreement(expected, predicted, "commitment groundedness v2")
    return {
        "n": summary.n,
        "quadratic_weighted_kappa": summary.kappa,
        "spearman": summary.spearman,
        "exact_band_rate": summary.exact,
        "within_one_band_rate": summary.within_one,
    }


def acceptance(result: dict) -> dict:
    judged = result.get("agreement", {})
    blind = result.get("blind_review_agreement", {})
    criteria = {
        "all_24_calls_completed": len(result["items"]) == 24 and not result["failures"],
        "no_thinking_disabled_retry": result["usage"]["thinking_disabled_retries"] == 0,
        "continuous_scoring_24_of_24": result["usage"]["with_logprobs"] == 24,
        "judge_exact_band_at_least_20_of_24": judged.get("exact_band_rate", 0) >= 20 / 24,
        "judge_kappa_at_least_0_85": judged.get("quadratic_weighted_kappa", 0) >= 0.85,
        "judge_every_item_within_one_band": judged.get("within_one_band_rate", 0) == 1.0,
        "blind_exact_band_at_least_20_of_24": blind.get("exact_band_rate", 0) >= 20 / 24,
        "blind_kappa_at_least_0_85": blind.get("quadratic_weighted_kappa", 0) >= 0.85,
        "blind_every_item_within_one_band": blind.get("within_one_band_rate", 0) == 1.0,
    }
    return {"passed": all(criteria.values()), "criteria": criteria}


def main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Score the frozen commitment-v2 set.")
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv[1:])
    if args.out.exists():
        print(f"refusing to overwrite paid result: {args.out}")
        return 2

    rows = load_validation_set()
    problems = validate_set(rows)
    if problems:
        raise ValueError("invalid commitment-v2 validation set: " + "; ".join(problems))
    blind_agreement = load_blind_review()

    load_env()
    judge = DashScopeJudge()
    enquiries = {row.id: row for row in load_enquiries()}
    items, failures = [], []
    started = time.perf_counter()
    for index, row in enumerate(rows, start=1):
        enquiry = enquiries[row.record_id]
        email = f"Subject: {enquiry.subject}\n\n{enquiry.body}"
        evidence = draft_evidence(email)
        item_started = time.perf_counter()
        print(f"[{index:02d}/24] {row.variant_id} scoring "
              f"(expected band {row.expected_band})...", flush=True)
        try:
            metric = commitment_groundedness_v2(judge)
            metric.measure(LLMTestCase(
                input=email,
                actual_output=row.draft_reply,
                context=list(evidence.context),
            ), _show_indicator=False)
            score = float(metric.score)
            band = judge_band(score, "commitment groundedness v2")
            items.append({
                "variant_id": row.variant_id,
                "record_id": row.record_id,
                "evidence_ids": list(evidence.ids),
                "expected_band": row.expected_band,
                "judge_score": score,
                "judge_band": band,
                "reason": metric.reason,
            })
            average = (time.perf_counter() - started) / index
            print(f"[{index:02d}/24] {row.variant_id} done: score={score:.3f}, "
                  f"band={band}, {time.perf_counter() - item_started:.1f}s, "
                  f"ETA~{average * (24 - index):.0f}s", flush=True)
        except Exception as exc:  # noqa: BLE001 - persisted, not hidden
            failures.append(f"{row.variant_id}: {type(exc).__name__}: {exc}")
            print(f"[{index:02d}/24] {row.variant_id} FAILED: "
                  f"{type(exc).__name__}: {exc}", flush=True)

    expected = [item["expected_band"] for item in items]
    predicted = [item["judge_band"] for item in items]
    result = {
        "metric": "commitment groundedness v2",
        "status": "preregistered_evidence_validation",
        "judge_model": judge.get_model_name(),
        "input_sha256": input_sha256(),
        "blind_review_agreement": blind_agreement,
        "items": items,
        "failures": failures,
        "usage": judge.usage.as_dict(),
        "confusion_matrix_rows_expected_columns_judge": matrix(expected, predicted),
    }
    if items:
        summary = agreement(expected, predicted, "commitment groundedness v2")
        result["agreement"] = {
            "n": summary.n,
            "quadratic_weighted_kappa": summary.kappa,
            "spearman": summary.spearman,
            "exact_band_rate": summary.exact,
            "within_one_band_rate": summary.within_one,
        }
    result["acceptance"] = acceptance(result)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"scored {len(items)}/{len(rows)} variants; results: {args.out}")
    print(f"preregistered acceptance passed: {result['acceptance']['passed']}")
    return 0 if result["acceptance"]["passed"] else 1


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv))
