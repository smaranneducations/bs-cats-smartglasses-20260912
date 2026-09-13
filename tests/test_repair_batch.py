"""Regression boundaries for the explicitly approved integration repair batch."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest

from packages.contracts.governance import BASE_FIELD_MAP
from packages.contracts.object import UniversalObject
from packages.contracts.warehouse_execution import WarehousePricePolicy
from packages.contracts.workflows import compose_brief, project_field_claim
from packages.intelligence.commerce import assess_commerce
from packages.media.planning import validate_storyboard
from packages.runtime.tools import source_policy_queue


NOW = datetime(2026, 9, 13, 7, 0, tzinfo=timezone.utc)


class MemoryStore:
    def __init__(self, items):
        self.items = items

    def list_objects(self):
        return self.items

    def definitions(self):
        return BASE_FIELD_MAP


class RepairBatchTests(unittest.TestCase):
    def source_policy(self, state):
        return SimpleNamespace(object_type="source_policy", object_id="policy_test", version=1,
            review=SimpleNamespace(model_dump=lambda **_: {"state": state}),
            payload={"automation": "allowed", "commercial_reuse": "allowed", "media_reuse": "allowed",
                     "terms_uri": "https://example.com/terms", "access": "manual_excerpt",
                     "permission_expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()})

    def test_source_adviser_reads_actual_review_state_and_access(self):
        row = source_policy_queue(None, [self.source_policy("approved")], {}, {})["source_policies"][0]
        self.assertEqual(row["access_method"], "manual_excerpt")
        self.assertEqual(row["blockers"], [])
        self.assertFalse(row["automated_collection_available"])

    def test_pending_source_review_is_not_approved(self):
        row = source_policy_queue(None, [self.source_policy("pending")], {}, {})["source_policies"][0]
        self.assertIn("human_source_policy_approval_not_established", row["blockers"])

    def path_record(self, observed):
        return {"object_id": "commerce_test", "version": 1, "title": "Test path", "status": "captured",
                "review": {"state": "pending"}, "sources": [{"source_id": "source_test", "uri": "https://example.com/terms", "captured_at": observed.isoformat()}],
                "payload": {"summary": "A research-only path", "merchant_uri": "https://example.com",
                            "customer_market": "Unverified", "observed_at": observed.isoformat(),
                            "evidence_source_ids": ["source_test"]}}

    def test_commerce_source_is_stale_at_exact_thirty_days(self):
        result = assess_commerce([self.path_record(NOW - timedelta(days=30))], [], NOW)["assessment"]
        gate = next(g for g in result["paths"][0]["gates"] if g["gate"] == "source_freshness")
        self.assertEqual(gate["state"], "unknown")
        self.assertFalse(result["publication_authorized"])

    def test_commerce_fresh_report_expires_at_source_boundary(self):
        result = assess_commerce([self.path_record(NOW - timedelta(days=30) + timedelta(seconds=1))], [], NOW)["assessment"]
        expiry = datetime.fromisoformat(result["valid_until"].replace("Z", "+00:00"))
        self.assertEqual(expiry, NOW + timedelta(seconds=1))

    def test_unknown_public_observation_is_representable_not_fabricated(self):
        price = WarehousePricePolicy(public_reference_uri="https://cloud.google.com/bigquery/pricing",
                                     public_reference_usd_per_tib="6.25", public_reference_observed_at=None)
        self.assertIsNone(price.public_reference_observed_at)
        self.assertFalse(price.account_on_demand_verified)

    def story_fixture(self):
        values = {"weight_g": 80, "display_type": "Micro-OLED", "resolution": "1920 x 1080 per eye",
                  "fov_deg": 45, "refresh_hz": 120, "brightness_nits": 600,
                  "tracking": "3DoF through supported software"}
        fields = {key: {"value": value, "source_ids": ["source_test"], "evidence_kind": "manufacturer_stated",
                        "observed_at": NOW.isoformat(), "conditions": "Supported host required.", "confidence": None}
                  for key, value in values.items()}
        product = UniversalObject(object_id="product_test", object_type="product", title="Test display",
            purpose="Test evidence projection", sources=[{"source_id": "source_test", "uri": "https://example.com/spec",
                     "title": "Manufacturer specification", "captured_at": NOW}],
            payload={"category": "display", "buyer_job": "Compare compatible hosts", "fields": fields, "caveats": []})
        brief = compose_brief("product", [product], "research-agent", "repair-test", BASE_FIELD_MAP)
        claim, binding = project_field_claim(product, "tracking", BASE_FIELD_MAP)
        self.assertNotIn(claim["claim_id"], [item["claim_id"] for item in brief.payload["claims"]])
        brief.payload["claims"] = [claim]
        brief.metadata["claim_inputs"] = {claim["claim_id"]: binding}
        story = SimpleNamespace(object_id="story_test", object_type="storyboard", version=1,
            payload={"brief_object_id": brief.object_id, "brief_version": brief.version, "workflow_family": "product",
                     "scenes": [{"claim_ids": [claim["claim_id"]], "lines": [claim["statement"]]}]})
        return MemoryStore([product, brief, story]), product, brief, story, claim, binding

    def test_source_bound_concept_after_first_six_is_admitted(self):
        store, _, _, story, _, _ = self.story_fixture()
        self.assertEqual(validate_storyboard(store, story.object_id)[0], story)

    def test_shortened_unbound_claim_text_is_still_rejected(self):
        store, _, _, story, _, _ = self.story_fixture()
        story.payload["scenes"][0]["lines"] = ["Works with every phone"]
        with self.assertRaises(ValueError):
            validate_storyboard(store, story.object_id)

    def test_omitted_line_binding_is_still_rejected(self):
        store, _, _, story, _, _ = self.story_fixture()
        story.payload["scenes"][0]["lines"].append("An unbound additional statement")
        with self.assertRaises(ValueError):
            validate_storyboard(store, story.object_id)

    def test_changed_claim_source_is_rejected(self):
        store, _, _, story, claim, _ = self.story_fixture()
        claim["source_ids"] = ["another_source"]
        with self.assertRaises(ValueError):
            validate_storyboard(store, story.object_id)

    def test_changed_definition_is_rejected(self):
        store, _, _, story, _, binding = self.story_fixture()
        binding["definition"] = {**binding["definition"], "label": "A different concept"}
        with self.assertRaises(ValueError):
            validate_storyboard(store, story.object_id)

    def test_changed_product_version_is_rejected(self):
        store, product, _, story, _, _ = self.story_fixture()
        product.version += 1
        with self.assertRaises(ValueError):
            validate_storyboard(store, story.object_id)

    def test_dropped_conditions_are_rejected(self):
        store, _, _, story, claim, _ = self.story_fixture()
        claim["caveats"] = []
        with self.assertRaises(ValueError):
            validate_storyboard(store, story.object_id)


if __name__ == "__main__":
    unittest.main()
