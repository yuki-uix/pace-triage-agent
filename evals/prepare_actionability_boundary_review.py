"""Prepare an opaque review packet for the actionability boundary set."""

from __future__ import annotations

import hashlib
import json
import pathlib
import random


SOURCE = pathlib.Path("data/actionability_boundary_set_v4.jsonl")
ENQUIRIES = pathlib.Path("data/enquiries.jsonl")
DEFAULT_OUT = pathlib.Path(".local/actionability_boundary_validation_v5")
SEED = 20260916


def _jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def prepare(out: pathlib.Path = DEFAULT_OUT) -> tuple[pathlib.Path, pathlib.Path]:
    variants = _jsonl(SOURCE)
    enquiries = {row["id"]: row for row in _jsonl(ENQUIRIES)}
    random.Random(SEED).shuffle(variants)

    packet: list[dict] = []
    key: list[dict] = []
    for index, variant in enumerate(variants, start=1):
        blind_id = f"BR-{index:02d}"
        enquiry = enquiries[variant["record_id"]]
        packet.append({
            "blind_id": blind_id,
            "enquiry": f"Subject: {enquiry['subject']}\n\n{enquiry['body']}",
            "draft_reply": variant["draft_reply"],
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
    packet_path = out / "blind_packet.jsonl"
    key_path = out / "blind_key.json"
    packet_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in packet),
        encoding="utf-8",
    )
    key_path.write_text(json.dumps({
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "seed": SEED,
        "items": key,
    }, indent=2) + "\n", encoding="utf-8")
    return packet_path, key_path


def main() -> int:
    packet, key = prepare()
    print(f"blind packet: {packet}")
    print(f"private key: {key}")
    print("Give a new reviewer only the packet; never the key or source set.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
