from copy import deepcopy
import unittest

from packages.cloud.firestore_journal import FirestoreJournal, RequestConflict, VersionConflict
from packages.cloud.firestore_store import FirestoreObjectStore
from packages.cloud.firestore_transport import (
    AmbiguousCommit, CloudAdmissionDenied, FirestoreTransport, TransactionAborted,
    decode_value, document_data, encode_value,
)
from packages.contracts.object import ActorType, CurationPatch, UniversalObject


class MemoryTransport:
    def __init__(self):
        self.documents = {}
        self.calls = []
        self.mode = None
        self.commits = 0

    def call(self, action, body):
        self.calls.append(action)
        if action == "beginTransaction":
            return {"transaction": "transaction-token"}
        if action == "rollback":
            return {}
        if action == "batchGet":
            return [{"found": deepcopy(self.documents[name])} if name in self.documents else {"missing": name} for name in body["documents"]]
        if action == "runQuery":
            query = body["structuredQuery"]
            collection = query["from"][0]["collectionId"]
            documents = [deepcopy(value) for name, value in self.documents.items()
                         if f"/{collection}/" in name]
            field_filter = query.get("where", {}).get("fieldFilter")
            if field_filter:
                expected = field_filter["value"]["stringValue"]
                documents = [document for document in documents
                             if document_data(document).get(field_filter["field"]["fieldPath"]) == expected]
            documents.sort(key=lambda document: document_data(document).get("version", 0))
            return [{"document": document} for document in documents[:query["limit"]]]
        if action != "commit":
            raise AssertionError("Unexpected transport operation")
        if self.mode == "aborted":
            raise TransactionAborted(action, 409)
        if self.mode == "ambiguous_before":
            raise AmbiguousCommit(action)
        staged = deepcopy(self.documents)
        for write in body["writes"]:
            document = deepcopy(write["update"])
            name = document["name"]
            condition = write["currentDocument"]
            if condition.get("exists") is False and name in staged:
                raise TransactionAborted(action, 409)
            if "updateTime" in condition and staged.get(name, {}).get("updateTime") != condition["updateTime"]:
                raise TransactionAborted(action, 409)
            document["updateTime"] = "2026-09-13T03:00:%02dZ" % self.commits
            staged[name] = document
        self.documents = staged
        self.commits += 1
        if self.mode == "ambiguous_after":
            raise AmbiguousCommit(action)
        return {"commitTime": "2026-09-13T03:00:00Z"}


