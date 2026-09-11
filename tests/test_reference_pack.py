import json
from datetime import date

import pytest

from src.reference_pack import (
    EVIDENCE_LIMITS,
    load_claims,
    load_sources,
    reference_context,
    topics_for,
)


def test_every_claim_has_a_known_source():
    sources = load_sources()
    claims = load_claims()
    assert claims
    assert all(claim.source_id in sources for claim in claims)
    assert all(
        set(claim.topics).issubset(sources[claim.source_id].topics)
        for claim in claims
    )


def test_sources_are_https_first_party_and_reviewed():
    for source in load_sources().values():
        assert source.url.startswith("https://")
        assert date.fromisoformat(source.verified_on) <= date.today()
        assert source.scope


def test_an_untrusted_host_is_rejected(tmp_path):
    manifest = [{
        "id": "BLOG", "publisher": "A blog", "authority_type": "blog",
        "title": "Plausible advice", "url": "https://example.com/advice",
        "topics": ["medical_claim"], "verified_on": "2026-09-10",
        "scope": "none",
    }]
    (tmp_path / "source_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="untrusted reference host"):
        load_sources(tmp_path)


def test_topic_selection_keeps_irrelevant_law_out_of_the_prompt():
    context = "\n".join(reference_context(
        "Please stop promotional email and telemarketing calls."
    ))
    assert EVIDENCE_LIMITS in context
    assert "MARKETING_01" in context
    assert "DAR_01" not in context
    assert "PARTICIPATING_01" not in context


def test_multi_topic_enquiry_receives_each_relevant_source():
    topics = topics_for(
        "This is a complaint about my hospital claim and premium deduction."
    )
    assert topics == frozenset({"complaint", "medical_claim", "premium_billing"})


def test_generic_cash_value_in_fraud_report_does_not_imply_participating_policy():
    assert "participating_policy" not in topics_for(
        "A suspicious WhatsApp says my policy will lose all cash value."
    )


def test_explicit_non_complaint_does_not_load_complaint_routing():
    context = "\n".join(reference_context(
        "This isn't a complaint. Please stop promotional emails."
    ))
    assert "MARKETING_01" in context
    assert "COMPLAINT_01" not in context


def test_address_question_does_not_load_levy_only_for_saying_premium():
    context = "\n".join(reference_context(
        "Will changing my address affect my premium?"
    ))
    assert "LEVY_01" not in context
