from __future__ import annotations

import copy
import os
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

from fastapi.testclient import TestClient

from packages.contracts import ActorType, CurationPatch, LocalObjectStore, ObjectStatus
from packages.contracts.governance import EvidenceValue
from packages.contracts.smart_glasses import EvidenceClaim
from packages.contracts.store import ObjectStoreError, VersionConflictError
from services.api.src.main import app

OBSERVED = "2026-09-01T10:30:00Z"
SOURCES = [
    {"source_id": "source_a", "uri": "https://manufacturer.example.test/spec",
     "title": "Fixture manufacturer", "publisher": "Fixture", "captured_at": OBSERVED},
    {"source_id": "source_b", "uri": "https://independent.example.test/report",
     "title": "Fixture report", "publisher": "Fixture", "captured_at": OBSERVED},
]


def evidence(value, kind="manufacturer_stated", confidence=None):
    return {"value": value, "source_ids": ["source_a", "source_b"], "evidence_kind": kind,
            "conditions": "Fixture conditions, not a real product finding.",
            "observed_at": OBSERVED, "confidence": confidence}


def product_body(oid="product_fixture", fields=None):
    return {"object_id": oid, "object_type": "product", "title": "Fixture display",
        "purpose": "Temporary regression fixture, not catalogue research.",
        "sources": copy.deepcopy(SOURCES),
        "payload": {"summary": "Test fixture", "brand": "Fixture", "category": "display",
            "market": "Test only", "variant": "Test fixture", "buyer_job": "Exercise evidence handling.",
            "fields": fields if fields is not None else {
                "weight_g": evidence(75.5, confidence=0),
                "fov_deg": evidence(46, "independent_test"),
                "audio": evidence("Audible in this observation", "human_observation"),
                "tracking": evidence("May suit this use case", "inference"),
            }}}


class WorkspaceGovernanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "events.jsonl"
        env = {
            "ENVIRONMENT": "production", "ALLOW_LOCAL_OPERATOR": "0",
            "API_OPERATOR_ID": "founder", "ALLOWED_HOSTS": "testserver,127.0.0.1,localhost",
            "API_REVIEW_TOKEN": "review-fixture-only", "API_WRITE_TOKEN": "edit-fixture-only",
            "API_AGENT_TOKEN": "agent-fixture-only", "API_READ_TOKEN": "read-fixture-only",
            "OBJECT_STORE_PATH": str(self.path),
        }
        self.environment = patch.dict(os.environ, env)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.client = TestClient(app, headers={
            "X-BS-CATS-Key": "review-fixture-only", "X-Workspace-Action": "1"})
        self.addCleanup(self.client.close)

    def capture_product(self, oid="product_fixture", fields=None):
        response = self.client.post("/v1/objects", json=product_body(oid, fields))
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def draft(self, oid="product_fixture"):
        response = self.client.post("/v1/content/briefs",
            json={"family": "product", "product_ids": [oid]},
            headers={"Idempotency-Key": "draft-fixture-" + oid})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_metadata_edit_retains_dates_confidence_and_all_references(self):
        item = self.capture_product()
        original_fields = item["payload"]["fields"]
        source = {"source_id": "source_c", "uri": "https://third.example.test/spec",
                  "title": "Additional fixture", "captured_at": OBSERVED}
        result = self.client.post("/v1/objects/product_fixture/curate", json={
            "expected_version": 1, "patch": {"title": "Retitled fixture",
                "payload": {"fields": original_fields}, "sources": item["sources"] + [source]}})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["payload"]["fields"], original_fields)
        self.assertEqual(len(result.json()["sources"]), 3)
        self.assertEqual(result.json()["payload"]["fields"]["weight_g"]["confidence"], 0)
        self.assertEqual(result.json()["review"]["state"], "pending")

    def test_new_source_can_support_an_existing_product_field(self):
        item = self.capture_product()
        fields = copy.deepcopy(item["payload"]["fields"])
        fields["weight_g"]["source_ids"].append("source_c")
        source = {"source_id": "source_c", "uri": "https://third.example.test/spec",
                  "captured_at": OBSERVED}
        result = self.client.post("/v1/objects/product_fixture/curate", json={
            "expected_version": 1, "patch": {"payload": {"fields": fields},
                "sources": item["sources"] + [source]}})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["payload"]["fields"]["weight_g"]["source_ids"],
                         ["source_a", "source_b", "source_c"])

    def test_unknown_source_rolls_back_edit_and_history(self):
        item = self.capture_product()
        fields = copy.deepcopy(item["payload"]["fields"])
        fields["weight_g"]["source_ids"] = ["missing_source"]
        result = self.client.post("/v1/objects/product_fixture/curate", json={
            "expected_version": 1, "patch": {"payload": {"fields": fields}}})
        self.assertEqual(result.status_code, 422, result.text)
        self.assertEqual(self.client.get("/v1/objects/product_fixture").json()["version"], 1)
        self.assertEqual(len(self.client.get("/v1/objects/product_fixture/history").json()), 1)

    def test_existing_source_id_cannot_be_silently_retargeted(self):
        item = self.capture_product()
        item["sources"][0]["uri"] = "https://different.example.test/spec"
        result = self.client.post("/v1/objects/product_fixture/curate", json={
            "expected_version": 1, "patch": {"sources": item["sources"]}})
        self.assertEqual(result.status_code, 422, result.text)

    def test_draft_preserves_units_evidence_types_and_unknown_confidence(self):
        self.capture_product()
        item = self.draft()
        claims = {item["metadata"]["claim_inputs"][claim["claim_id"]]["field_key"]: claim
                  for claim in item["payload"]["claims"]}
        self.assertIn("75.5 g", claims["weight_g"]["statement"])
        self.assertIn("46 degrees", claims["fov_deg"]["statement"])
        self.assertEqual(claims["weight_g"]["confidence"], 0)
        self.assertIsNone(claims["fov_deg"]["confidence"])
        self.assertEqual(claims["fov_deg"]["evidence_tier"], "independent_unassessed")
        self.assertEqual(claims["audio"]["evidence_tier"], "anecdotal")
        self.assertEqual(claims["tracking"]["kind"], "interpretation")
        self.assertEqual(claims["tracking"]["evidence_tier"], "synthetic")
        self.assertTrue(all(c["verification_state"] == "unverified" for c in claims.values()))
        self.assertEqual(item["payload"]["input_versions"], {"product_fixture": 1})

    def test_long_product_identifiers_produce_bounded_claim_ids(self):
        oid = "product_" + "x" * 120
        self.capture_product(oid)
        item = self.draft(oid)
        self.assertTrue(all(len(c["claim_id"]) <= 128 for c in item["payload"]["claims"]))

    def test_unknown_fields_do_not_displace_supported_draft_claims(self):
        fields = {key: evidence(None) for key in
                  ["display_type", "resolution", "fov_deg", "refresh_hz", "brightness_nits", "tracking"]}
        fields["weight_g"] = evidence(12)
        self.capture_product(fields=fields)
        claims = self.draft()["payload"]["claims"]
        self.assertEqual(len(claims), 1)
        self.assertIn("12 g", claims[0]["statement"])

    def test_routine_draft_approval_is_blocked_and_lineage_cannot_be_relabelled(self):
        self.capture_product()
        item = self.draft()
        self.assertEqual(self.client.post("/v1/objects/product_fixture/curate", json={
            "expected_version": 1, "patch": {"title": "New revision"}}).status_code, 200)
        base = "/v1/objects/" + item["object_id"]
        forged = self.client.post(base + "/curate", json={"expected_version": 1,
            "patch": {"payload": {"input_versions": {"product_fixture": 2}}}})
        self.assertEqual(forged.status_code, 422)
        review = self.client.post(base + "/review", json={"expected_version": 1, "decision": "approved"})
        self.assertEqual(review.status_code, 409, review.text)
        self.assertEqual(len(self.client.get(base + "/history").json()), 1)
        reject = self.client.post(base + "/review", json={"expected_version": 1, "decision": "rejected"})
        self.assertEqual(reject.status_code, 409, reject.text)

    def test_approved_custom_fields_supply_units_to_drafts(self):
        definition = self.client.post("/v1/objects", json={
            "object_id": "field_fixture", "object_type": "field_definition",
            "title": "Diagonal", "purpose": "Temporary field fixture.",
            "payload": {"key": "diagonal_inches", "label": "Diagonal", "description": "Fixture measurement.",
                        "value_type": "number", "unit": "inches", "category": "display"}})
        self.assertEqual(definition.status_code, 201, definition.text)
        premature = self.client.post("/v1/objects", json=product_body(fields={"diagonal_inches": evidence(12.5)}))
        self.assertEqual(premature.status_code, 422)
        approved = self.client.post("/v1/objects/field_fixture/review",
            json={"expected_version": 1, "decision": "approved"})
        self.assertEqual(approved.status_code, 200, approved.text)
        self.capture_product(fields={"diagonal_inches": evidence(12.5)})
        self.assertIn("12.5 inches", self.draft()["payload"]["claims"][0]["statement"])

    def test_idempotent_capture_replays_original_and_rejects_changed_input(self):
        body = {"object_type": "market_observation", "title": "Fixture signal",
                "purpose": "Deduplicate a request.", "payload": {"raw_note": "Fixture"}}
        headers = {"Idempotency-Key": "capture-fixture-retry"}
        first = self.client.post("/v1/objects", json=body, headers=headers)
        retry = self.client.post("/v1/objects", json=body, headers=headers)
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(first.json(), retry.json())
        changed = self.client.post("/v1/objects", json={**body, "title": "Changed"}, headers=headers)
        self.assertEqual(changed.status_code, 409)

    def test_revision_is_required_and_stale_revision_is_rejected(self):
        self.capture_product()
        endpoint = "/v1/objects/product_fixture/curate"
        self.assertEqual(self.client.post(endpoint, json={"patch": {"title": "No revision"}}).status_code, 422)
        request = {"expected_version": 1, "patch": {"title": "Updated"}}
        self.assertEqual(self.client.post(endpoint, json=request).status_code, 200)
        self.assertEqual(self.client.post(endpoint, json=request).status_code, 409)

    def test_agent_cannot_forge_human_identity_or_approval(self):
        self.capture_product()
        agent = {"X-BS-CATS-Key": "agent-fixture-only"}
        forged = self.client.post("/v1/objects/product_fixture/curate", headers=agent,
            json={"expected_version": 1, "actor_type": "human", "patch": {"title": "Forged"}})
        self.assertEqual(forged.status_code, 403)
        review = self.client.post("/v1/objects/product_fixture/review", headers=agent,
            json={"expected_version": 1, "decision": "approved"})
        self.assertEqual(review.status_code, 403)
        body = product_body("product_forgery")
        body["created_by"] = "founder"
        self.assertEqual(self.client.post("/v1/objects", json=body, headers=agent).status_code, 403)

    def test_reader_cannot_edit(self):
        response = self.client.post("/v1/objects", json=product_body(),
            headers={"X-BS-CATS-Key": "read-fixture-only"})
        self.assertEqual(response.status_code, 403)

    def test_production_without_credentials_fails_closed(self):
        with patch.dict(os.environ, {name: "" for name in
                        ["API_REVIEW_TOKEN", "API_WRITE_TOKEN", "API_AGENT_TOKEN", "API_READ_TOKEN"]}):
            response = self.client.get("/v1/objects", headers={"X-BS-CATS-Key": ""})
        self.assertEqual(response.status_code, 503)

    def test_cross_site_and_missing_action_headers_are_rejected(self):
        body = product_body()
        response = self.client.post("/v1/objects", json=body, headers={"Origin": "https://other.example.test"})
        self.assertEqual(response.status_code, 403)
        response = self.client.post("/v1/objects", json=body, headers={"X-Workspace-Action": ""})
        self.assertEqual(response.status_code, 403)
        response = self.client.get("/v1/objects", headers={"Sec-Fetch-Site": "cross-site"})
        self.assertEqual(response.status_code, 403)

    def test_chunked_body_limit_and_small_body_replay(self):
        response = self.client.post("/v1/objects",
            content=iter([b"x" * 400000, b"y" * 200000]), headers={"Content-Type": "application/json"})
        self.assertEqual(response.status_code, 413, response.text)
        response = self.client.post("/v1/objects",
            content=iter([b'{"object_type":"market_observation",', b'"title":"Chunked","purpose":"Fixture","payload":{}}']),
            headers={"Content-Type": "application/json"})
        self.assertEqual(response.status_code, 201, response.text)

    def test_invalid_numeric_evidence_cannot_enter_the_store(self):
        with self.assertRaises(ValueError):
            EvidenceValue(value=float("inf"), source_ids=["source_a"], observed_at=OBSERVED)
        response = self.client.post("/v1/objects", json=product_body(fields={"weight_g": evidence(True)}))
        self.assertEqual(response.status_code, 422, response.text)

    def test_unassessed_independent_evidence_cannot_claim_verified(self):
        with self.assertRaises(ValueError):
            EvidenceClaim(claim_id="claim_fixture", statement="Fixture.", kind="fact",
                source_ids=["source_a"], evidence_tier="independent_unassessed", verification_state="verified")

    def test_concurrent_edits_have_one_winner_and_no_lost_history(self):
        self.capture_product()
        store = LocalObjectStore(self.path)
        barrier = Barrier(2)

        def edit(title):
            barrier.wait(timeout=5)
            try:
                store.curate("product_fixture", CurationPatch(title=title),
                    actor_id="fixture-agent", actor_type=ActorType.agent, expected_version=1)
                return "saved"
            except VersionConflictError:
                return "conflict"

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(edit, "First proposal")
            second = pool.submit(edit, "Second proposal")
            outcomes = [first.result(timeout=10), second.result(timeout=10)]
        self.assertCountEqual(outcomes, ["saved", "conflict"])
        self.assertEqual([record.snapshot.version for record in store.history("product_fixture")], [1, 2])

    def test_failed_legacy_import_rolls_back_and_preserves_original(self):
        self.capture_product()
        record = LocalObjectStore(self.path).history("product_fixture")[0]
        legacy = Path(self.temp.name) / "invalid.jsonl"
        original = record.model_dump_json() + "\nnot-json\n"
        legacy.write_text(original, encoding="utf-8")
        with self.assertRaises(ObjectStoreError):
            LocalObjectStore(legacy)
        self.assertEqual(legacy.read_text(encoding="utf-8"), original)
        with sqlite3.connect(legacy.with_suffix(".sqlite3")) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM objects").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
