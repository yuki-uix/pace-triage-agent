import json

from evals.prepare_actionability_boundary_review import prepare


def test_boundary_packet_hides_scores_pairs_and_variant_ids(tmp_path):
    packet_path, key_path = prepare(tmp_path)
    packet = [json.loads(line) for line in packet_path.read_text().splitlines()]
    key = json.loads(key_path.read_text())

    assert len(packet) == 18
    assert len(key["items"]) == 18
    assert all(set(row) == {"blind_id", "enquiry", "draft_reply"}
               for row in packet)
    hidden = {"target_score", "expected_band", "variant_id", "pair_id"}
    assert all(not hidden.intersection(row) for row in packet)
    assert all(hidden.issubset(row) for row in key["items"])


def test_boundary_packet_is_deterministic(tmp_path):
    first_packet, first_key = prepare(tmp_path / "first")
    second_packet, second_key = prepare(tmp_path / "second")
    assert first_packet.read_bytes() == second_packet.read_bytes()
    assert first_key.read_bytes() == second_key.read_bytes()
