"""Versioned synthetic operating evidence for the fictional case-study insurer."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path


CATALOGUE_ROOT = Path(__file__).resolve().parents[1] / "knowledge"
MANIFEST_NAME = "service_catalogue_manifest.json"
CATALOGUE_NAME = "service_catalogue.jsonl"

SERVICE_LIMITS = (
    "Internal evidence boundary: these are synthetic operating rules for the "
    "Harbourview Life case study, not facts about a real insurer. They do not "
    "establish an individual policy term, account state, completed action, "
    "refund entitlement, claim outcome or case-specific deadline. Never invent "
    "a contact address, form location, case reference, completed action or SLA."
)

TOPIC_TERMS: dict[str, tuple[str, ...]] = {
    "policy_information": (
        "cash value", "benefit illustration", "policy statement", "sum assured",
        "policy status", "policy still", "premium due", "annual statement",
    ),
    "address_change": (
        "change of address", "update the address", "update my address",
        "new address", "moved",
        "correspondence address",
    ),
    "premium_billing": (
        "autopay", "deduct", "debit", "double charge", "duplicate", "billing",
        "refund",
    ),
    "medical_claim": (
        "make a claim", "put in a claim", "claim form", "hospital claim",
        "hospital bill",
        "surgery", "medical", "receipt", "doctor",
        "letter of guarantee",
    ),
    "complaint": ("complaint", "complain", "mis-selling", "misled"),
    "direct_marketing": (
        "marketing", "telemarketing", "promotional", "sales call", "opt out",
    ),
    "data_access": ("data access", "personal data", "privacy", "ops003"),
    "suspected_fraud": (
        "suspicious sms", "whatsapp", "fraud", "scam", "phishing", "suspicious link",
    ),
    "vendor_invoice": (
        "vendor", "invoice", "purchase order", "accounts payable", "supplier",
    ),
}


@dataclass(frozen=True)
class ServiceEntry:
    id: str
    topics: tuple[str, ...]
    owner: str
    guidance: str


def load_manifest(root: Path = CATALOGUE_ROOT) -> dict:
    manifest = json.loads((root / MANIFEST_NAME).read_text(encoding="utf-8"))
    if manifest.get("authority_type") != "synthetic_internal_contract":
        raise ValueError("service catalogue must be labelled synthetic")
    if date.fromisoformat(manifest["effective_from"]) > date.today():
        raise ValueError("service catalogue has a future effective date")
    if not manifest.get("version") or not manifest.get("scope"):
        raise ValueError("service catalogue manifest is incomplete")
    return manifest


def load_entries(root: Path = CATALOGUE_ROOT) -> list[ServiceEntry]:
    load_manifest(root)
    entries, seen = [], set()
    for line in (root / CATALOGUE_NAME).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        raw["topics"] = tuple(raw["topics"])
        entry = ServiceEntry(**raw)
        if entry.id in seen:
            raise ValueError(f"duplicate service evidence id: {entry.id}")
        if not entry.owner.strip() or not entry.guidance.strip():
            raise ValueError(f"incomplete service evidence: {entry.id}")
        unknown = set(entry.topics) - set(TOPIC_TERMS)
        if unknown:
            raise ValueError(f"unknown service topics for {entry.id}: {sorted(unknown)}")
        seen.add(entry.id)
        entries.append(entry)
    if not entries:
        raise ValueError("service catalogue is empty")
    return entries


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


def selected_entries(text: str, root: Path = CATALOGUE_ROOT) -> list[ServiceEntry]:
    selected_topics = topics_for(text)
    return [entry for entry in load_entries(root)
            if selected_topics.intersection(entry.topics)]


def service_context(text: str, root: Path = CATALOGUE_ROOT) -> list[str]:
    manifest = load_manifest(root)
    context = [
        SERVICE_LIMITS,
        f"Catalogue {manifest['catalogue_id']} version {manifest['version']}; "
        f"scope: {manifest['scope']}",
    ]
    context.extend(
        f"[{entry.id}] Owner: {entry.owner}. {entry.guidance}"
        for entry in selected_entries(text, root)
    )
    return context


def service_evidence_ids(text: str, root: Path = CATALOGUE_ROOT) -> tuple[str, ...]:
    return tuple(entry.id for entry in selected_entries(text, root))
