from __future__ import annotations

from datetime import datetime, timezone
import json
import re

from packages.runtime.context import canonical, fingerprint, reject_obvious_credentials
from .firestore_transport import (
    DOCUMENTS, AmbiguousCommit, FirestoreTransport, ProviderFailure,
    TransactionAborted, document_data, document_fields,
)

IDENTIFIER = re.compile(r"^[A-Za-z0-9_:-]{1,160}$")


class VersionConflict(ValueError):
    pass


class RequestConflict(ValueError):
    pass


class FirestoreJournal:
    """Atomic current object, version history, and idempotency receipt.

    Domain authorization and transition validation are mandatory collaborators.
    This storage adapter cannot substitute for those policies or Firebase Auth.
    """

    def __init__(self, transition_validator, transport=None):
        if not callable(transition_validator):
            raise ValueError("A domain transition and authorization validator is required.")
        self.validate_transition = transition_validator
        self.transport = transport or FirestoreTransport()

    @staticmethod
    def name(collection, identifier):
        if collection not in {"governed_objects", "governed_object_versions", "governed_requests"} or not IDENTIFIER.fullmatch(identifier):
            raise ValueError("Invalid governed document identifier.")
        return DOCUMENTS + "/" + collection + "/" + identifier

    def read(self, names, transaction=None):
        if len(names) != len(set(names)):
            raise ValueError("Duplicate transaction read keys.")
        request = {"documents": names}
        if transaction:
            request["transaction"] = transaction
        response = self.transport.call("batchGet", request)
        if not isinstance(response, list):
            raise ProviderFailure("batchGet_response")
        found = {}
        for item in response:
            if "found" in item:
                document = item["found"]
                name = document["name"]
                if "updateTime" not in document:
                    raise ProviderFailure("document_version_missing")
                value = {"data": document_data(document), "update_time": document["updateTime"]}
            elif "missing" in item:
                name, value = item["missing"], None
            else:
                continue
            if name not in names or name in found:
                raise ProviderFailure("batchGet_identity_mismatch")
            found[name] = value
        if set(found) != set(names):
            raise ProviderFailure("batchGet_incomplete")
        return found

    def get(self, object_id):
        name = self.name("governed_objects", object_id)
        result = self.read([name])[name]
        return json.loads(result["data"]["snapshot_json"]) if result else None

    def receipt(self, name, request_hash):
        item = self.read([name])[name]
        if item is None:
            return None
        if item["data"].get("request_hash") != request_hash:
            raise RequestConflict("The request key belongs to different content or authority.")
        return json.loads(item["data"]["result_json"])

    def rollback(self, transaction):
        try:
            self.transport.call("rollback", {"transaction": transaction})
        except ProviderFailure:
            # Preserve the primary failure; server transaction expiry is the fallback.
            pass

    def list_current(self, limit=500):
        response = self.transport.call("runQuery", {"structuredQuery": {
            "from": [{"collectionId": "governed_objects"}], "limit": limit,
        }})
        result = []
        for row in response:
            document = row.get("document")
            if document:
                result.append(json.loads(document_data(document)["snapshot_json"]))
        return result

    def history(self, object_id, limit=100):
        self.name("governed_objects", object_id)
        response = self.transport.call("runQuery", {"structuredQuery": {
            "from": [{"collectionId": "governed_object_versions"}],
            "where": {"fieldFilter": {
                "field": {"fieldPath": "object_id"}, "op": "EQUAL",
                "value": {"stringValue": object_id},
            }},
            "orderBy": [{"field": {"fieldPath": "version"}, "direction": "ASCENDING"}],
            "limit": limit,
        }})
        result = []
        for row in response:
            document = row.get("document")
            if not document:
                continue
            data = document_data(document)
            result.append(json.loads(data["record_json"]) if data.get("record_json") else {
                "snapshot": json.loads(data["snapshot_json"]),
                "event": {
                    "event_type": "captured" if data["version"] == 1 else "curated",
                    "object_id": object_id, "object_version": data["version"], "sequence": data["version"],
                    "actor_id": data["actor_id"], "actor_type": data["actor_type"],
                    "occurred_at": data["recorded_at"], "data": {"cloud_history_reconstructed": True},
                },
            })
        return result

    def compare_and_swap(self, snapshot, expected_version, actor, idempotency_key, input_versions=None,
                         record=None, request_payload=None):
        if isinstance(expected_version, bool) or not isinstance(expected_version, int) or expected_version < 0:
            raise ValueError("Expected version must be a nonnegative integer.")
        if not isinstance(snapshot, dict) or not IDENTIFIER.fullmatch(str(snapshot.get("object_id", ""))):
            raise ValueError("A named, versioned object snapshot is required.")
        if type(snapshot.get("version")) is not int or snapshot["version"] != expected_version + 1:
            raise VersionConflict("The new snapshot must increment the expected version exactly once.")
        if not snapshot.get("object_type") or not snapshot.get("status"):
            raise ValueError("Object type and lifecycle status are required.")
        if not isinstance(actor, dict) or not actor.get("actor_id") or actor.get("actor_type") not in {"human", "agent", "system"}:
            raise ValueError("An authenticated actor must be supplied by the application boundary.")
        if not isinstance(idempotency_key, str) or not 8 <= len(idempotency_key) <= 160:
            raise ValueError("A bounded idempotency key is required.")
        inputs = dict(input_versions or {})
        if len(inputs) > 10 or snapshot["object_id"] in inputs or any(type(value) is not int or value < 1 for value in inputs.values()):
            raise ValueError("Pin at most ten distinct parent object versions.")
        for key in inputs:
            self.name("governed_objects", key)
        reject_obvious_credentials({"snapshot": snapshot, "actor": actor})
        if record is not None:
            if (not isinstance(record, dict) or record.get("snapshot") != snapshot
                    or record.get("event", {}).get("object_id") != snapshot["object_id"]
                    or record.get("event", {}).get("object_version") != snapshot["version"]):
                raise ValueError("A supplied history record must describe the exact proposed snapshot.")
            reject_obvious_credentials({"record": record})
        serialized = canonical(snapshot)
        if len(serialized.encode()) > 262144:
            raise ValueError("Object snapshots are limited to 256 KiB.")
        request_hash = fingerprint({"request": request_payload if request_payload is not None else snapshot,
                                    "expected_version": expected_version, "actor": actor, "input_versions": inputs})
        request_id = fingerprint([actor["actor_type"], actor["actor_id"], idempotency_key])
        receipt_name = self.name("governed_requests", request_id)
        object_name = self.name("governed_objects", snapshot["object_id"])
        version_name = self.name("governed_object_versions", fingerprint([snapshot["object_id"], snapshot["version"]]))
        input_names = {key: self.name("governed_objects", key) for key in inputs}
        names = [receipt_name, object_name, *input_names.values()]
        for attempt in range(3):
            transaction = None
            try:
                transaction = self.transport.call("beginTransaction", {"options": {"readWrite": {}}})["transaction"]
                read = self.read(names, transaction)
                existing_receipt = read[receipt_name]
                if existing_receipt:
                    if existing_receipt["data"].get("request_hash") != request_hash:
                        raise RequestConflict("The request key was already used with different content or authority.")
                    self.rollback(transaction)
                    return json.loads(existing_receipt["data"]["result_json"])
                current = read[object_name]
                previous = json.loads(current["data"]["snapshot_json"]) if current else None
                if (previous["version"] if previous else 0) != expected_version:
                    raise VersionConflict("The object changed; recompute against its current version.")
                parents = {}
                for key, name in input_names.items():
                    item = read[name]
                    if not item or item["data"].get("version") != inputs[key]:
                        raise VersionConflict("A pinned parent changed or is unavailable.")
                    parents[key] = json.loads(item["data"]["snapshot_json"])
                # A validator must explicitly return True. It must be pure because
                # an aborted transaction may invoke it again with fresh reads.
                if self.validate_transition(previous, snapshot, actor, parents) is not True:
                    raise ValueError("The domain transition or actor authority was not approved.")
                when = datetime.now(timezone.utc).isoformat()
                result = {"object_id": snapshot["object_id"], "version": snapshot["version"],
                          "snapshot_hash": fingerprint(snapshot), "request_id": request_id}
                envelope = {"object_id": snapshot["object_id"], "object_type": snapshot["object_type"],
                            "version": snapshot["version"], "status": snapshot["status"],
                            "snapshot_json": serialized, "snapshot_hash": result["snapshot_hash"],
                            "actor_id": actor["actor_id"], "actor_type": actor["actor_type"],
                            "recorded_at": when, "input_versions_json": canonical(inputs),
                            "record_json": canonical(record) if record is not None else ""}
                writes = [
                    {"update": {"name": object_name, "fields": document_fields(envelope)},
                     "currentDocument": {"updateTime": current["update_time"]} if current else {"exists": False}},
                    {"update": {"name": version_name, "fields": document_fields(envelope)}, "currentDocument": {"exists": False}},
                    {"update": {"name": receipt_name, "fields": document_fields({"request_hash": request_hash,
                        "result_json": canonical(result), "recorded_at": when, "actor_id": actor["actor_id"]})},
                     "currentDocument": {"exists": False}},
                ]
                self.transport.call("commit", {"transaction": transaction, "writes": writes})
                return result
            except AmbiguousCommit:
                # A missing receipt is not proof that an uncertain commit failed.
                # Resolve if present; otherwise require the caller to retain this
                # operation identity and reconcile, not issue a replacement key.
                resolved = self.receipt(receipt_name, request_hash)
                if resolved is not None:
                    return resolved
                raise
            except TransactionAborted:
                if transaction:
                    self.rollback(transaction)
                if attempt == 2:
                    raise
            except Exception:
                if transaction:
                    self.rollback(transaction)
                raise
        raise ProviderFailure("transaction_attempts_exhausted")
