from src.draft_evidence import draft_evidence


def test_evidence_bundle_keeps_public_and_internal_provenance_distinct():
    evidence = draft_evidence(
        "Formal complaint about a duplicate premium deduction and refund."
    )
    joined = "\n".join(evidence.context)
    assert "PUBLIC REGULATORY EVIDENCE" in joined
    assert "SYNTHETIC INTERNAL SERVICE CONTRACT" in joined
    assert "COMPLAINT_01" in evidence.ids
    assert "SVC_COMPLAINT_01" in evidence.ids
    assert "SVC_BILLING_01" in evidence.ids


def test_evidence_bundle_does_not_load_unrelated_service_paths():
    evidence = draft_evidence("Please change my correspondence address.")
    assert "SVC_ADDRESS_01" in evidence.ids
    assert "SVC_CLAIM_01" not in evidence.ids
    assert "SVC_BILLING_01" not in evidence.ids
