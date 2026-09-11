import json

from evals.prepare_actionability_blind_review import prepare


def test_prepare_strips_expected_labels_and_obscures_variant_ids(tmp_path):
    packet_path, key_path = prepare(tmp_path)
    packet = [json.loads(line) for line in packet_path.read_text().splitlines()]
    key = json.loads(key_path.read_text())

    assert len(packet) == 24
    assert len(key["items"]) == 24
    assert [row["blind_id"] for row in packet] == [
        f"AR-{index:02d}" for index in range(1, 25)
    ]
    assert all(set(row) == {"blind_id", "enquiry", "draft_reply"}
               for row in packet)
    assert all("expected_band" not in row and "variant_id" not in row
               for row in packet)
    assert all("expected_band" in row and "variant_id" in row
               for row in key["items"])


def test_prepare_is_deterministic(tmp_path):
    first_packet, first_key = prepare(tmp_path / "first")
    second_packet, second_key = prepare(tmp_path / "second")
    assert first_packet.read_bytes() == second_packet.read_bytes()
    assert first_key.read_bytes() == second_key.read_bytes()
