from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch
from pathlib import Path
from packages.runtime.local_api import LocalAgentClient, LocalCredentialError


class LocalAgentClientTests(unittest.TestCase):
    def credential(self):
        return {"agent_token": "not-a-real-token-used-only-in-unit-test", "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()}

    def client(self, identity=None):
        identity = identity or {"actor_id": "research-agent", "actor_type": "agent", "role": "editor", "mode": "token"}
        with patch("packages.runtime.local_api.load_local_credential", return_value=self.credential()), patch.object(LocalAgentClient, "get", return_value=identity):
            return LocalAgentClient(Path("unused-fixture-path"))

    def test_human_role_cannot_be_used_as_agent_fallback(self):
        with self.assertRaises(LocalCredentialError):
            self.client({"actor_id": "founder", "actor_type": "human", "role": "reviewer", "mode": "local_operator"})

    def test_reader_role_cannot_mutate_as_agent(self):
        with self.assertRaises(LocalCredentialError):
            self.client({"actor_id": "research-agent", "actor_type": "agent", "role": "reader", "mode": "token"})

    def test_capture_identity_is_bound_to_authentication(self):
        client = self.client()
        with patch.object(client, "_request", return_value={}) as request:
            client.capture({"title": "Test"}, "test-capture-1")
            body = request.call_args.args[2]
            self.assertEqual(body["actor_type"], "agent")
            self.assertEqual(body["created_by"], "research-agent")

    def test_capture_cannot_impersonate_human(self):
        client = self.client()
        with self.assertRaises(ValueError):
            client.capture({"created_by": "founder"}, "test-capture-2")

    def test_review_endpoint_rejected_before_transport(self):
        client = self.client()
        with patch.object(client._opener, "open") as request:
            with self.assertRaises(ValueError):
                client._request("POST", "/v1/objects/test-object/review", {}, "test-review-1")
            request.assert_not_called()

    def test_remote_path_rejected_before_transport(self):
        client = self.client()
        with self.assertRaises(ValueError):
            client.get("https://outside.example/v1/objects")

    def test_curate_requires_version(self):
        with self.assertRaises(ValueError):
            self.client().curate("test-object", {}, 0, "test-curate-1")


if __name__ == "__main__":
    unittest.main()
