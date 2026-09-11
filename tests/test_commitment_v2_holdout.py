import json

from evals.prepare_commitment_v2_holdout_review import prepare
from src.commitment_v2_holdout import load_holdout, validate_holdout


def test_holdout_is_disjoint_balanced_and_evidence_frozen():
    rows = load_holdout()
    assert len(rows) == 18
    assert validate_holdout(rows) == []
    assert {row.record_id for row in rows}.isdisjoint({
        "ENQ-009", "ENQ-016", "ENQ-023", "ENQ-028", "ENQ-035", "ENQ-040"
    })


def test_holdout_packet_hides_targets_and_is_deterministic(tmp_path):
    first_packet, first_key = prepare(tmp_path / "first")
    second_packet, second_key = prepare(tmp_path / "second")
    assert first_packet.read_bytes() == second_packet.read_bytes()
    assert first_key.read_bytes() == second_key.read_bytes()
    packet = [json.loads(line) for line in first_packet.read_text().splitlines()]
    assert len(packet) == 18
    assert all("target_score" not in row and "expected_band" not in row
               and "variant_id" not in row for row in packet)
