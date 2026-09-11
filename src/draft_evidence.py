"""Assemble public and synthetic-internal evidence without merging provenance."""

from __future__ import annotations

from dataclasses import dataclass

from src.reference_pack import EVIDENCE_LIMITS, load_sources, selected_claims
from src.service_catalogue import (
    SERVICE_LIMITS,
    load_manifest,
    selected_entries,
)


@dataclass(frozen=True)
class DraftEvidence:
    ids: tuple[str, ...]
    context: tuple[str, ...]


def draft_evidence(text: str) -> DraftEvidence:
    """Select only relevant evidence and retain its source class in the prompt."""
    sources = load_sources()
    public = selected_claims(text)
    services = selected_entries(text)
    manifest = load_manifest()

    context = [
        "PUBLIC REGULATORY EVIDENCE",
        EVIDENCE_LIMITS,
    ]
    context.extend(
        f"[{claim.id}] {claim.claim} Source: {sources[claim.source_id].publisher}, "
        f"{sources[claim.source_id].title}, {claim.locator}."
        for claim in public
    )
    context.extend((
        "SYNTHETIC INTERNAL SERVICE CONTRACT",
        SERVICE_LIMITS,
        f"Catalogue {manifest['catalogue_id']} version {manifest['version']}.",
    ))
    context.extend(
        f"[{entry.id}] Owner: {entry.owner}. {entry.guidance}"
        for entry in services
    )
    return DraftEvidence(
        ids=tuple([claim.id for claim in public]
                  + [entry.id for entry in services]),
        context=tuple(context),
    )
