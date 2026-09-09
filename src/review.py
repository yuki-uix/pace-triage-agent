"""The human-in-the-loop review CLI.

`docs/04-scope.md` budgets twenty minutes for this and it should stay that
size: a pending queue, accept / edit / discard, and a decision written back.
Polish is the first thing on the degradation list.

Two things it does that are worth more than polish:

**It keeps the reviewer's edited text, not just the decision.** That single
extra field is what makes "reviewer corrections flow back as new golden
samples" possible, which is the most natural first item in the next-two-weeks
section. A decision alone tells you a draft was wrong; the edit tells you what
right looked like.

**It writes after every decision.** A reviewer who loses forty judgements to a
crash on the forty-first does not come back, and this project has already lost
paid-for work twice by persisting only at the end.

**Nothing sends.** This module has no transport and introduces none; the queue
is a file, and a decision is a field in it. `tests/test_pipeline.py` asserts
that for the whole of `src/` by scanning it.
"""

from __future__ import annotations

import json
import math
import os
import pathlib
import subprocess
import tempfile
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Iterable


class Decision(str, Enum):
    ACCEPT = "accept"
    EDIT = "edit"
    DISCARD = "discard"


KEYS: dict[str, Decision] = {
    "a": Decision.ACCEPT,
    "e": Decision.EDIT,
    "d": Decision.DISCARD,
}

SKIP, QUIT = "s", "q"

PROMPT = "[a]ccept  [e]dit  [d]iscard  [s]kip  [q]uit > "


@dataclass
class Item:
    """One queue entry. Unknown fields are preserved, not dropped.

    The queue is written by the pipeline and read back here; silently discarding
    a field this module does not understand would lose the traces on the first
    review pass.
    """

    raw: dict

    @property
    def record_id(self) -> str:
        return self.raw.get("record_id", "?")

    @property
    def decision(self) -> str | None:
        return self.raw.get("decision")

    @property
    def draft_reply(self) -> str:
        return self.raw.get("draft_reply", "")

    def decided(self, decision: Decision, reviewer_text: str | None = None) -> "Item":
        updated = dict(self.raw)
        updated["decision"] = decision.value
        # Kept only for an edit: recording the unchanged draft as "reviewer text"
        # would make an accepted draft indistinguishable from a corrected one.
        updated["reviewer_text"] = reviewer_text if decision is Decision.EDIT else None
        return Item(updated)


def load_queue(path: str) -> list[Item]:
    return [Item(json.loads(line))
            for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()]


def save_queue(path: str, items: Iterable[Item]) -> None:
    """Whole-file rewrite through a temporary file, so an interrupted save
    cannot truncate a queue that holds decisions already made."""
    target = pathlib.Path(path)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False,
                                     dir=target.parent) as handle:
        for item in items:
            handle.write(json.dumps(item.raw, ensure_ascii=False) + "\n")
        temporary = handle.name
    os.replace(temporary, target)


def display_confidence(value: float) -> str:
    """Truncated, never rounded up.

    Displaying 0.9993 as "1.00" shows the reviewer a certainty the system never
    produced, and errs in the direction that invites less scrutiny. The whole
    purpose of a derived confidence (ADR-002) is to route uncertain cases to a
    closer look, so its display must not round towards confident.
    """
    return f"{math.floor(value * 1000) / 1000:.3f}"


def render(item: Item, position: int, total: int) -> str:
    raw = item.raw
    confidence = raw.get("confidence")
    header = (f"[{position}/{total}] {item.record_id}  "
              f"{raw.get('case_type', '?')} / {raw.get('priority', '?')}")
    if isinstance(confidence, (int, float)):
        header += f"  confidence {display_confidence(confidence)}"
    return "\n".join([
        "=" * 78,
        header,
        "",
        "SUMMARY",
        raw.get("summary", ""),
        "",
        "DRAFT REPLY",
        item.draft_reply,
        "",
    ])


def edit_text(text: str, editor: str | None = None) -> str:
    """Open the draft in $EDITOR. Falls back to returning it unchanged."""
    editor = editor or os.environ.get("EDITOR")
    if not editor:
        return text
    with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8",
                                     delete=False) as handle:
        handle.write(text)
        path = handle.name
    subprocess.run([*editor.split(), path], check=False)
    edited = pathlib.Path(path).read_text(encoding="utf-8")
    os.unlink(path)
    return edited


@dataclass
class Review:
    reviewed: int = 0
    skipped: int = 0
    quit_early: bool = False


def review(path: str, read: Callable[[str], str], write: Callable[[str], None],
           editor: Callable[[str], str] = edit_text) -> Review:
    """Walk the undecided items. IO is injected so this is testable without a TTY."""
    items = load_queue(path)
    pending = [index for index, item in enumerate(items) if item.decision is None]
    outcome = Review()

    if not pending:
        write("nothing pending: every item already carries a decision.\n")
        return outcome

    for position, index in enumerate(pending, start=1):
        write(render(items[index], position, len(pending)))

        while True:
            answer = (read(PROMPT) or "").strip().lower()
            if answer == QUIT:
                outcome.quit_early = True
                write(f"\nstopped. {outcome.reviewed} decided, "
                      f"{len(pending) - position + 1} still pending.\n")
                return outcome
            if answer == SKIP:
                outcome.skipped += 1
                break
            if answer in KEYS:
                decision = KEYS[answer]
                text = editor(items[index].draft_reply) if decision is Decision.EDIT \
                    else None
                items[index] = items[index].decided(decision, text)
                save_queue(path, items)  # after every decision, not at the end
                outcome.reviewed += 1
                write(f"  -> {decision.value}\n")
                break
            write("  unrecognised. a / e / d / s / q\n")

    write(f"\ndone. {outcome.reviewed} decided, {outcome.skipped} skipped.\n")
    return outcome


def main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Review the pending queue.")
    parser.add_argument("--queue", default="results/pending_queue.jsonl")
    args = parser.parse_args(argv[1:])

    if not pathlib.Path(args.queue).exists():
        print(f"no queue at {args.queue}; run the pipeline first")
        return 2

    review(args.queue, read=input, write=lambda text: print(text, end=""))
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv))
