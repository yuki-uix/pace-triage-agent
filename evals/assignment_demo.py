"""Run the frozen five-case baseline/evidence-backed assignment demo.

This is deliberately smaller than the 2x2 comparison.  It proves that the
complete path works and preserves paired outputs for inspection; it is not a
new production-readiness experiment.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys

from deepeval.test_case import LLMTestCase
from openai import OpenAI

from evals.metrics.flow import as_test_case
from evals.metrics.groundedness import EntityGroundedness
from evals.metrics.judged import actionability, commitment_groundedness_v2
from evals.metrics.safety import InjectionResistance, RefusalCorrectness
from src.contract import FailureCounters
from src.dataset import EnquiryRecord, Tag
from src.draft_evidence import draft_evidence
from src.generate import load_env
from src.judge import DashScopeJudge
from src.pipeline import PipelineConfig, StageConfig, run
from src.quotas import load_enquiries, load_golden
from src.redaction import build_analyzer

VERSION = "assignment-demo-v1"
DEFAULT_DATASET = pathlib.Path("data/assignment_demo_v1.jsonl")
DEFAULT_MANIFEST = pathlib.Path("data/assignment_demo_v1_manifest.json")
DEFAULT_GOLDEN = pathlib.Path("data/golden.jsonl")
DEFAULT_OUT = pathlib.Path("results/assignment_demo_v1.json")
DEFAULT_REVIEW = pathlib.Path(".local/assignment_demo_v1/review.jsonl")
DEFAULT_REPORT = pathlib.Path("results/assignment_demo_v1.md")
VARIANTS = ("baseline", "evidence_backed")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def code_version() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], check=True,
                              capture_output=True, text=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def validate_demo(dataset: pathlib.Path, manifest_path: pathlib.Path,
                  golden_path: pathlib.Path) -> tuple[list[EnquiryRecord], dict]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("version") != VERSION:
        raise ValueError(f"manifest version must be {VERSION}")

    source = pathlib.Path(manifest["source"])
    expected_ids = manifest["record_ids"]
    problems = []
    if sha256(source) != manifest["source_sha256"]:
        problems.append("source enquiry SHA-256 no longer matches the manifest")
    if sha256(golden_path) != manifest["golden_source_sha256"]:
        problems.append("golden SHA-256 no longer matches the manifest")

    demo = load_enquiries(str(dataset))
    if [row.id for row in demo] != expected_ids:
        problems.append(f"demo ids/order must be exactly {expected_ids}")
    source_by_id = {row.id: row for row in load_enquiries(str(source))}
    for row in demo:
        if row.id not in source_by_id or row != source_by_id[row.id]:
            problems.append(f"{row.id} is not a verbatim copy of the frozen source")

    labels = {row.id: row for row in load_golden(str(golden_path))}
    if any(record_id not in labels for record_id in expected_ids):
        problems.append("one or more demo ids have no golden label")
    if problems:
        raise ValueError("invalid assignment demo: " + "; ".join(problems))
    return ([EnquiryRecord.join(row, labels[row.id]) for row in demo], manifest)


def atomic_write(path: pathlib.Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False,
                                    sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def merge_counts(base: dict, current: dict) -> dict:
    return {key: base.get(key, 0) + current.get(key, 0)
            for key in ("schema_failures", "retry_exhaustions",
                        "provider_refusals")}


def merge_judge_usage(base: dict, current: dict) -> dict:
    keys = ("calls", "with_logprobs", "prompt_tokens", "completion_tokens",
            "reasoning_tokens", "thinking_disabled_retries")
    merged = {key: base.get(key, 0) + current.get(key, 0) for key in keys}
    merged["failures"] = base.get("failures", []) + current.get("failures", [])
    merged["continuous_scoring_rate"] = (
        merged["with_logprobs"] / merged["calls"] if merged["calls"] else 0.0)
    return merged


def review_rows(path: pathlib.Path, ids: list[str]) -> dict[str, dict]:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(
            {"record_id": record_id, "preferred": None, "reason": None}) + "\n"
            for record_id in ids), encoding="utf-8")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    if [row.get("record_id") for row in rows] != ids:
        raise ValueError(f"review rows must be exactly {ids} in that order")
    for row in rows:
        if row.get("preferred") not in (None, "baseline", "evidence_backed", "tie"):
            raise ValueError("preferred must be baseline, evidence_backed, tie or null")
        if row.get("preferred") is not None and not str(row.get("reason") or "").strip():
            raise ValueError("a completed human preference requires a reason")
    return {row["record_id"]: row for row in rows}


def empty_result(records: list[EnquiryRecord], manifest: dict,
                 dataset: pathlib.Path, manifest_path: pathlib.Path,
                 golden: pathlib.Path,
                 triage_model: str, draft_model: str, judge_model: str) -> dict:
    return {
        "version": VERSION,
        "status": "partial",
        "claim_scope": "assignment proof of concept; not production readiness",
        "code_version": code_version(),
        "inputs": {
            "dataset": dataset.as_posix(), "dataset_sha256": sha256(dataset),
            "manifest": manifest_path.as_posix(),
            "manifest_sha256": sha256(manifest_path),
            "golden": golden.as_posix(), "golden_sha256": sha256(golden),
            "source_sha256": manifest["source_sha256"],
            "record_ids": [record.id for record in records],
        },
        "models": {"triage": triage_model, "draft": draft_model,
                   "judge": judge_model, "thinking": False},
        "contract_failures": {variant: {} for variant in VARIANTS},
        "judge_usage": {},
        "cases": [{
            "record_id": record.id,
            "expected": {"case_type": record.expected_type.value,
                         "priority": record.expected_priority.value,
                         "tags": sorted(tag.value for tag in record.tags)},
            "evidence_ids": list(draft_evidence(
                f"Subject: {record.subject}\n\n{record.body}").ids),
            "variants": {},
            "human_review": {"preferred": None, "reason": None},
        } for record in records],
    }


def validate_resume(payload: dict, expected: dict) -> None:
    for field in ("version", "inputs", "models"):
        if payload.get(field) != expected.get(field):
            raise ValueError(f"resume result has different {field}")


def deterministic_scores(record: EnquiryRecord, output: dict, analyzer) -> dict:
    test_case = as_test_case(record, output)
    metrics = [EntityGroundedness(analyzer)]
    if Tag.REFUSAL in record.tags:
        metrics.append(RefusalCorrectness())
    if Tag.INJECTION in record.tags:
        metrics.append(InjectionResistance())
    scores = {}
    for metric in metrics:
        metric.measure(test_case)
        scores[metric.__name__] = {"score": metric.score, "reason": metric.reason}
    return scores


def judged_test_case(record: EnquiryRecord, output: dict) -> LLMTestCase:
    enquiry = f"Subject: {record.subject}\n\n{record.body}"
    evidence = draft_evidence(enquiry)
    return LLMTestCase(input=enquiry, actual_output=output["draft_reply"],
                       context=list(evidence.context))


def generated_variant(item) -> dict:
    output = {
        "case_type": item.case_type, "priority": item.priority,
        "confidence": item.confidence, "summary": item.summary,
        "draft_reply": item.draft_reply,
    }
    return {
        "status": "generated", "output": output,
        "evidence_ids": list(item.evidence_ids), "traces": item.traces,
        "deterministic_scores": {}, "judged_scores": {}, "skipped": [],
    }


def render_report(payload: dict) -> str:
    lines = ["# Assignment demo v1", "", payload["claim_scope"] + ".", "",
             "| Case | Variant | Entity | Commitment v2 | Actionability | Refusal | Injection |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for case in payload["cases"]:
        for variant in VARIANTS:
            row = case["variants"].get(variant, {})
            deterministic = row.get("deterministic_scores", {})
            judged = row.get("judged_scores", {})
            value = lambda group, name: (  # noqa: E731
                "—" if name not in group else f'{group[name]["score"]:.3f}')
            lines.append(
                f'| {case["record_id"]} | {variant} | '
                f'{value(deterministic, "entity groundedness")} | '
                f'{value(judged, "commitment groundedness v2")} | '
                f'{value(judged, "actionability")} | '
                f'{value(deterministic, "refusal correctness")} | '
                f'{value(deterministic, "injection resistance")} |')
    lines += ["", "## Paired score deltas", "",
              "Positive values favour the evidence-backed draft.", "",
              "| Case | Commitment v2 Δ | Actionability Δ |",
              "|---|---:|---:|"]
    for case in payload["cases"]:
        baseline = case["variants"].get("baseline", {}).get("judged_scores", {})
        evidence = case["variants"].get("evidence_backed", {}).get(
            "judged_scores", {})
        deltas = []
        for name in ("commitment groundedness v2", "actionability"):
            if name not in baseline or name not in evidence:
                deltas.append("—")
            else:
                delta = evidence[name]["score"] - baseline[name]["score"]
                deltas.append(f"{delta:+.3f}")
        lines.append(f'| {case["record_id"]} | {deltas[0]} | {deltas[1]} |')
    lines += ["", "## Human pair review", "",
              "| Case | Preferred | Reason |", "|---|---|---|"]
    for case in payload["cases"]:
        review = case["human_review"]
        lines.append(f'| {case["record_id"]} | {review["preferred"] or "pending"} '
                     f'| {review["reason"] or "pending"} |')
    lines += ["", "## Limitations", "",
              "Five frozen synthetic cases demonstrate execution and make paired "
              "differences inspectable. They do not estimate production error rates, "
              "regulatory readiness or statistical significance.", ""]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=pathlib.Path, default=DEFAULT_DATASET)
    parser.add_argument("--manifest", type=pathlib.Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--golden", type=pathlib.Path, default=DEFAULT_GOLDEN)
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument("--review", type=pathlib.Path, default=DEFAULT_REVIEW)
    parser.add_argument("--report", type=pathlib.Path, default=DEFAULT_REPORT)
    parser.add_argument("--triage-model", default=None)
    parser.add_argument("--draft-model", default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--validate-only", action="store_true",
                        help="validate frozen inputs and print evidence ids; no calls")
    args = parser.parse_args(argv[1:])

    records, manifest = validate_demo(args.dataset, args.manifest, args.golden)
    if args.validate_only:
        print(f"{VERSION}: {len(records)} frozen records valid")
        for record in records:
            evidence = draft_evidence(f"Subject: {record.subject}\n\n{record.body}")
            print(f"  {record.id}: {', '.join(evidence.ids) or 'no selected evidence'}")
        return 0
    load_env()
    base = PipelineConfig.from_env(args.triage_model, args.draft_model)
    judge = DashScopeJudge()
    expected = empty_result(records, manifest, args.dataset, args.manifest,
                            args.golden,
                            base.triage.model, base.draft.model,
                            judge.get_model_name())
    if args.out.exists():
        if not args.resume:
            print(f"refusing to overwrite existing paid result: {args.out}")
            return 2
        payload = json.loads(args.out.read_text(encoding="utf-8"))
        validate_resume(payload, expected)
    else:
        payload = expected

    reviews = review_rows(args.review, [record.id for record in records])
    for case in payload["cases"]:
        case["human_review"] = {
            "preferred": reviews[case["record_id"]].get("preferred"),
            "reason": reviews[case["record_id"]].get("reason"),
        }

    client = OpenAI(api_key=os.environ["DASHSCOPE_API_KEY"],
                    base_url=os.environ["DASHSCOPE_BASE_URL"])
    analyzer = build_analyzer()
    base_contracts = payload.get("contract_failures", {})
    base_judge = payload.get("judge_usage", {})
    current_contracts = {variant: FailureCounters() for variant in VARIANTS}
    failures = []

    for index, (record, case) in enumerate(zip(records, payload["cases"]), start=1):
        for variant in VARIANTS:
            if case["variants"].get(variant, {}).get("status") == "complete":
                print(f"[{index}/5] {record.id} {variant}: reused", flush=True)
                continue
            print(f"[{index}/5] {record.id} {variant}: running", flush=True)
            config = PipelineConfig(
                triage=StageConfig(base.triage.model),
                draft=StageConfig(base.draft.model),
                evidence_backed=variant == "evidence_backed")
            row = case["variants"].get(variant, {})
            if not row.get("output"):
                try:
                    item = run(client, config, record.id, record.subject, record.body,
                               current_contracts[variant])
                    row = generated_variant(item)
                    case["variants"][variant] = row
                    atomic_write(args.out, payload)
                except Exception as exc:  # noqa: BLE001
                    error = f"{type(exc).__name__}: {exc}"
                    case["variants"][variant] = {"status": "failed", "error": error}
                    failures.append(f"{record.id} {variant}: {error}")
                    print(f"[{index}/5] {record.id} {variant}: failed: {error}",
                          flush=True)
                    payload["contract_failures"] = {
                        name: merge_counts(base_contracts.get(name, {}),
                                           counters.as_dict())
                        for name, counters in current_contracts.items()}
                    payload["judge_usage"] = merge_judge_usage(
                        base_judge, judge.usage.as_dict())
                    atomic_write(args.out, payload)
                    continue

            row.pop("error", None)
            row.pop("score_error", None)
            try:
                if not row.get("deterministic_scores"):
                    row["deterministic_scores"] = deterministic_scores(
                        record, row["output"], analyzer)
                if Tag.REFUSAL in record.tags:
                    row["skipped"] = ["commitment groundedness v2", "actionability"]
                else:
                    test_case = judged_test_case(record, row["output"])
                    for name, build in (("commitment groundedness v2",
                                         commitment_groundedness_v2),
                                        ("actionability", actionability)):
                        if name in row["judged_scores"]:
                            continue
                        metric = build(judge)
                        metric.measure(test_case, _show_indicator=False)
                        row["judged_scores"][name] = {
                            "score": float(metric.score),
                            "reason": str(metric.reason),
                        }
                        atomic_write(args.out, payload)
                row["status"] = "complete"
                print(f"[{index}/5] {record.id} {variant}: complete", flush=True)
            except Exception as exc:  # noqa: BLE001
                error = f"{type(exc).__name__}: {exc}"
                row["status"] = "generated"
                row["score_error"] = error
                failures.append(f"{record.id} {variant} scoring: {error}")
                print(f"[{index}/5] {record.id} {variant}: scoring failed: {error}",
                      flush=True)
            payload["contract_failures"] = {
                name: merge_counts(base_contracts.get(name, {}), counters.as_dict())
                for name, counters in current_contracts.items()}
            payload["judge_usage"] = merge_judge_usage(
                base_judge, judge.usage.as_dict())
            atomic_write(args.out, payload)

    complete = all(case["variants"].get(variant, {}).get("status") == "complete"
                   for case in payload["cases"] for variant in VARIANTS)
    reviews_complete = all(case["human_review"]["preferred"] is not None
                           for case in payload["cases"])
    payload["status"] = ("complete" if complete and reviews_complete
                         else "awaiting_human_review" if complete else "partial")
    payload["failures"] = failures
    atomic_write(args.out, payload)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(payload), encoding="utf-8")
    print(f"result: {args.out}; report: {args.report}; review: {args.review}")
    if complete and not reviews_complete:
        print("generation/scoring complete; fill the five review rows, then rerun "
              "with --resume to finalise the report")
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
