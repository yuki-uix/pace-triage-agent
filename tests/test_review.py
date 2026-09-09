"""The review CLI. IO is injected, so none of this needs a terminal."""

import json
import pathlib

import pytest

from src.review import (
    Decision,
    Item,
    load_queue,
    render,
    review,
    save_queue,
)

DRAFT = "Dear customer, thank you for your email."


def queue_file(tmp_path, count: int = 2, **overrides) -> str:
    path = tmp_path / "queue.jsonl"
    rows = []
    for index in range(count):
        rows.append({
            "record_id": f"ENQ-{index + 1:03d}",
            "case_type": "CLAIM", "priority": "NORMAL", "confidence": 0.8,
            "summary": "A claim is pending.", "draft_reply": DRAFT,
            "traces": [{"stage": "triage"}],
            "decision": None, "reviewer_text": None, **overrides,
        })
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return str(path)


class Session:
    """Scripted answers, captured output."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.output: list[str] = []

    def read(self, prompt: str) -> str:
        return self.answers.pop(0)

    def write(self, text: str) -> None:
        self.output.append(text)

    @property
    def text(self) -> str:
        return "".join(self.output)


def decisions(path: str) -> list[str | None]:
    return [item.decision for item in load_queue(path)]


def test_accepting_writes_the_decision(tmp_path):
    path = queue_file(tmp_path, 1)
    review(path, Session(["a"]).read, lambda t: None)
    assert decisions(path) == ["accept"]


def test_discarding_writes_the_decision(tmp_path):
    path = queue_file(tmp_path, 1)
    review(path, Session(["d"]).read, lambda t: None)
    assert decisions(path) == ["discard"]


def test_editing_keeps_the_reviewers_text(tmp_path):
    """The field that lets corrections come back as golden samples."""
    path = queue_file(tmp_path, 1)
    review(path, Session(["e"]).read, lambda t: None,
           editor=lambda text: "Dear Ms Chan, we have received your claim.")

    item = load_queue(path)[0]
    assert item.decision == "edit"
    assert item.raw["reviewer_text"] == "Dear Ms Chan, we have received your claim."
    assert item.draft_reply == DRAFT, "the original draft must survive the edit"


def test_accepting_records_no_reviewer_text(tmp_path):
    """Otherwise an accepted draft is indistinguishable from a corrected one."""
    path = queue_file(tmp_path, 1)
    review(path, Session(["a"]).read, lambda t: None)
    assert load_queue(path)[0].raw["reviewer_text"] is None


def test_fields_the_cli_does_not_understand_are_preserved(tmp_path):
    """The traces would be lost on the first review pass otherwise."""
    path = queue_file(tmp_path, 1)
    review(path, Session(["a"]).read, lambda t: None)
    assert load_queue(path)[0].raw["traces"] == [{"stage": "triage"}]


def test_each_decision_is_written_before_the_next_is_asked(tmp_path):
    """A reviewer who loses forty judgements to a crash does not come back."""
    path = queue_file(tmp_path, 3)
    seen: list[list[str | None]] = []

    def read(prompt: str) -> str:
        seen.append(decisions(path))
        return "a"

    review(path, read, lambda t: None)

    assert seen[1][0] == "accept", "the first decision was not on disk yet"
    assert seen[2][1] == "accept"


def test_skipping_leaves_the_item_undecided(tmp_path):
    path = queue_file(tmp_path, 2)
    session = Session(["s", "a"])
    outcome = review(path, session.read, session.write)

    assert decisions(path) == [None, "accept"]
    assert outcome.skipped == 1
    assert outcome.reviewed == 1


def test_quitting_stops_and_keeps_what_was_decided(tmp_path):
    path = queue_file(tmp_path, 3)
    session = Session(["a", "q"])
    outcome = review(path, session.read, session.write)

    assert decisions(path) == ["accept", None, None]
    assert outcome.quit_early is True
    assert "still pending" in session.text


def test_an_unrecognised_key_re_asks_rather_than_guessing(tmp_path):
    path = queue_file(tmp_path, 1)
    session = Session(["x", "", "a"])
    review(path, session.read, session.write)

    assert decisions(path) == ["accept"]
    assert "unrecognised" in session.text


def test_already_decided_items_are_not_offered_again(tmp_path):
    path = queue_file(tmp_path, 2, decision="accept")
    session = Session([])
    outcome = review(path, session.read, session.write)

    assert outcome.reviewed == 0
    assert "nothing pending" in session.text


def test_the_prompt_shows_what_the_reviewer_needs_to_decide(tmp_path):
    item = load_queue(queue_file(tmp_path, 1))[0]
    shown = render(item, 1, 1)

    assert "ENQ-001" in shown
    assert "CLAIM" in shown and "NORMAL" in shown
    assert "confidence 0.80" in shown
    assert DRAFT in shown


def test_a_save_leaves_no_partial_file(tmp_path):
    """Written through a temporary file: an interrupted save must not truncate
    a queue that already holds decisions."""
    path = queue_file(tmp_path, 2)
    items = load_queue(path)
    save_queue(path, [items[0].decided(Decision.ACCEPT), items[1]])

    assert len(load_queue(path)) == 2
    assert list(pathlib.Path(path).parent.glob("tmp*")) == []


def test_the_review_module_introduces_no_send_path():
    """Asserted for all of src/ in tests/test_pipeline.py; named here too
    because a review tool is where a send button would be added."""
    source = pathlib.Path("src/review.py").read_text(encoding="utf-8")
    for forbidden in ("smtplib", "sendmail", "requests.post", "httpx.post"):
        assert forbidden not in source


@pytest.mark.parametrize("value,shown", [
    (0.9993, "0.999"),
    (0.9965, "0.996"),
    (0.9999, "0.999"),
    (1.0, "1.000"),
    (0.2251, "0.225"),
    (0.0, "0.000"),
])
def test_confidence_is_truncated_never_rounded_up(value, shown):
    """0.9993 shown as "1.00" is a certainty the system never produced, and the
    error runs towards inviting less scrutiny - the opposite of what a derived
    confidence is for."""
    from src.review import display_confidence

    assert display_confidence(value) == shown


def test_a_confident_looking_draft_is_not_shown_as_certain(tmp_path):
    path = queue_file(tmp_path, 1, confidence=0.9993)
    shown = render(load_queue(path)[0], 1, 1)

    assert "confidence 0.999" in shown
    assert "1.00" not in shown
