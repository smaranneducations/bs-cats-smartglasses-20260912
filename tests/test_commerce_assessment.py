import copy
from datetime import datetime, timedelta, timezone
import unittest
from pydantic import ValidationError
from packages.contracts.commerce_assessment import CommercialEvidencePayload
from packages.intelligence.commerce import assess_commerce, EVIDENCE_GATES

NOW = datetime(2026, 9, 13, 4, 30, tzinfo=timezone.utc)


def path():
    return {"object_id": "commerce_test_path", "object_type": "commerce_path", "version": 1, "title": "Test commercial path", "status": "captured", "review": {"state": "pending"}, "sources": [{"source_id": "source_terms", "uri": "https://merchant.example/program", "captured_at": NOW.isoformat()}], "payload": {"summary": "Public program candidate", "merchant_uri": "https://merchant.example/", "program_uri": "https://merchant.example/program", "customer_market": "US storefront only", "checkout": "unknown", "publisher_access": "not_applied", "commission_rate": None, "evidence_source_ids": ["source_terms"], "observed_at": NOW.isoformat()}}


def proof():
    return {"object_id": "commerce_evidence_test", "object_type": "commerce_evidence", "version": 1, "status": "captured", "review": {"state": "approved"}, "updated_at": NOW.isoformat(), "sources": [{"source_id": "source_private_terms", "uri": "local://governed-agreement-reference", "captured_at": NOW.isoformat()}], "payload": {"summary": "Fixture only, not a real accepted agreement", "path_id": "commerce_test_path", "path_version": 1, "checked_at": NOW.isoformat(), "recheck_after": (NOW + timedelta(days=7)).isoformat(), "authority_basis": "account_holder_reviewed_documents", "findings": [{"gate": gate, "finding": "clear", "rationale": "Documented fixture condition", "evidence_source_ids": ["source_private_terms"]} for gate in EVIDENCE_GATES]}}


class CommerceAssessmentTests(unittest.TestCase):
    def test_public_program_is_not_access_or_income(self):
        result = assess_commerce([path()], [], NOW)["assessment"]
        self.assertEqual(result["paths"][0]["stage"], "awaiting_evidence")
        self.assertFalse(result["publication_authorized"])
        self.assertFalse(result["tracked_links_authorized"])
        self.assertFalse(result["predicted_earnings_included"])

    def test_rate_does_not_change_readiness(self):
        first = path()
        second = copy.deepcopy(first)
        second["payload"]["commission_rate"] = 0.9
        self.assertEqual(assess_commerce([first], [], NOW)["assessment"]["paths"], assess_commerce([second], [], NOW)["assessment"]["paths"])

    def test_complete_evidence_still_does_not_authorize_publication(self):
        item = path()
        item["review"]["state"] = "approved"
        item["payload"].update({"checkout": "observed", "publisher_access": "approved"})
        result = assess_commerce([item], [proof()], NOW)["assessment"]
        self.assertEqual(result["paths"][0]["stage"], "ready_for_exact_artifact_review")
        self.assertFalse(result["financial_commitment_authorized"])
        self.assertFalse(result["publication_authorized"])

    def test_wrong_version_evidence_cannot_clear_gates(self):
        item = path()
        item["version"] = 2
        result = assess_commerce([item], [proof()], NOW)["assessment"]
        self.assertTrue(all(gate["state"] != "clear" for gate in result["paths"][0]["gates"] if gate["gate"] in EVIDENCE_GATES))

    def test_pending_new_evidence_does_not_resurrect_old_approval(self):
        old = proof()
        new = copy.deepcopy(old)
        new.update({"object_id": "commerce_evidence_new", "updated_at": (NOW + timedelta(seconds=1)).isoformat(), "review": {"state": "pending"}})
        result = assess_commerce([path()], [old, new], NOW)["assessment"]
        self.assertIn("commerce_evidence_new", result["input_versions"])
        self.assertNotIn("commerce_evidence_test", result["input_versions"])

    def test_expired_evidence_is_not_clear(self):
        item = proof()
        item["payload"]["checked_at"] = (NOW - timedelta(days=8)).isoformat()
        item["payload"]["recheck_after"] = (NOW - timedelta(days=1)).isoformat()
        result = assess_commerce([path()], [item], NOW)["assessment"]
        self.assertEqual(result["paths"][0]["stage"], "awaiting_evidence")

    def test_missing_evidence_sources_do_not_clear_a_gate(self):
        item = proof()
        item["sources"] = []
        result = assess_commerce([path()], [item], NOW)["assessment"]
        self.assertTrue(all(gate["state"] != "clear" for gate in result["paths"][0]["gates"] if gate["gate"] in EVIDENCE_GATES))

    def test_explicit_adverse_evidence_blocks_path(self):
        item = proof()
        item["payload"]["findings"][3]["finding"] = "not_clear"
        self.assertEqual(assess_commerce([path()], [item], NOW)["assessment"]["paths"][0]["stage"], "blocked_by_evidence")

    def test_public_analysis_cannot_claim_publisher_approval(self):
        values = proof()["payload"]
        values["authority_basis"] = "public_document_analysis"
        with self.assertRaises(ValidationError):
            CommercialEvidencePayload.model_validate(values)

    def test_future_source_observation_is_not_fresh(self):
        item = path()
        item["sources"][0]["captured_at"] = (NOW + timedelta(days=1)).isoformat()
        gates = assess_commerce([item], [], NOW)["assessment"]["paths"][0]["gates"]
        self.assertEqual(gates[0]["state"], "unknown")

    def test_unbounded_candidate_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_commerce([path()] * 5, [], NOW)


if __name__ == "__main__":
    unittest.main()
