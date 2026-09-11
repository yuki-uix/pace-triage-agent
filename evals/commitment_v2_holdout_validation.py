"""Run the preregistered disjoint commitment-v2 boundary holdout."""

from __future__ import annotations

import hashlib
import json
import pathlib
import time
from collections import defaultdict

from deepeval.test_case import LLMTestCase

from evals.judge_validation import matrix
from evals.meta_evaluation import agreement, judge_band
from evals.metrics.judged import commitment_groundedness_v2
from src.commitment_v2_holdout import BOUNDARIES, load_holdout, validate_holdout
from src.draft_evidence import draft_evidence
from src.generate import load_env
from src.judge import DashScopeJudge
from src.quotas import load_enquiries


ROOT = pathlib.Path(".local/commitment_v2_holdout_v1")
SOURCE = pathlib.Path("data/commitment_v2_holdout_v1.jsonl")
KEY = ROOT / "blind_key.json"
SCORES = ROOT / "blind_agent_scores.jsonl"
DEFAULT_OUT = ROOT / "judge_result.json"
PROVENANCE = (
    SOURCE, pathlib.Path("docs/commitment-v2-holdout-plan.md"),
    pathlib.Path("evals/metrics/judged.py"),
    pathlib.Path("knowledge/source_manifest.json"),
    pathlib.Path("knowledge/reference_claims.jsonl"),
    pathlib.Path("knowledge/service_catalogue_manifest.json"),
    pathlib.Path("knowledge/service_catalogue.jsonl"), KEY, SCORES,
)


def input_sha256(paths=PROVENANCE) -> dict[str, str]:
    return {path.as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths if path.exists()}


def pair_ordering(items: list[dict], score_key: str) -> dict:
    pairs: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        pairs[item["pair_id"]].append(item)
    details, counts = [], defaultdict(list)
    for pair_id, pair in sorted(pairs.items()):
        lower, upper = sorted(pair, key=lambda item: item["target_score"])
        ordered = upper[score_key] > lower[score_key]
        boundary = (lower["target_score"], upper["target_score"])
        details.append({"pair_id": pair_id, "boundary": list(boundary),
                        "lower": lower[score_key], "upper": upper[score_key],
                        "strictly_ordered": ordered})
        counts[boundary].append(ordered)
    return {"pairs": details, "by_boundary": {
        f"{a}/{b}": {"ordered": sum(counts[(a, b)]),
                     "total": len(counts[(a, b)])}
        for a, b in BOUNDARIES
    }}


def load_blind_review() -> tuple[dict, dict]:
    document = json.loads(KEY.read_text(encoding="utf-8"))
    if document.get("source_sha256") != hashlib.sha256(SOURCE.read_bytes()).hexdigest():
        raise ValueError("blind key was prepared from another holdout version")
    key = document["items"]
    scores = [json.loads(line) for line in SCORES.read_text(encoding="utf-8").splitlines()
              if line.strip()]
    if len(scores) != 18 or len({row.get("blind_id") for row in scores}) != 18:
        raise ValueError("blind scores must contain 18 unique ids")
    by_id = {row["blind_id"]: row for row in scores}
    if set(by_id) != {row["blind_id"] for row in key}:
        raise ValueError("blind score ids do not match the private key")
    joined = []
    for row in key:
        score = by_id[row["blind_id"]]
        if type(score.get("score")) is not int or score["score"] not in range(11):
            raise ValueError("blind scores must be integers from 0 to 10")
        if score.get("band") != judge_band(score["score"] / 10,
                                            "commitment groundedness v2"):
            raise ValueError("blind score and band disagree")
        joined.append({**row, "blind_score": score["score"],
                       "blind_band": score["band"]})
    summary = agreement([x["expected_band"] for x in joined],
                        [x["blind_band"] for x in joined],
                        "commitment groundedness v2")
    return ({"n": summary.n, "exact_band_rate": summary.exact,
             "quadratic_weighted_kappa": summary.kappa,
             "within_one_band_rate": summary.within_one,
             "spearman": summary.spearman},
            pair_ordering(joined, "blind_score"))


def acceptance(result: dict) -> dict:
    judged, blind = result.get("agreement", {}), result["blind_review_agreement"]
    criteria = {
        "all_18_calls_completed": len(result["items"]) == 18 and not result["failures"],
        "no_thinking_disabled_retry": result["usage"]["thinking_disabled_retries"] == 0,
        "continuous_scoring_18_of_18": result["usage"]["with_logprobs"] == 18,
        "judge_exact_at_least_15_of_18": judged.get("exact_band_rate", 0) >= 15 / 18,
        "judge_kappa_at_least_0_85": judged.get("quadratic_weighted_kappa", 0) >= 0.85,
        "judge_within_one_18_of_18": judged.get("within_one_band_rate", 0) == 1.0,
        "judge_two_pairs_ordered_per_boundary": all(
            value["total"] == 3 and value["ordered"] >= 2
            for value in result["pair_ordering"]["by_boundary"].values()),
        "blind_exact_at_least_15_of_18": blind["exact_band_rate"] >= 15 / 18,
        "blind_kappa_at_least_0_85": blind["quadratic_weighted_kappa"] >= 0.85,
        "blind_within_one_18_of_18": blind["within_one_band_rate"] == 1.0,
        "blind_two_pairs_ordered_per_boundary": all(
            value["total"] == 3 and value["ordered"] >= 2
            for value in result["blind_pair_ordering"]["by_boundary"].values()),
    }
    return {"passed": all(criteria.values()), "criteria": criteria}


