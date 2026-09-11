"""Entity-level groundedness: deterministic, free, and auditable (ADR-003).

Every policy number, amount, date and name in the draft must be supported by the
enquiry. This is the half of "does the draft invent facts" that a set comparison
can settle, so it does not get a judge. The other half - fabricated SLAs,
promises and entitlements - is a judgement call and belongs to the judge metric.

Detection reuses the analyzer from `src/redaction.py`. One detection path for
one class of data: if a recognizer is added there, this metric sees it too, and
nothing can be covered in one place and missed in the other.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase
from presidio_analyzer import AnalyzerEngine

from src.redaction import resolve_overlaps

# Exported so coverage comes from a constant rather than from call sites.
CHECKED_ENTITIES: tuple[str, ...] = (
    "POLICY_NUMBER",
    "MONEY",
    "DATE_TIME",
    "PERSON",
    "HK_ID",
    "PHONE_NUMBER",
    "EMAIL_ADDRESS",
)

# Letter runs and digit runs separately, so "5:00pm" and "5:00 pm" tokenise
# alike. Real drafts respace times and the first version flagged that as a
# fabricated date.
_WORD = re.compile(r"[A-Za-z]+|\d+")

# A reply that opens "Dear Ms Cheung" to an enquiry signed "Cheung Ka Yan" is
# being polite, not inventing a person. Honorifics are dropped before the name
# is compared; the surname still has to be there.
HONORIFICS = frozenset({
    "mr", "mrs", "ms", "miss", "mx", "dr", "prof", "sir", "madam", "mdm",
})

# NER hands back "Dear Michelle" as one PERSON span. The salutation is not part
# of the name and is not in the enquiry, so the token-subset test failed and a
# correctly-addressed reply was reported as inventing a person.
SALUTATIONS = frozenset({"dear", "hi", "hello", "attn"})

# A concrete date can be checked against the enquiry by set membership. A vague
# one cannot: "annually", "recent day" and "shortly" assert no fact an extractor
# can verify, and flagging them made a faithful draft look unfaithful. ADR-003
# already draws this line - mechanically checkable failures are entity-level,
# and an invented *timeframe* is a commitment, which is the judge's half of the
# split. Measured on fifteen real drafts, three of six flags were this artifact.
_HAS_DIGIT = re.compile(r"\d")
_MONTH = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", re.IGNORECASE)


def is_checkable_date(text: str) -> bool:
    """Concrete enough that its absence from the enquiry means something."""
    return bool(_HAS_DIGIT.search(text) or _MONTH.search(text))


def date_core(text: str) -> set[str]:
    """The part of a date span whose absence is a fabrication.

    NER returns "7pm on a weekday" as one span. The enquiry said 7pm; the
    connective prose around it did not appear there, and comparing the whole
    span called a grounded time an invention. The checkable content of a date is
    its numbers and month names - inventing wording around a real date is a
    commitment question, which ADR-003 gives to the judge.
    """
    return {
        token if token.isdigit() else token.lower()[:3]
        for token in _WORD.findall(text)
        if token.isdigit() or _MONTH.match(token)
    }


def _normalise(text: str) -> str:
    """Comparable form: case-folded, comma-free, no trailing pence."""
    lowered = text.lower().replace(",", "").replace(" ", " ")
    lowered = re.sub(r"(\d)\.00\b", r"\1", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in _WORD.findall(text)}


def _comparable_tokens(text: str) -> set[str]:
    return _tokens(text) - HONORIFICS - SALUTATIONS


@dataclass(frozen=True)
class Ungrounded:
    entity_type: str
    text: str

    def __str__(self) -> str:
        return f"{self.entity_type}:{self.text!r}"


def extract(text: str, analyzer: AnalyzerEngine) -> list[tuple[str, str]]:
    """(entity_type, surface form) pairs, overlaps resolved by score."""
    results = analyzer.analyze(text=text, language="en",
                               entities=list(CHECKED_ENTITIES))
    return [
        (result.entity_type, text[result.start : result.end].strip())
        for result in resolve_overlaps(results)
    ]


def ungrounded_entities(enquiry: str, draft: str,
                        analyzer: AnalyzerEngine) -> list[Ungrounded]:
    """Entities in the draft that the enquiry does not support.

    Two ways to be supported, because a reply legitimately rephrases. The exact
    normalised string may appear in the enquiry, or every word of the entity may
    appear in it - which is what lets a draft opening "Dear Mr Tseung" match an
    enquiry signed "Marco Tseung" without being called a fabrication, while a
    policy number that appears nowhere still is one.
    """
    enquiry_normalised = _normalise(enquiry)
    enquiry_tokens = _tokens(enquiry)
    enquiry_date_core = date_core(enquiry)

    findings = []
    for entity_type, surface in extract(draft, analyzer):
        normalised = _normalise(surface)
        if not normalised:
            continue
        if entity_type == "DATE_TIME":
            if not is_checkable_date(surface):
                continue
            if date_core(surface) <= enquiry_date_core:
                continue
        if normalised in enquiry_normalised:
            continue
        if _comparable_tokens(surface) <= enquiry_tokens:
            continue
        findings.append(Ungrounded(entity_type, surface))
    return findings


class EntityGroundedness(BaseMetric):
    """Share of the draft's entities the enquiry supports.

    A rate rather than a per-record pass, because the bar in
    `docs/02-metrics.md` is 99% of entities: one fabricated policy number in
    forty drafts should move the number, not be rounded away by a record that
    happens to contain thirty grounded ones.
    """

    def __init__(self, analyzer: AnalyzerEngine, threshold: float = 0.99):
        self.analyzer = analyzer
        self.threshold = threshold

    @property
    def __name__(self) -> str:
        return "entity groundedness"

    def measure(self, test_case: LLMTestCase) -> float:
        meta = test_case.metadata or {}
        draft = meta.get("draft_reply")

        if draft is None:
            self.skipped = True
            self.score = 1.0
            self.success = True
            self.reason = "no draft to score"
            return self.score

        entities = extract(draft, self.analyzer)
        findings = ungrounded_entities(test_case.input, draft, self.analyzer)

        self.score = 1.0 if not entities else 1 - len(findings) / len(entities)
        self.success = self.score >= self.threshold
        self.reason = (
            f"{len(entities) - len(findings)}/{len(entities)} entities grounded"
            + (f"; ungrounded: {', '.join(str(f) for f in findings)}" if findings else "")
        )
        return self.score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return bool(getattr(self, "success", False))
