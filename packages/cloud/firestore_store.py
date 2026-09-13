"""Cloud object-store adapter with the same governed contract as LocalObjectStore."""
from __future__ import annotations

from packages.governance.review_routing import classify_review
from packages.runtime.context import fingerprint
from packages.contracts.governance import BASE_FIELD_MAP, FieldDefinition, validate_object
from packages.contracts.object import (
    ActorType, CurationPatch, HumanReview, ObjectEvent, ObjectEventType, ObjectRecord,
    ObjectStatus, ReviewDecision, ReviewState, UniversalObject, utc_now,
)
from packages.contracts.store import (
    ContractViolationError, DuplicateObjectError, InvalidTransitionError,
    ObjectNotFoundError, ObjectStoreError, PermissionDeniedError, VersionConflictError,
)
from .firestore_journal import FirestoreJournal, RequestConflict, VersionConflict
from .firestore_transport import (
    CloudAdmissionDenied, FirestoreTransport, ProviderFailure,
    ShortLivedGoogleToken, bounded_production_admission,
)


class FirestoreObjectStore:
    """Versioned object store backed by Firestore transactions and workload identity."""

    def __init__(self, transport=None):
        self.transport = transport or FirestoreTransport(admission=bounded_production_admission)

    def _journal(self, validator=lambda *_args: False):
        return FirestoreJournal(validator, self.transport)

    def get(self, object_id: str) -> UniversalObject:
        try:
            value = self._journal().get(object_id)
        except (CloudAdmissionDenied, ProviderFailure) as exc:
            raise ObjectStoreError("Cloud object read failed closed.") from exc
        if value is None:
            raise ObjectNotFoundError(f"Object not found: {object_id}")
        return UniversalObject.model_validate(value)

    def list_objects(self, *, object_type=None, status=None):
        try:
            values = self._journal().list_current()
        except (CloudAdmissionDenied, ProviderFailure) as exc:
            raise ObjectStoreError("Cloud object listing failed closed.") from exc
        items = [UniversalObject.model_validate(value) for value in values]
        return sorted([
            item for item in items
            if (object_type is None or item.object_type == object_type)
            and (status is None or item.status == status)
        ], key=lambda item: item.updated_at, reverse=True)

    def history(self, object_id):
        if self._journal().get(object_id) is None:
            raise ObjectNotFoundError(f"Object not found: {object_id}")
        try:
            return [ObjectRecord.model_validate(value) for value in self._journal().history(object_id)]
        except (CloudAdmissionDenied, ProviderFailure) as exc:
            raise ObjectStoreError("Cloud object history failed closed.") from exc

    def definitions(self):
        definitions = dict(BASE_FIELD_MAP)
        for item in self.list_objects(object_type="field_definition", status=ObjectStatus.active):
            field = FieldDefinition.model_validate(item.payload)
            if field.key not in definitions:
                definitions[field.key] = field
        return definitions

    def _validated(self, item):
        try:
            validated = validate_object(item, self.definitions(), self.get)
        except ValueError as exc:
            from pydantic import ValidationError
            message = "; ".join(error["msg"] for error in exc.errors(include_input=False)) if isinstance(exc, ValidationError) else str(exc)
            raise ContractViolationError(message) from exc
        if validated.object_type == "field_definition" and validated.status == ObjectStatus.active:
            for other in self.list_objects(object_type="field_definition", status=ObjectStatus.active):
                if other.object_id != validated.object_id and other.payload.get("key") == validated.payload["key"]:
                    raise ContractViolationError("Another active definition already uses this key.")
        return validated

    def _mutate(self, operation, object_id, data, actor_id, actor_type,
                expected_version, idempotency_key, request_input=None):
        if not actor_id:
            raise PermissionDeniedError("An attributable actor is required.")
        if idempotency_key is None or not 8 <= len(idempotency_key) <= 160:
            raise ContractViolationError("Cloud writes require an idempotency key containing 8-160 characters.")
        try:
            current_value = self._journal().get(object_id)
        except (CloudAdmissionDenied, ProviderFailure) as exc:
            raise ObjectStoreError("Cloud mutation preflight failed closed.") from exc
        current = UniversalObject.model_validate(current_value) if current_value else None
        if operation == "capture":
            if current is not None:
                proposed_input = UniversalObject.model_validate(data)
                request_payload = [operation, object_id, request_input if request_input is not None else data,
                                   actor_id, actor_type.value, expected_version]
                proposed_hash = fingerprint(request_payload)
                existing_hash = current.metadata.get("initial_request_hash")
                if existing_hash == proposed_hash:
                    return current
                raise DuplicateObjectError(f"Object already exists: {object_id}")
            item = UniversalObject.model_validate(data)
            item.status, item.version = ObjectStatus.captured, 1
            item.created_by, item.recorded_at = actor_id, utc_now()
            route = classify_review(item, operation="capture")
            item.review = HumanReview(required=route.required)
            request_payload = [operation, object_id, request_input if request_input is not None else data,
                               actor_id, actor_type.value, expected_version]
            item.metadata = {**item.metadata, "governance_route": route.model_dump(),
                             "initial_request_hash": fingerprint(request_payload)}
            event_type = ObjectEventType.captured
            expected = 0
        else:
            if current is None:
                raise ObjectNotFoundError(f"Object not found: {object_id}")
            if expected_version is not None and current.version != expected_version:
                raise VersionConflictError("Object changed. Reload its current version before submitting.")
            if current.status in {ObjectStatus.archived, ObjectStatus.deprecated} and operation != "restore":
                raise InvalidTransitionError("Archived objects cannot be changed.")
            item = current.model_copy(deep=True)
            item.version += 1
            if operation == "curate":
                if current.status == ObjectStatus.rejected:
                    raise InvalidTransitionError("Rejected objects cannot be curated.")
                patch = CurationPatch.model_validate(data)
                if current.object_type == "content_brief" and current.payload.get("workflow_family"):
                    for key in ("workflow_family", "input_versions", "entities"):
                        if patch.payload is not None and key in patch.payload and patch.payload[key] != current.payload.get(key):
                            raise ContractViolationError("Regenerate the draft to change its input lineage.")
                if patch.sources is not None:
                    original_sources = {source.source_id: source for source in current.sources}
                    for source in patch.sources:
                        original = original_sources.get(source.source_id)
                        if original is not None and source.model_dump() != original.model_dump():
                            raise ContractViolationError("Use a new source ID for a changed source observation.")
                    item.sources = patch.sources
                updates = patch.model_dump(exclude_none=True)
                for key in ("title", "purpose", "confidence", "tags"):
                    if key in updates:
                        setattr(item, key, updates[key])
                if patch.payload is not None:
                    item.payload = {**item.payload, **patch.payload}
                if patch.metadata is not None:
                    item.metadata = {**item.metadata, **patch.metadata}
                route = classify_review(item, operation="curate")
                item.status, item.review = ObjectStatus.proposed, HumanReview(required=route.required)
                item.metadata = {**item.metadata, "governance_route": route.model_dump()}
                event_type = ObjectEventType.curated
            elif operation == "review":
                if current.object_type == "refresh_job":
                    raise InvalidTransitionError("Refresh plans are operational records, not factual approval requests.")
                if not classify_review(current, operation="review").required:
                    raise InvalidTransitionError("Routine policy-routed records are monitored, not sent for human approval.")
                if actor_type != ActorType.human:
                    raise PermissionDeniedError("Agents cannot record human approval.")
                decision = ReviewDecision(data["decision"])
                item.review = HumanReview(state=ReviewState(decision.value),
                    requested_at=current.review.requested_at, reviewed_at=utc_now(),
                    reviewed_by=actor_id, notes=data.get("notes"))
                item.status = {ReviewDecision.approved: ObjectStatus.active,
                               ReviewDecision.rejected: ObjectStatus.rejected,
                               ReviewDecision.changes_requested: ObjectStatus.proposed}[decision]
                if decision == ReviewDecision.approved and not item.payload:
                    raise ContractViolationError("An empty draft cannot be approved.")
                event_type = ObjectEventType.reviewed
            elif operation == "archive":
                if actor_type != ActorType.human:
                    raise PermissionDeniedError("Only an authenticated human administrator can retire an object.")
                item.status = ObjectStatus.archived
                item.metadata = {**item.metadata, "retirement": {
                    "reason": data["reason"], "previous_status": current.status.value,
                    "retired_by": actor_id, "retired_at": utc_now().isoformat()}}
                event_type = ObjectEventType.curated
            elif operation == "restore":
                if current.status != ObjectStatus.archived:
                    raise InvalidTransitionError("Only archived objects can be restored.")
                if actor_type != ActorType.human:
                    raise PermissionDeniedError("Only an authenticated human administrator can restore an object.")
                item.status = ObjectStatus.captured
                item.metadata = {**item.metadata, "restoration": {
                    "reason": data["reason"], "restored_by": actor_id, "restored_at": utc_now().isoformat()}}
                route = classify_review(item, operation="curate")
                item.review = HumanReview(required=route.required)
                item.metadata = {**item.metadata, "governance_route": route.model_dump()}
                event_type = ObjectEventType.curated
            else:
                raise ContractViolationError("Unknown operation.")
            expected = current.version
            request_payload = [operation, object_id, data, actor_id, actor_type.value, expected_version]
        item.updated_at = utc_now()
        item = self._validated(item)
        if len(item.parent_ids) > 10:
            raise ContractViolationError("Cloud writes can pin at most ten parent objects per transaction.")
        inputs = {parent_id: self.get(parent_id).version for parent_id in item.parent_ids}
        event = ObjectEvent(event_type=event_type, object_id=item.object_id,
            object_version=item.version, sequence=item.version, actor_type=actor_type,
            actor_id=actor_id, data=data if operation != "capture" else {})
        record = ObjectRecord(event=event, snapshot=item)
        expected_previous_hash = fingerprint(current.model_dump(mode="json")) if current else None
        proposed_hash = fingerprint(item.model_dump(mode="json"))
        actor = {"actor_id": actor_id, "actor_type": actor_type.value}

        def approve(previous, proposed, supplied_actor, _parents):
            previous_hash = fingerprint(previous) if previous else None
            return (previous_hash == expected_previous_hash and fingerprint(proposed) == proposed_hash
                    and supplied_actor == actor)

        try:
            self._journal(approve).compare_and_swap(
                item.model_dump(mode="json"), expected, actor, idempotency_key, inputs,
                record=record.model_dump(mode="json"), request_payload=request_payload,
            )
            return self.get(object_id)
        except VersionConflict as exc:
            raise VersionConflictError(str(exc)) from exc
        except RequestConflict as exc:
            raise VersionConflictError(str(exc)) from exc
        except (CloudAdmissionDenied, ProviderFailure) as exc:
            raise ObjectStoreError("Cloud mutation failed closed.") from exc

    def capture(self, item, *, actor_id, actor_type=ActorType.human, idempotency_key=None, request_input=None):
        return self._mutate("capture", item.object_id, item.model_dump(mode="json"),
                            actor_id, actor_type, None, idempotency_key, request_input)

    def curate(self, object_id, patch, *, actor_id, actor_type=ActorType.agent,
               expected_version=None, idempotency_key=None):
        return self._mutate("curate", object_id, patch.model_dump(mode="json", exclude_none=True),
                            actor_id, actor_type, expected_version, idempotency_key)

    def review(self, object_id, decision, *, reviewer_id, notes=None,
               actor_type=ActorType.human, expected_version=None, idempotency_key=None):
        return self._mutate("review", object_id, {"decision": decision.value, "notes": notes},
                            reviewer_id, actor_type, expected_version, idempotency_key)

    def archive(self, object_id, *, reason, actor_id, actor_type=ActorType.human,
                expected_version=None, idempotency_key=None):
        return self._mutate("archive", object_id, {"reason": reason}, actor_id,
                            actor_type, expected_version, idempotency_key)

    def restore(self, object_id, *, reason, actor_id, actor_type=ActorType.human,
                expected_version=None, idempotency_key=None):
        return self._mutate("restore", object_id, {"reason": reason}, actor_id,
                            actor_type, expected_version, idempotency_key)


def production_store():
    allow_local = __import__("os").getenv("FIRESTORE_ALLOW_LOCAL_CLI") == "1"
    token = ShortLivedGoogleToken(allow_local_cli=allow_local)
    return FirestoreObjectStore(FirestoreTransport(token_source=token, admission=bounded_production_admission))
