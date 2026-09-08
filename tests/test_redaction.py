"""Entity detection and pseudonymisation.

The behaviour these tests pin down was arrived at by running the pass on real
generated records and finding it made them worse. They exist so the same
mistake cannot come back quietly.
"""

import pytest

from src.dataset import EnquiryRecord
from src.redaction import (
    PSEUDONYMISED_ENTITIES,
    REVIEW_ENTITIES,
    build_analyzer,
    pseudonymise,
    resolve_overlaps,
)


@pytest.fixture(scope="module")
def analyzer():
    return build_analyzer()


def record(**overrides) -> EnquiryRecord:
    payload = {
        "id": "ENQ-001",
        "subject": "Address change for policy TL-88990011",
        "body": (
            "Dear team, I am Chan Tai Man in Kwun Tong. Policy TL-88990011. "
            "Please call me on 9123 4567 or email tai.man@example.com."
        ),
        "expected_type": "ADDRESS_CHANGE",
        "expected_priority": "NORMAL",
        "must_include": ("Confirm the new address on policy TL-88990011",),
    }
    return EnquiryRecord.model_validate({**payload, **overrides})


def test_policy_number_is_replaced(analyzer):
    result = pseudonymise(record(), analyzer)
    assert "TL-88990011" not in result.record.body
    assert "TL-88990011" in result.mapping


def test_hong_kong_phone_number_is_detected(analyzer):
    """Presidio's built-in recognizer reads a bare 8-digit HK number as a date."""
    result = pseudonymise(record(), analyzer)
    assert "9123 4567" in result.mapping


def test_email_is_replaced(analyzer):
    result = pseudonymise(record(), analyzer)
    assert "tai.man@example.com" not in result.record.body


def test_the_same_identifier_is_replaced_identically_across_fields(analyzer):
    """must_include quotes the body; entity groundedness compares those sets."""
    result = pseudonymise(record(), analyzer)
    replacement = result.mapping["TL-88990011"]
    assert replacement in result.record.body
    assert replacement in result.record.subject
    assert replacement in result.record.must_include[0]


def test_no_original_identifier_survives_anywhere(analyzer):
    result = pseudonymise(record(), analyzer)
    blob = result.record.model_dump_json()
    assert [original for original in result.mapping if original in blob] == []


def test_substitution_is_deterministic(analyzer):
    first = pseudonymise(record(), analyzer)
    second = pseudonymise(record(), analyzer)
    assert first.record == second.record


def test_different_records_get_different_fakes(analyzer):
    """The salt is the record id, so one leak does not unmask the whole set."""
    a = pseudonymise(record(), analyzer)
    b = pseudonymise(record(id="ENQ-002"), analyzer)
    assert a.mapping["TL-88990011"] != b.mapping["TL-88990011"]


def test_person_names_are_flagged_but_not_rewritten(analyzer):
    """Rewriting names corrupted addresses and split one customer into three."""
    result = pseudonymise(record(), analyzer)
    assert "Chan Tai Man" in result.record.body
    assert any("Chan Tai Man" in candidate for candidate in result.for_review)


def test_person_is_not_in_the_substitution_set():
    assert "PERSON" not in PSEUDONYMISED_ENTITIES
    assert "PERSON" in REVIEW_ENTITIES


def test_hong_kong_district_is_not_rewritten_into_a_person(analyzer):
    result = pseudonymise(record(), analyzer)
    assert "Kwun Tong" in result.record.body


def test_overlapping_detections_keep_the_highest_score(analyzer):
    text = "HKID A123456(7) on file"
    kept = resolve_overlaps(
        analyzer.analyze(
            text=text, language="en", entities=list(PSEUDONYMISED_ENTITIES)
        )
    )
    spans = [(r.start, r.end) for r in kept]
    assert len(spans) == len({s for s in spans})
    for i, first in enumerate(kept):
        for second in kept[i + 1 :]:
            assert not (first.start < second.end and second.start < first.end)


def test_a_record_with_no_identifiers_is_unchanged(analyzer):
    plain = record(
        subject="General question",
        body="How do I read my annual statement?",
        must_include=(),
    )
    result = pseudonymise(plain, analyzer)
    assert result.record == plain
    assert result.mapping == {}