def assignment_acceptance(result: dict) -> dict:
    """A proof-of-concept gate for coursework, not a production safety claim.

    The preregistered gate above remains untouched.  This profile asks whether
    the judge is directionally useful for demonstrating the evidence-backed
    workflow: at least two thirds of bands must match exactly, every miss must
    stay within one adjacent band, agreement must remain strong, and the judge
    must preserve the ordering around each rubric boundary.
    """
    judged, blind = result.get("agreement", {}), result["blind_review_agreement"]
    criteria = {
        "all_18_calls_completed": len(result["items"]) == 18 and not result["failures"],
        "continuous_scoring_18_of_18": result["usage"]["with_logprobs"] == 18,
        "judge_exact_at_least_12_of_18": judged.get("exact_band_rate", 0) >= 12 / 18,
        "judge_kappa_at_least_0_80": judged.get("quadratic_weighted_kappa", 0) >= 0.80,
        "judge_within_one_18_of_18": judged.get("within_one_band_rate", 0) == 1.0,
        "judge_two_pairs_ordered_per_boundary": all(
            value["total"] == 3 and value["ordered"] >= 2
            for value in result["pair_ordering"]["by_boundary"].values()),
        "blind_exact_at_least_12_of_18": blind["exact_band_rate"] >= 12 / 18,
        "blind_kappa_at_least_0_80": blind["quadratic_weighted_kappa"] >= 0.80,
        "blind_within_one_18_of_18": blind["within_one_band_rate"] == 1.0,
        "blind_two_pairs_ordered_per_boundary": all(
            value["total"] == 3 and value["ordered"] >= 2
            for value in result["blind_pair_ordering"]["by_boundary"].values()),
    }
    return {"profile": "assignment-poc-v1", "passed": all(criteria.values()),
            "criteria": criteria,
            "claim": ("Suitable for demonstrating the end-to-end approach; "
                      "not evidence of production safety or regulatory readiness.")}


def main(argv: list[str]) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Score the commitment-v2 holdout.")
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv[1:])
    if args.out.exists():
        print(f"refusing to overwrite paid result: {args.out}")
        return 2
    rows = load_holdout()
    problems = validate_holdout(rows)
    if problems:
        raise ValueError("invalid holdout: " + "; ".join(problems))
    blind, blind_ordering = load_blind_review()
    load_env()
    judge = DashScopeJudge()
    enquiries = {row.id: row for row in load_enquiries()}
    items, failures, started = [], [], time.perf_counter()
    for index, row in enumerate(rows, start=1):
        enquiry = enquiries[row.record_id]
        email = f"Subject: {enquiry.subject}\n\n{enquiry.body}"
        evidence = draft_evidence(email)
        item_started = time.perf_counter()
        print(f"[{index:02d}/18] {row.variant_id} scoring "
              f"(target {row.target_score})...", flush=True)
        try:
            metric = commitment_groundedness_v2(judge)
            metric.measure(LLMTestCase(input=email, actual_output=row.draft_reply,
                                      context=list(evidence.context)),
                           _show_indicator=False)
            score = float(metric.score)
            items.append({"variant_id": row.variant_id, "pair_id": row.pair_id,
                          "record_id": row.record_id, "target_score": row.target_score,
                          "expected_band": row.expected_band,
                          "evidence_ids": list(evidence.ids), "judge_score": score,
                          "judge_band": judge_band(score, "commitment groundedness v2"),
                          "reason": metric.reason})
            avg = (time.perf_counter() - started) / index
            print(f"[{index:02d}/18] done score={score:.3f}, "
                  f"{time.perf_counter()-item_started:.1f}s, ETA~{avg*(18-index):.0f}s",
                  flush=True)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{row.variant_id}: {type(exc).__name__}: {exc}")
    expected, predicted = ([x["expected_band"] for x in items],
                           [x["judge_band"] for x in items])
    result = {"metric": "commitment groundedness v2", "status": "heldout_validation",
              "judge_model": judge.get_model_name(), "input_sha256": input_sha256(),
              "blind_review_agreement": blind, "blind_pair_ordering": blind_ordering,
              "items": items, "failures": failures, "usage": judge.usage.as_dict(),
              "confusion_matrix_rows_expected_columns_judge": matrix(expected, predicted)}
    if items:
        summary = agreement(expected, predicted, "commitment groundedness v2")
        result["agreement"] = {"n": summary.n, "exact_band_rate": summary.exact,
                               "quadratic_weighted_kappa": summary.kappa,
                               "within_one_band_rate": summary.within_one,
                               "spearman": summary.spearman}
    result["pair_ordering"] = pair_ordering(items, "judge_score")
    result["acceptance"] = acceptance(result)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"scored {len(items)}/18; acceptance passed: {result['acceptance']['passed']}")
    return 0 if result["acceptance"]["passed"] else 1


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv))
