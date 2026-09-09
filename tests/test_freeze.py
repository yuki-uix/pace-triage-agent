"""The freeze rule, as a gate rather than a paragraph.

`CLAUDE.md`: regenerating the golden set after seeing results is the one action
that invalidates the whole submission. Defending that with a sentence in the
README defends it not at all — the standing rule in this repository is that
coverage is written as a test, not as a checklist.

So the frozen content is hashed and the hash is asserted. Changing the golden
set fails the suite until someone updates `data/provenance.json`, which is
exactly the explicit, deliberate commit the rule asks for. The test does not
prevent a change; it prevents a *silent* one.
"""

import hashlib
import json
import pathlib

import pytest

PROVENANCE = pathlib.Path("data/provenance.json")


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def frozen() -> dict:
    if not PROVENANCE.exists():
        pytest.skip("dataset not generated")
    return json.loads(PROVENANCE.read_text(encoding="utf-8"))["frozen"]


@pytest.mark.parametrize("name,key", [
    ("data/golden.jsonl", "golden_sha256"),
    ("data/enquiries.jsonl", "enquiries_sha256"),
])
def test_the_frozen_files_match_their_recorded_hashes(frozen, name, key):
    path = pathlib.Path(name)
    if not path.exists():
        pytest.skip("dataset not generated")

    assert digest(path) == frozen[key], (
        f"{name} has changed since the freeze.\n"
        "If this is deliberate: say so in the commit message, update the hash in "
        "data/provenance.json, add a row to the change log in "
        "data/labeling_guide.md, and re-tag.\n"
        "If it is not deliberate, this is the failure the freeze exists to catch."
    )


def test_the_freeze_records_which_tag_it_belongs_to(frozen):
    assert frozen["tag"] == "golden-v1"


def test_every_enquiry_has_exactly_one_label():
    """A half-drifted benchmark fails silently: the record simply never scores."""
    if not pathlib.Path("data/golden.jsonl").exists():
        pytest.skip("dataset not generated")

    from src.quotas import load_enquiries, load_golden

    assert sorted(e.id for e in load_enquiries()) == sorted(
        label.id for label in load_golden()
    )
