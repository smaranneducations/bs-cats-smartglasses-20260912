import base64
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from packages.intelligence.gmail_alerts import diagnose_delivery, ingest


WORKFLOW = {
    "workflow_id": "gmail_alert_intelligence",
    "domain": "smart_glasses",
    "source": {
        "alert_sender": "googlealerts-noreply@google.com",
        "max_messages_per_run": 25,
        "max_pages_per_run": 2,
    },
}


class FakeStore:
    def __init__(self):
        self.objects = {}

    def capture(self, item, **_kwargs):
        self.objects[item.object_id] = item
        return item


class DiagnosticClient:
    def __init__(self, counts):
        self.counts = counts
        self.queries = []

    def get(self, suffix, parameters):
        self.assert_messages_endpoint(suffix)
        self.queries.append(parameters)
        key = (parameters["q"], parameters["includeSpamTrash"])
        return {"resultSizeEstimate": self.counts.get(key, 0)}

    @staticmethod
    def assert_messages_endpoint(suffix):
        if suffix != "messages":
            raise AssertionError("Diagnostic must not read a message body.")


class IngestClient:
    def __init__(self):
        html = '<a href="https://news.example.test/story?utm_source=alert">Story</a>'
        encoded = base64.urlsafe_b64encode(html.encode()).decode().rstrip("=")
        self.message = {
            "id": "message-1",
            "internalDate": "1789257600000",
            "payload": {"mimeType": "text/html", "body": {"data": encoded}},
        }

    def get(self, suffix, _parameters):
        if suffix == "messages":
            return {"messages": [{"id": "message-1"}]}
        if suffix == "messages/message-1":
            return self.message
        raise AssertionError(suffix)


class GmailAlertTests(unittest.TestCase):
    def test_delivery_diagnostic_uses_counts_without_reading_bodies(self):
        query = 'from:googlealerts-noreply@google.com "smart glasses"'
        client = DiagnosticClient({(query, "true"): 2})
        result = diagnose_delivery(client, WORKFLOW, query)
        self.assertEqual(result["state"], "matching_alert_only_in_spam_or_trash")
        self.assertEqual(result["message_ids_retained"], 0)
        self.assertEqual(result["message_bodies_read"], 0)
        self.assertEqual(len(client.queries), 3)

    def test_ingest_creates_separate_blocked_news_item_and_deduplicates(self):
        store = FakeStore()
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "alerts.sqlite3"
            first = ingest(IngestClient(), store, WORKFLOW, database, "fixture", datetime(2026, 9, 13, tzinfo=UTC))
            second = ingest(IngestClient(), store, WORKFLOW, database, "fixture", datetime(2026, 9, 13, tzinfo=UTC) + timedelta(minutes=1))
        self.assertEqual(first["articles_new"], 1)
        self.assertEqual(second["articles_new"], 0)
        self.assertEqual(len(first["news_discovery_item_ids"]), 1)
        item = store.objects[first["news_discovery_item_ids"][0]]
        self.assertEqual(item.object_type, "news_discovery_item")
        self.assertEqual(item.payload["evidence_state"], "discovery_only")
        self.assertEqual(item.payload["video_eligibility"], "blocked_pending_source_admission")
        self.assertFalse(item.metadata["human_review_required"])


if __name__ == "__main__":
    unittest.main()
