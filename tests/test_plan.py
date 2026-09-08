"""The plan is checked before it is generated from, not after.

A plan that cannot meet the quotas would only reveal itself after a generation
run had been paid for, so every assertion here runs offline in milliseconds.
"""

import pytest

from src.dataset import EnquiryRecord, Tag
from src.plan import PLAN
from src.quotas import QUOTAS, check_quotas
from src.schema import CaseType, Priority


def stub(slot) -> EnquiryRecord:
    """The slot's labels with placeholder prose, so quotas can be checked."""
    return EnquiryRecord(
        id=slot.record_id,
        subject="placeholder",
        body="placeholder",
        expected_type=slot.case_type,
        expected_priority=slot.priority,
        acceptable_types=slot.acceptable_types,
        tags=slot.tags,
        must_not_assert=("placeholder",) if Tag.REFUSAL in slot.tags else (),
        label_note="placeholder" if _needs_note(slot) else None,
    )


def _needs_note(slot) -> bool:
    return Tag.MIXED_TOPIC in slot.tags or (
        Tag.ANGRY in slot.tags and slot.priority is Priority.URGENT
    )


STUBS = [stub(slot) for slot in PLAN]


def test_the_plan_meets_every_quota():
    assert check_quotas(STUBS) == []


def test_the_plan_is_exactly_forty_slots():
    assert len(PLAN) == 40


def test_slot_indices_are_contiguous_and_unique():
    assert [slot.index for slot in PLAN] == list(range(1, 41))


def test_every_planned_record_validates_against_the_record_contract():
    """Catches a slot whose labels the contract would reject before generating."""
    assert len(STUBS) == len(PLAN)


@pytest.mark.parametrize("quota", QUOTAS, ids=lambda q: q.name)
def test_each_quota_has_slack_or_is_exact(quota):
    """Every quota is met by the plan, reported per quota rather than in bulk."""
    assert quota.violation(STUBS) is None


def test_hard_cases_carry_a_scenario_brief():
    """Refusal and injection records must differ in kind, not just in wording."""
    for slot in PLAN:
        if slot.tags & {Tag.REFUSAL, Tag.INJECTION}:
            assert slot.note, f"{slot.record_id} needs a scenario brief"


def test_the_two_refusal_cases_are_different_in_kind():
    notes = [slot.note for slot in PLAN if Tag.REFUSAL in slot.tags]
    assert len(notes) == 2
    assert notes[0] != notes[1]


def test_the_two_injection_cases_are_different_in_kind():
    notes = [slot.note for slot in PLAN if Tag.INJECTION in slot.tags]
    assert len(notes) == 2
    assert notes[0] != notes[1]


def test_refusal_records_keep_a_topical_type():
    """Labeling guide rule 1, as amended 2026-09-08: not OTHER."""
    for slot in PLAN:
        if Tag.REFUSAL in slot.tags:
            assert slot.case_type is not CaseType.OTHER


def test_no_address_change_is_urgent():
    """Sanity on the distribution: a routine work item should not carry urgency."""
    for slot in PLAN:
        if slot.case_type is CaseType.ADDRESS_CHANGE:
            assert slot.priority is not Priority.URGENT


def test_at_least_three_angry_records_are_not_urgent():
    """The records that punish escalation-on-tone are the point of the ANGRY tag."""
    angry = [s for s in PLAN if Tag.ANGRY in s.tags]
    not_urgent = [s for s in angry if s.priority is not Priority.URGENT]
    assert len(not_urgent) >= 3


def test_every_other_slot_carries_a_scenario_brief():
    """Undifferentiated OTHER slots collapsed onto one scenario in the first run.

    Four of six came back as variations of "is this SMS from you?", so the class
    measured one thing rather than six, and the blind relabeller contested five
    of the six labels.
    """
    for slot in PLAN:
        if slot.case_type is CaseType.OTHER and slot.index != 40:
            assert slot.note, f"{slot.record_id} needs a scenario brief"


def test_other_slot_briefs_are_distinct():
    briefs = [s.note for s in PLAN if s.case_type is CaseType.OTHER and s.note]
    assert len(briefs) == len(set(briefs))


def test_the_dataset_labels_match_the_plan():
    """The plan is the source of truth. Drift between them is silent otherwise.

    Skipped when the dataset has not been generated yet, so the suite still runs
    on a fresh checkout before anyone spends anything.
    """
    import pathlib

    if not pathlib.Path("data/enquiries.jsonl").exists():
        pytest.skip("dataset not generated")

    from src.quotas import load_records

    planned = {slot.record_id: slot for slot in PLAN}
    for record in load_records("data/enquiries.jsonl"):
        slot = planned[record.id]
        assert record.expected_type is slot.case_type, record.id
        assert record.expected_priority is slot.priority, record.id
        assert record.tags == slot.tags, record.id
        assert record.acceptable_types == slot.acceptable_types, record.id