class FirestoreJournalTests(unittest.TestCase):
    def setUp(self):
        self.transport = MemoryTransport()
        self.journal = FirestoreJournal(lambda previous, proposed, actor, parents: True, self.transport)
        self.actor = {"actor_id": "test-reviewer", "actor_type": "human"}
        self.snapshot = {"object_id": "task_example", "object_type": "runtime_task", "version": 1, "status": "queued", "payload": {"purpose": "Review source coverage"}}

    def commit(self, snapshot=None, expected=0, key="request-example-001", inputs=None):
        return self.journal.compare_and_swap(snapshot or self.snapshot, expected, self.actor, key, inputs)

    def test_creates_current_history_and_receipt_atomically(self):
        result = self.commit()
        self.assertEqual(result["version"], 1)
        self.assertEqual(len(self.transport.documents), 3)
        self.assertEqual(self.journal.get("task_example"), self.snapshot)

    def test_duplicate_request_is_read_only(self):
        result = self.commit()
        self.assertEqual(self.commit(), result)
        self.assertEqual(self.transport.commits, 1)

    def test_changed_content_cannot_reuse_request_key(self):
        self.commit()
        altered = {**self.snapshot, "status": "cancelled"}
        with self.assertRaises(RequestConflict):
            self.commit(altered)

    def test_compare_and_swap_rejects_stale_version(self):
        self.commit()
        with self.assertRaises(VersionConflict):
            self.commit(key="different-request-key")
        self.assertEqual(self.transport.commits, 1)

    def test_valid_version_update_preserves_old_snapshot(self):
        self.commit()
        next_snapshot = {**self.snapshot, "version": 2, "status": "running"}
        self.commit(next_snapshot, 1, "request-example-002")
        self.assertEqual(self.journal.get("task_example")["version"], 2)
        versions = [document_data(value)["version"] for key, value in self.transport.documents.items() if "/governed_object_versions/" in key]
        self.assertEqual(sorted(versions), [1, 2])
        self.assertEqual([item["snapshot"]["version"] for item in self.journal.history("task_example")], [1, 2])
        self.assertEqual(len(self.journal.list_current()), 1)

    def test_domain_validator_must_explicitly_authorize(self):
        self.journal = FirestoreJournal(lambda *args: None, self.transport)
        with self.assertRaises(ValueError):
            self.commit()
        self.assertEqual(self.transport.commits, 0)

    def test_domain_validator_is_required(self):
        with self.assertRaises(ValueError):
            FirestoreJournal(None, self.transport)

    def test_parent_version_is_pinned_in_transaction(self):
        self.commit()
        child = {**self.snapshot, "object_id": "task_child"}
        with self.assertRaises(VersionConflict):
            self.commit(child, key="child-request-001", inputs={"task_example": 2})
        self.assertEqual(self.transport.commits, 1)

    def test_ambiguous_committed_request_resolves_receipt(self):
        self.transport.mode = "ambiguous_after"
        result = self.commit()
        self.assertEqual(result["version"], 1)
        self.assertEqual(self.transport.commits, 1)
        self.assertEqual(self.transport.calls.count("commit"), 1)

    def test_ambiguous_unresolved_request_is_not_retried(self):
        self.transport.mode = "ambiguous_before"
        with self.assertRaises(AmbiguousCommit):
            self.commit()
        self.assertEqual(self.transport.calls.count("commit"), 1)

    def test_aborted_transactions_have_three_attempt_limit(self):
        self.transport.mode = "aborted"
        with self.assertRaises(TransactionAborted):
            self.commit()
        self.assertEqual(self.transport.calls.count("commit"), 3)

    def test_path_escape_is_rejected_before_network(self):
        with self.assertRaises(ValueError):
            self.commit({**self.snapshot, "object_id": "../../another-project"})
        self.assertEqual(self.transport.calls, [])

    def test_probable_credentials_are_rejected_before_network(self):
        with self.assertRaises(ValueError):
            self.commit({**self.snapshot, "payload": {"note": "api_key=not-a-real-key-for-this-test"}})
        self.assertEqual(self.transport.calls, [])

    def test_default_transport_denies_before_accessing_identity(self):
        def no_identity():
            self.fail("Admission must run before identity retrieval")
        transport = FirestoreTransport(token_source=no_identity)
        with self.assertRaises(CloudAdmissionDenied):
            transport.call("beginTransaction", {"options": {"readWrite": {}}})

    def test_value_codec_preserves_false_null_and_numeric_types(self):
        value = {"flag": False, "unknown": None, "count": 2, "measurement": 2.5, "tags": ["evidence", "draft"]}
        self.assertEqual(decode_value(encode_value(value)), value)

    def test_invalid_numeric_and_nested_array_values_are_rejected(self):
        for value in (float("nan"), float("inf"), 2**63, [[1]]):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    encode_value(value)

    def test_cloud_store_matches_capture_curate_read_and_history_contract(self):
        store = FirestoreObjectStore(self.transport)
        item = UniversalObject(object_id="market_example", object_type="market_observation",
            title="Fixture observation", purpose="Exercise the cloud store contract.",
            payload={"summary": "Fixture only."})
        captured = store.capture(item, actor_id="test-agent", actor_type=ActorType.agent,
                                 idempotency_key="capture-market-example")
        replay = store.capture(item, actor_id="test-agent", actor_type=ActorType.agent,
                               idempotency_key="capture-market-example")
        self.assertEqual(captured.model_dump(), replay.model_dump())
        curated = store.curate(item.object_id, CurationPatch(title="Updated fixture"),
                               actor_id="test-agent", actor_type=ActorType.agent,
                               expected_version=1, idempotency_key="curate-market-example")
        self.assertEqual(curated.version, 2)
        self.assertEqual(store.get(item.object_id).title, "Updated fixture")
        self.assertEqual(len(store.list_objects(object_type="market_observation")), 1)
        self.assertEqual([record.snapshot.version for record in store.history(item.object_id)], [1, 2])


if __name__ == "__main__":
    unittest.main()
