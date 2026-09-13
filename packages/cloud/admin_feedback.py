from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from typing import Literal

from pydantic import Field

from packages.contracts import ActorType, UniversalObject
from packages.contracts.object import StrictContract
from packages.contracts.store import ObjectNotFoundError
from packages.runtime.context import reject_obvious_credentials
from .firestore_transport import FirestoreTransport, document_data


class CloudAdminFeedback(StrictContract):
    schema_version: Literal["admin-feedback-1"] = "admin-feedback-1"
    title: str = Field(min_length=1, max_length=240)
    input: str = Field(min_length=1, max_length=4000)
    classification: Literal["preference", "correction", "operating_directive", "hypothesis", "ontology_gap"]
    system_area: Literal["governance", "agents_workflows", "ontology_schema", "data_evidence", "content_editorial", "media_rights", "release_publication", "commerce", "cost_operations", "audience_experience"]
    proposed_improvement: str = Field(default="", max_length=3000)
    target_ids: list[str] = Field(default_factory=list, max_length=30)
    submitted_at: datetime
    status: Literal["submitted"] = "submitted"


class FirestoreAdminFeedbackReader:
    def __init__(self, transport: FirestoreTransport):
        self.transport = transport

    def fetch(self, limit=20):
        response = self.transport.call("runQuery", {"structuredQuery": {
            "from": [{"collectionId": "admin_feedback"}],
            "orderBy": [{"field": {"fieldPath": "submitted_at"}, "direction": "ASCENDING"}],
            "limit": limit}})
        result = []
        for row in response:
            document = row.get("document")
            if not document:
                continue
            data = document_data(document)
            reject_obvious_credentials(data)
            result.append((document["name"], CloudAdminFeedback.model_validate(data)))
        return result

    def import_into(self, store, limit=20):
        imported, retained = [], []
        for name, feedback in self.fetch(limit):
            identity = sha256(name.encode()).hexdigest()
            object_id = "feedback_cloud_" + identity[:24]
            item = UniversalObject(object_id=object_id, object_type="feedback", title=feedback.title,
                purpose="Preserve authenticated cloud-admin feedback as a governed proposal input.",
                parent_ids=feedback.target_ids, payload={"summary": feedback.title, "input": feedback.input,
                    "classification": feedback.classification, "system_area": feedback.system_area,
                    "authority": "operating_directive" if feedback.classification == "operating_directive" else "observation",
                    "target_ids": feedback.target_ids, "proposed_improvement": feedback.proposed_improvement},
                metadata={"origin": "firestore_admin_feedback", "source_document_hash": identity,
                    "submitted_at": feedback.submitted_at.isoformat(), "automatic_policy_promotion": False})
            try:
                store.get(object_id)
            except ObjectNotFoundError:
                store.capture(item, actor_id="firestore-feedback-reader", actor_type=ActorType.system,
                    idempotency_key="cloud-feedback-" + identity)
                imported.append(object_id)
            else:
                retained.append(object_id)
        return {"imported": imported, "retained": retained, "policy_changed": False,
                "publication_allowed": False}
