"""Entity detection and pseudonymisation.

Two callers, one analyzer. The dataset builder uses it to replace whatever
identifiers the generator invented with deterministic fakes; the trace boundary
of ADR-004 will use the same detection with a different operator.

**What the "no real PII" claim actually rests on.** Not this module. The dataset
contains no real customer data because no real customer data was ever an input —
every enquiry is written from a label specification, not from a real inbox. This
pass is defence in depth: it removes the residual risk that a generator emits a
memorised real-looking identifier, and it makes the identifiers consistent and
reproducible. The write-up should state it that way round.

**Known limitation, to be disclosed rather than discovered.** The analyzer runs
`en_core_web_lg`, so a personal name written in Chinese characters is not
detected. Records with Cantonese bodies are checked by hand for this.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer

from src.dataset import EnquiryRecord

# Entities worth replacing. Exported so a caller cannot quietly cover a subset —
# adding an entity here is what extends coverage, not editing a call site.
#
# PERSON is deliberately absent, and the reason is measured rather than assumed.
# Substituting names end to end on the pilot records made the data worse:
#
#   - Spans ran past the name into the next line, so 'Chan Tai Man\nFlat 8,'
#     was replaced wholesale and the address lost its flat number.
#   - Hong Kong districts were classified as people. 'Kwun Tong', 'Mong Kok',
#     'Sheung Wan', 'Tai Po' and 'N.T.' all became personal names, because
#     romanised Cantonese place names and personal names are the same shape to
#     an English NER model. Addresses turned to nonsense.
#   - Without coreference the same customer got three identities in one email:
#     'Chan Ka Yan', 'Chan Ka Yan\nPolicy' and 'Ka Yan' mapped to three
#     different people.
#
# The residual risk that motivates this pass — a generator emitting a memorised
# real identifier — lives in structured identifiers, not in common names, and
# those are regex-bounded and safe to rewrite. Detected names are reported for
# human review instead of silently rewritten (`REVIEW_ENTITIES`).
PSEUDONYMISED_ENTITIES: tuple[str, ...] = (
    "PHONE_NUMBER",
    "EMAIL_ADDRESS",
    "POLICY_NUMBER",
    "HK_ID",
)

# Detected, never rewritten. Surfaced so a human decides, rather than a model
# quietly deciding by doing nothing.
REVIEW_ENTITIES: tuple[str, ...] = ("PERSON", "LOCATION")

# Hong Kong flavour. Faker has no en_HK locale, and substituting en_GB names
# would turn a Hong Kong insurer's queue into a British one — the dataset would
# stop testing what it exists to test.
SURNAMES = (
    "Chan", "Wong", "Lee", "Cheung", "Lam", "Ng", "Ho", "Tsang", "Lau", "Yeung",
    "Kwok", "Leung", "Mak", "Tam", "Fung", "Poon", "Yip", "Chow", "Lo", "Siu",
)
GIVEN_NAMES = (
    "Ka Yan", "Tai Man", "Siu Fan", "Wing Sze", "Chi Ho", "Mei Ling", "Ka Ho",
    "Yuk Lan", "Man Kit", "Pui Shan", "Ho Yin", "Wai Man", "Sze Wing", "Kwok Wai",
)

POLICY_NUMBER = PatternRecognizer(
    supported_entity="POLICY_NUMBER",
    patterns=[
        # The suffix may be alphanumeric: HKL-90595202-ZX was being truncated to
        # HKL-90595202, which is a different identifier.
        Pattern("policy-alpha-dash-digits",
                r"\b[A-Z]{1,4}-\d{2,}(?:-[A-Z0-9]+)*\b", 0.8),
        Pattern("policy-alpha-digits", r"\b[A-Z]{1,3}\d{6,}\b", 0.7),
    ],
)
HK_ID = PatternRecognizer(
    supported_entity="HK_ID",
    patterns=[Pattern("hkid", r"\b[A-Z]{1,2}\d{6}(?:\([0-9A]\))?", 0.9)],
)
# Presidio's built-in phone recognizer works through `phonenumbers`, which wants
# a country context. A bare Hong Kong mobile — eight digits, no dialling code —
# is read as a date instead. Measured, not assumed: "9123 4567" came back as
# DATE_TIME with score 0.85.
# Presidio ships no Hong Kong currency recognizer, so amounts were invisible.
# A fabricated amount is among the most damaging things a draft can contain, so
# this is not optional for the groundedness metric.
HK_MONEY = PatternRecognizer(
    supported_entity="MONEY",
    patterns=[
        Pattern("hkd-symbol", r"\bHK\$\s?[\d,]+(?:\.\d{2})?", 0.9),
        Pattern("hkd-code", r"\bHKD\s?[\d,]+(?:\.\d{2})?", 0.9),
        Pattern("bare-dollar", r"(?<![A-Z])\$\s?[\d,]{3,}(?:\.\d{2})?", 0.6),
    ],
)
HK_PHONE = PatternRecognizer(
    supported_entity="PHONE_NUMBER",
    patterns=[Pattern("hk-8-digit", r"\b[2-9]\d{3}\s?\d{4}\b", 0.7)],
)


def build_analyzer() -> AnalyzerEngine:
    analyzer = AnalyzerEngine()
    analyzer.registry.add_recognizer(POLICY_NUMBER)
    analyzer.registry.add_recognizer(HK_ID)
    analyzer.registry.add_recognizer(HK_PHONE)
    analyzer.registry.add_recognizer(HK_MONEY)
    return analyzer


def resolve_overlaps(results):
    """Keep the highest-scoring detection per span.

    An HKID matches the policy-number pattern too. Without this, one span
    produces two mapping entries and which fake wins depends on string length.
    """
    kept = []
    for result in sorted(results, key=lambda r: (-r.score, r.start)):
        if any(result.start < k.end and k.start < result.end for k in kept):
            continue
        kept.append(result)
    return kept


def _seeded(value: str, salt: str, modulus: int) -> int:
    digest = hashlib.sha256(f"{salt}:{value}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % modulus


def _fake(entity: str, original: str, salt: str) -> str:
    """Deterministic replacement. Same input always gives the same output, so a
    regenerated dataset is byte-identical and the frozen golden set stays frozen.
    """
    if entity == "PERSON":
        surname = SURNAMES[_seeded(original, salt + "s", len(SURNAMES))]
        given = GIVEN_NAMES[_seeded(original, salt + "g", len(GIVEN_NAMES))]
        return f"{surname} {given}"
    if entity == "PHONE_NUMBER":
        return f"9{_seeded(original, salt + 'p', 10_000_000):07d}"
    if entity == "EMAIL_ADDRESS":
        return f"customer{_seeded(original, salt + 'e', 9000) + 1000}@example.com"
    if entity == "HK_ID":
        return f"X{_seeded(original, salt + 'h', 1_000_000):06d}(A)"
    if entity == "POLICY_NUMBER":
        prefix = re.match(r"^[A-Z]{1,4}", original)
        head = prefix.group(0) if prefix else "HK"
        return f"{head}-{_seeded(original, salt + 'n', 90_000_000) + 10_000_000}"
    return original


@dataclass
class Pseudonymisation:
    record: EnquiryRecord
    mapping: dict[str, str]
    for_review: tuple[str, ...] = ()

    @property
    def replaced(self) -> int:
        return len(self.mapping)


def _fields(record: EnquiryRecord) -> list[str]:
    texts = [record.subject, record.body, *record.must_include, *record.must_not_assert]
    if record.label_note:
        texts.append(record.label_note)
    return texts


def pseudonymise(record: EnquiryRecord, analyzer: AnalyzerEngine) -> Pseudonymisation:
    """Replace detected identifiers consistently across every field of a record.

    Consistency across fields is the point. `must_include` and `must_not_assert`
    quote policy numbers and addresses out of the body; replacing only the body
    would leave the reference notes citing an identifier that no longer appears
    in the enquiry, and the entity-groundedness metric compares exactly those two
    sets. A partial substitution would silently corrupt that metric.
    """
    mapping: dict[str, str] = {}
    review: set[str] = set()

    for text in _fields(record):
        detections = analyzer.analyze(
            text=text, language="en", entities=list(PSEUDONYMISED_ENTITIES)
        )
        for result in resolve_overlaps(detections):
            original = text[result.start : result.end].strip()
            if len(original) < 3 or original in mapping:
                continue
            mapping[original] = _fake(result.entity_type, original, record.id)

        for result in analyzer.analyze(
            text=text, language="en", entities=list(REVIEW_ENTITIES)
        ):
            candidate = text[result.start : result.end].strip()
            if len(candidate) >= 3:
                review.add(candidate)

    def apply(text: str) -> str:
        for original in sorted(mapping, key=len, reverse=True):
            text = text.replace(original, mapping[original])
        return text

    return Pseudonymisation(
        record=record.model_copy(
            update={
                "subject": apply(record.subject),
                "body": apply(record.body),
                "must_include": tuple(apply(t) for t in record.must_include),
                "must_not_assert": tuple(apply(t) for t in record.must_not_assert),
                "label_note": apply(record.label_note) if record.label_note else None,
            }
        ),
        mapping=mapping,
        for_review=tuple(sorted(review)),
    )
