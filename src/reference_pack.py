"""Load a small, versioned and source-backed context for the quality judge."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


PACK_ROOT = Path(__file__).resolve().parents[1] / "knowledge"
TRUSTED_HOSTS = frozenset({"www.ia.org.hk", "www.pcpd.org.hk", "www.icb.org.hk"})

TOPIC_TERMS: dict[str, tuple[str, ...]] = {
    "participating_policy": (
        "dividend", "bonus", "cash value", "projected value", "illustration",
        "红利", "紅利",
    ),
    "medical_claim": (
        "hospital", "surgery", "medical claim", "doctor", "receipt",
        "住院", "手术", "手術", "索偿", "索償",
    ),
    "complaint": (
        "complaint", "complain", "mis-selling", "misled", "投诉", "投訴",
    ),
    "direct_marketing": (
        "marketing", "telemarketing", "promotional", "sales call", "推广", "推廣",
    ),
    "data_access": (
        "data access", "personal data", "privacy ordinance", "个人资料", "個人資料",
    ),
    "premium_billing": (
        "premium debit", "premium deduction", "autopay", "double charge",
        "charged amount", "billing", "levy", "自动转账", "自動轉賬", "重复扣款",
    ),
}

EVIDENCE_LIMITS = (
    "Evidence boundary: no insurer-specific product wording, policy schedule, "
    "service-channel SOP, document checklist, SLA, billing record or CRM/action "
    "state is present in this reference pack. Definite claims about those facts "
    "must be marked unsupported unless the evaluation case supplies them."
)


@dataclass(frozen=True)
class Source:
    id: str
    publisher: str
    authority_type: str
    title: str
    url: str
    topics: tuple[str, ...]
    verified_on: str
    scope: str


@dataclass(frozen=True)
class ReferenceClaim:
    id: str
    source_id: str
    topics: tuple[str, ...]
    locator: str
    claim: str


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_sources(root: Path = PACK_ROOT) -> dict[str, Source]:
    sources: dict[str, Source] = {}
    for raw in _load_json(root / "source_manifest.json"):
        host = urlparse(raw["url"]).hostname
        if host not in TRUSTED_HOSTS:
            raise ValueError(f"untrusted reference host for {raw['id']}: {host}")
        raw["topics"] = tuple(raw["topics"])
        source = Source(**raw)
        if date.fromisoformat(source.verified_on) > date.today():
            raise ValueError(f"source {source.id} has a future review date")
        if source.id in sources:
            raise ValueError(f"duplicate source id: {source.id}")
        sources[source.id] = source
    return sources


def load_claims(root: Path = PACK_ROOT) -> list[ReferenceClaim]:
    claims, ids = [], set()
    for line in (root / "reference_claims.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            raw = json.loads(line)
            raw["topics"] = tuple(raw["topics"])
            claim = ReferenceClaim(**raw)
            if claim.id in ids:
                raise ValueError(f"duplicate claim id: {claim.id}")
            if not claim.claim.strip() or not claim.locator.strip():
                raise ValueError(f"claim {claim.id} is missing text or a locator")
            ids.add(claim.id)
            claims.append(claim)
    return claims


def topics_for(text: str) -> frozenset[str]:
    lowered = text.lower()
    topics = {
        topic for topic, terms in TOPIC_TERMS.items()
        if any(term in lowered for term in terms)
    }
    if any(phrase in lowered for phrase in (
        "not a complaint", "isn't a complaint", "is not a complaint",
    )):
        topics.discard("complaint")
    return frozenset(topics)


def reference_context(text: str, root: Path = PACK_ROOT) -> list[str]:
    """Return relevant atomic claims plus an explicit boundary for missing data."""
    sources = load_sources(root)
    selected_topics = topics_for(text)
    context = [EVIDENCE_LIMITS]
    for claim in load_claims(root):
        if not selected_topics.intersection(claim.topics):
            continue
        try:
            source = sources[claim.source_id]
        except KeyError as exc:
            raise ValueError(
                f"claim {claim.id} references missing source {claim.source_id}"
            ) from exc
        context.append(
            f"[{claim.id}] {claim.claim} Source: {source.publisher}, "
            f"{source.title}, {claim.locator}. {source.url} "
            f"(verified {source.verified_on}; scope: {source.scope})"
        )
    return context
