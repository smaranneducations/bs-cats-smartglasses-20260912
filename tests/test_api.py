import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from services.api.src.main import app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.environment = patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "test",
                "API_WRITE_TOKEN": "",
                "API_REVIEW_TOKEN": "review-test-only",
                "API_READ_TOKEN": "",
                "API_AGENT_TOKEN": "",
                "ALLOW_LOCAL_OPERATOR": "0",
                "API_OPERATOR_ID": "founder",
                "ALLOWED_HOSTS": "testserver,127.0.0.1,localhost",
                "OBJECT_STORE_PATH": str(
                    Path(self.temporary_directory.name) / "events.jsonl"
                ),
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.client = TestClient(app, headers={"X-BS-CATS-Key": "review-test-only", "X-Workspace-Action": "1"})
        self.addCleanup(self.client.close)

    def test_capture_curate_routine_monitoring_api_flow(self):
        capture = self.client.post(
            "/v1/objects",
            json={
                "object_id": "obj_api_flow",
                "object_type": "market_observation",
                "title": "API-captured signal",
                "purpose": "Prove the service boundary.",
                "payload": {"raw_note": "Captured locally."},
            },
        )
        self.assertEqual(capture.status_code, 201)
        self.assertEqual(capture.json()["status"], "captured")

        curate = self.client.post(
            "/v1/objects/obj_api_flow/curate",
            json={
                "expected_version": 1,
                "patch": {
                    "confidence": 0.76,
                    "payload": {"summary": "Curated for review."},
                }
            },
        )
        self.assertEqual(curate.status_code, 200)
        self.assertEqual(curate.json()["review"]["state"], "pending")

        review = self.client.post(
            "/v1/objects/obj_api_flow/review",
            json={"decision": "approved", "reviewer_id": "founder", "expected_version": 2},
        )
        self.assertEqual(review.status_code, 409)

        history = self.client.get("/v1/objects/obj_api_flow/history")
        self.assertEqual([item["event"]["sequence"] for item in history.json()], [1, 2])

    def test_production_api_requires_configured_token(self):
        with patch.dict(
            os.environ,
            {"ENVIRONMENT": "production", "API_WRITE_TOKEN": "test-secret"},
        ):
            denied = self.client.get("/v1/objects", headers={"X-BS-CATS-Key": ""})
            allowed = self.client.get(
                "/v1/objects", headers={"X-BS-CATS-Key": "test-secret"}
            )
        self.assertEqual(denied.status_code, 401)
        self.assertEqual(allowed.status_code, 200)


if __name__ == "__main__":
    unittest.main()
