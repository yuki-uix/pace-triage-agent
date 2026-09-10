"""The quota check, and a proof that the declared quotas are jointly satisfiable."""

import json
import pathlib

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
        load_records(str(path), str(path))


def write_pair(tmp_path, records, separator="\n"):
    """Write the two halves the way the generator does."""
    enquiries = tmp_path / "enquiries.jsonl"
    golden = tmp_path / "golden.jsonl"
    enquiries.write_text(
        separator.join(r.enquiry().model_dump_json() for r in records) + "\n",
        encoding="utf-8")
    golden.write_text(
        separator.join(r.label().model_dump_json() for r in records) + "\n",
        encoding="utf-8")
    return str(enquiries), str(golden)


def test_load_records_skips_blank_lines(tmp_path):
    enquiries, golden = write_pair(tmp_path, valid_dataset()[:2], separator="\n\n")
    assert len(load_records(enquiries, golden)) == 2


def test_the_enquiries_file_carries_no_answers(tmp_path):
    """Structural, not a discipline: the pipeline cannot read what is not there."""
    enquiries, _ = write_pair(tmp_path, valid_dataset()[:3])
    for line in pathlib.Path(enquiries).read_text(encoding="utf-8").splitlines():
        assert sorted(json.loads(line)) == ["body", "id", "subject"]


def test_a_label_without_an_enquiry_raises(tmp_path):
    """Otherwise the record silently never gets scored."""
    enquiries, golden = write_pair(tmp_path, valid_dataset()[:3])
    pathlib.Path(enquiries).write_text(
        "\n".join(pathlib.Path(enquiries).read_text(encoding="utf-8").splitlines()[:2])
        + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unlabelled|orphaned"):
        load_records(enquiries, golden)


def test_an_enquiry_without_a_label_raises(tmp_path):
    enquiries, golden = write_pair(tmp_path, valid_dataset()[:3])
    pathlib.Path(golden).write_text(
        "\n".join(pathlib.Path(golden).read_text(encoding="utf-8").splitlines()[:2])
        + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unlabelled|orphaned"):
        load_records(enquiries, golden)


def test_cli_exits_nonzero_on_violations(tmp_path, capsys, monkeypatch):
    enquiries, golden = write_pair(tmp_path, valid_dataset()[:3])
    monkeypatch.setattr("src.quotas.GOLDEN", golden)

    assert main(["src.quotas", enquiries]) == 1
    assert "quota violation" in capsys.readouterr().err


def test_cli_exits_zero_on_a_valid_dataset(tmp_path, capsys, monkeypatch):
    enquiries, golden = write_pair(tmp_path, valid_dataset())
    monkeypatch.setattr("src.quotas.GOLDEN", golden)

    assert main(["src.quotas", enquiries]) == 0
    assert "all 15 quotas met" in capsys.readouterr().out


def test_the_cli_defaults_to_the_shipped_dataset():
    """The first free command a stranger runs must work with no arguments."""
    if not pathlib.Path("data/enquiries.jsonl").exists():
        pytest.skip("dataset not generated")
    assert main(["src.quotas"]) == 0


def test_an_unknown_flag_is_a_usage_error():
    """It used to crash with a traceback: --help was read as a filename."""
    with pytest.raises(SystemExit) as exit_info:
        main(["src.quotas", "--nonsense"])
    assert exit_info.value.code == 2


def test_records_round_trip_through_json():
    original = valid_dataset()[20]
    restored = EnquiryRecord.model_validate(json.loads(original.model_dump_json()))
    assert restored == original
