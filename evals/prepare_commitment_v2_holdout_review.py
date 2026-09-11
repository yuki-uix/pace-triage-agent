"""Prepare the opaque commitment-v2 boundary holdout packet."""

from __future__ import annotations

import hashlib
import json
import pathlib
import random

from src.draft_evidence import draft_evidence


SOURCE = pathlib.Path("data/commitment_v2_holdout_v1.jsonl")
ENQUIRIES = pathlib.Path("data/enquiries.jsonl")
DEFAULT_OUT = pathlib.Path(".local/commitment_v2_holdout_v1")
SEED = 20260920


def _jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def prepare(out: pathlib.Path = DEFAULT_OUT) -> tuple[pathlib.Path, pathlib.Path]:
    variants = _jsonl(SOURCE)
    enquiries = {row["id"]: row for row in _jsonl(ENQUIRIES)}
    random.Random(SEED).shuffle(variants)
    packet, key = [], []
    for index, variant in enumerate(variants, start=1):
        blind_id = f"CHR-{index:02d}"
        enquiry = enquiries[variant["record_id"]]
        email = f"Subject: {enquiry['subject']}\n\n{enquiry['body']}"
        evidence = draft_evidence(email)
        packet.append({
            "blind_id": blind_id,
            "enquiry": email,
            "draft_reply": variant["draft_reply"],
            "evidence_ids": list(evidence.ids),
            "evidence_context": list(evidence.context),
        })
        key.append({
            "blind_id": blind_id,
            "variant_id": variant["variant_id"],
            "pair_id": variant["pair_id"],
            "record_id": variant["record_id"],
            "target_score": variant["target_score"],
            "expected_band": variant["expected_band"],
        })
    out.mkdir(parents=True, exist_ok=True)
    packet_path, key_path = out / "blind_packet.jsonl", out / "blind_key.json"
    packet_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n"
                                   for row in packet), encoding="utf-8")
    key_path.write_text(json.dumps({
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "seed": SEED,
        "items": key,
    }, indent=2) + "\n", encoding="utf-8")
    return packet_path, key_path


def main(argv: list[str]) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Prepare commitment-v2 holdout review.")
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv[1:])
    packet, key = prepare(args.out)
    print(f"blind packet: {packet}\nprivate key: {key}")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv))
