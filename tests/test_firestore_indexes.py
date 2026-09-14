import json
from pathlib import Path
import unittest

from packages.cloud.firestore_journal import FirestoreJournal


class HistoryIndexTests(unittest.TestCase):
    def test_history_query_has_matching_deployable_index(self):
        class Capture:
            query = None

            def call(self, action, body):
                if action != "runQuery":
                    raise AssertionError("Unexpected history operation")
                self.query = body["structuredQuery"]
                return []

        transport = Capture()
        FirestoreJournal(lambda *_: True, transport).history("product_example")
        query = transport.query
        definition = json.loads((Path(__file__).resolve().parents[1] / "firestore.indexes.json").read_text())
        expected = {
            "collectionGroup": query["from"][0]["collectionId"],
            "queryScope": "COLLECTION",
            "fields": [
                {"fieldPath": query["where"]["fieldFilter"]["field"]["fieldPath"], "order": "ASCENDING"},
                {"fieldPath": query["orderBy"][0]["field"]["fieldPath"], "order": query["orderBy"][0]["direction"]},
            ],
        }
        self.assertIn(expected, definition["indexes"])
        self.assertEqual(query["limit"], 100)

    def test_existing_large_payload_exemptions_remain(self):
        definition = json.loads((Path(__file__).resolve().parents[1] / "firestore.indexes.json").read_text())
        exempt = {(item["collectionGroup"], item["fieldPath"]) for item in definition["fieldOverrides"] if item["indexes"] == []}
        self.assertIn(("governed_objects", "snapshot_json"), exempt)
        self.assertIn(("governed_object_versions", "snapshot_json"), exempt)
        self.assertIn(("governed_requests", "result_json"), exempt)


if __name__ == "__main__":
    unittest.main()
