import json
from datetime import date

import pytest

from src.service_catalogue import (
    SERVICE_LIMITS,
    load_entries,
    load_manifest,
    selected_entries,
    service_context,
    service_evidence_ids,
    topics_for,
)


def test_catalogue_is_explicitly_synthetic_and_versioned():
    manifest = load_manifest()
    assert manifest["authority_type"] == "synthetic_internal_contract"
    assert date.fromisoformat(manifest["effective_from"]) <= date.today()
    assert manifest["version"]
    assert "not evidence about any real insurer" in manifest["scope"]


def test_every_service_entry_has_unique_provenance():
    entries = load_entries()
    assert len(entries) == len({entry.id for entry in entries})
    assert all(entry.owner and entry.guidance for entry in entries)


def test_billing_and_complaint_enquiry_gets_both_service_paths():
    ids = service_evidence_ids(
        "Formal complaint: my premium was deducted twice and I need a refund."
    )
    assert "SVC_BILLING_01" in ids
    assert "SVC_COMPLAINT_01" in ids


def test_non_complaint_does_not_route_to_customer_relations():
    topics = topics_for("This is not a complaint; please stop marketing calls.")
    assert "complaint" not in topics
    assert topics == frozenset({"direct_marketing"})


def test_unknown_topic_is_rejected(tmp_path):
    manifest = load_manifest()
    (tmp_path / "service_catalogue_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    (tmp_path / "service_catalogue.jsonl").write_text(
        json.dumps({"id": "BAD", "topics": ["unknown"], "owner": "x",
                    "guidance": "x"}) + "\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="unknown service topics"):
        load_entries(tmp_path)


def test_context_carries_limits_version_and_selected_evidence_only():
    context = "\n".join(service_context("Please update my address."))
    assert SERVICE_LIMITS in context
    assert "version 1.0.0" in context
    assert "SVC_ADDRESS_01" in context
    assert "SVC_CLAIM_01" not in context


def test_selector_returns_stable_catalogue_order():
    entries = selected_entries("complaint about a medical claim")
    assert [entry.id for entry in entries] == [
        "SVC_CLAIM_01", "SVC_COMPLAINT_01"
    ]


def test_no_topic_means_no_guessed_service_route():
    assert service_evidence_ids("Thank you for the seasonal greeting.") == ()
