"""The quota check, and a proof that the declared quotas are jointly satisfiable."""

import json

import pytest

from src.dataset import EnquiryRecord, Tag
from src.quotas import (
    MAX_RECORDS,
    MIN_RECORDS,
    QUOTAS,
    Quota,
    check_quotas,
    load_records,
    main,
)
from src.schema import CaseType, Priority

TYPES = list(CaseType)


def build_record(index: int, tags: tuple[str, ...] = ()) -> EnquiryRecord:
    expected_type = TYPES[index % len(TYPES)]

    if index < 8:
        priority = Priority.URGENT
    elif index < 16:
        priority = Priority.LOW
    else:
        priority = Priority.NORMAL

    payload = {
        "id": f"ENQ-{index:03d}",
        "subject": f"Enquiry {index}",
        "body": f"Body of enquiry {index}.",
        "expected_type": expected_type.value,
        "expected_priority": priority.value,
        "tags": list(tags),
    }

    if Tag.MIXED_TOPIC.value in tags:
        other = TYPES[(index + 1) % len(TYPES)]
        payload["acceptable_types"] = [expected_type.value, other.value]
        payload["label_note"] = "the work item outranks the tone"
    if Tag.REFUSAL.value in tags:
        payload["must_not_assert"] = ["that the claim will be approved"]

    return EnquiryRecord.model_validate(payload)


def valid_dataset() -> list[EnquiryRecord]:
    """40 records that meet every declared quota simultaneously."""
    tags_by_index: dict[int, tuple[str, ...]] = {}
    for i in range(0, 6):
        tags_by_index[i] = ("NOISY",)
    for i in range(20, 25):
        tags_by_index[i] = ("MIXED_TOPIC",)
    for i in range(25, 29):
        tags_by_index[i] = ("ANGRY",)
    for i in range(29, 33):
        tags_by_index[i] = ("MISSING_INFO",)
    for i in range(33, 35):
        tags_by_index[i] = ("REFUSAL",)
    for i in range(35, 37):
        tags_by_index[i] = ("INJECTION",)

    return [build_record(i, tags_by_index.get(i, ())) for i in range(40)]


def test_the_declared_quotas_are_jointly_satisfiable():
    """If this fails, the spec is self-contradictory and no generator can pass."""
    assert check_quotas(valid_dataset()) == []


@pytest.mark.parametrize("quota", QUOTAS, ids=lambda q: q.name)
def test_every_declared_quota_is_actually_enforced(quota):
    """Derived from QUOTAS, so a new quota is covered without editing this test."""
    records = [r for r in valid_dataset() if not quota.predicate(r)]
    violations = check_quotas(records)
    assert any(violation.startswith(quota.name) for violation in violations)


def test_quota_needs_exactly_one_bound():
    with pytest.raises(ValueError):
        Quota("both", lambda r: True, minimum=1, exact=1)
    with pytest.raises(ValueError):
        Quota("neither", lambda r: True)


def test_too_few_records_is_a_violation():
    violations = check_quotas(valid_dataset()[:10])
    assert any("record count" in violation for violation in violations)


def test_too_many_records_is_a_violation():
    records = valid_dataset()
    padded = records + [build_record(i) for i in range(40, 40 + MAX_RECORDS)]
    assert any("record count" in violation for violation in check_quotas(padded))


def test_record_count_bounds_match_the_data_spec():
    assert (MIN_RECORDS, MAX_RECORDS) == (40, 50)


def test_duplicate_ids_are_caught():
    records = valid_dataset()
    records[5] = records[4]
    assert any("duplicate ids" in violation for violation in check_quotas(records))


def test_load_records_rejects_a_malformed_line(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"id": "ENQ-001"}\n', encoding="utf-8")
    with pytest.raises(Exception):
        load_records(str(path))


def test_load_records_skips_blank_lines(tmp_path):
    path = tmp_path / "ok.jsonl"
    lines = [r.model_dump_json() for r in valid_dataset()[:2]]
    path.write_text("\n\n".join(lines) + "\n", encoding="utf-8")
    assert len(load_records(str(path))) == 2


def test_cli_exits_nonzero_on_violations(tmp_path, capsys):
    path = tmp_path / "short.jsonl"
    lines = [r.model_dump_json() for r in valid_dataset()[:3]]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assert main(["src.quotas", str(path)]) == 1
    assert "quota violation" in capsys.readouterr().err


def test_cli_exits_zero_on_a_valid_dataset(tmp_path, capsys):
    path = tmp_path / "good.jsonl"
    lines = [r.model_dump_json() for r in valid_dataset()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assert main(["src.quotas", str(path)]) == 0
    assert "all 15 quotas met" in capsys.readouterr().out


def test_cli_usage_error():
    assert main(["src.quotas"]) == 2


def test_records_round_trip_through_json():
    original = valid_dataset()[20]
    restored = EnquiryRecord.model_validate(json.loads(original.model_dump_json()))
    assert restored == original
