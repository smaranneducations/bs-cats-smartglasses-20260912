from __future__ import annotations

from packages.governance.review_routing import classify_review

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .object import (
    ActorType, CurationPatch, HumanReview, ObjectEvent, ObjectEventType,
    ObjectRecord, ObjectStatus, ReviewDecision, ReviewState, UniversalObject, utc_now,
)


class ObjectStoreError(RuntimeError):
    pass


class ObjectNotFoundError(ObjectStoreError):
    pass


class DuplicateObjectError(ObjectStoreError):
    pass


class InvalidTransitionError(ObjectStoreError):
    pass


class VersionConflictError(ObjectStoreError):
    pass


class ContractViolationError(ObjectStoreError):
    pass


class PermissionDeniedError(ObjectStoreError):
    pass


class LocalObjectStore:
    """Transactional snapshots, history and request deduplication on local SQLite."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.db_path = self.path.with_suffix(".sqlite3") if self.path.suffix == ".jsonl" else self.path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.db_path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        os.chmod(self.db_path, 0o600)
        with self._connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS objects(
                    object_id TEXT PRIMARY KEY, version INTEGER NOT NULL, snapshot TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events(
                    object_id TEXT NOT NULL, version INTEGER NOT NULL, record TEXT NOT NULL,
                    PRIMARY KEY(object_id, version));
                CREATE TABLE IF NOT EXISTS requests(
                    request_key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, snapshot TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """)
            if self.path.suffix == ".jsonl" and self.path.exists():
                self._import_legacy(db)

    @contextmanager
    def _connection(self):
        db = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
        except sqlite3.Error as exc:
            if db.in_transaction:
                db.rollback()
            raise ObjectStoreError("Local database operation failed.") from exc
        finally:
            db.close()

    def _import_legacy(self, db):
        db.execute("BEGIN IMMEDIATE")
        try:
            if db.execute("SELECT 1 FROM settings WHERE key='legacy_import'").fetchone():
                db.commit()
                return
            versions = {}
            with self.path.open(encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, 1):
                    if not line.strip():
                        continue
                    try:
                        record = ObjectRecord.model_validate_json(line)
                    except ValueError as exc:
                        raise ObjectStoreError(f"Invalid legacy record at line {line_number}.") from exc
                    item = record.snapshot
                    expected = versions.get(item.object_id, 0) + 1
                    if (item.version != expected or record.event.sequence != expected
                            or record.event.object_version != expected
                            or record.event.object_id != item.object_id):
                        raise ObjectStoreError("Legacy history has inconsistent identities or versions.")
                    versions[item.object_id] = expected
                    record.event.data = {**record.event.data, "legacy_identity_unverified": True}
                    self._write_record(db, record)
            db.execute("INSERT INTO settings VALUES('legacy_import', ?)", (str(self.path),))
            db.commit()
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def _get(db, object_id):
        row = db.execute("SELECT snapshot FROM objects WHERE object_id=?", (object_id,)).fetchone()
        if row is None:
            raise ObjectNotFoundError(f"Object not found: {object_id}")
        return UniversalObject.model_validate_json(row["snapshot"])

    @staticmethod
    def _write_record(db, record):
        item = record.snapshot
        db.execute("INSERT INTO events VALUES(?,?,?)",
                   (item.object_id, item.version, record.model_dump_json()))
        db.execute("""INSERT INTO objects VALUES(?,?,?)
                    ON CONFLICT(object_id) DO UPDATE SET version=excluded.version,snapshot=excluded.snapshot""",
                   (item.object_id, item.version, item.model_dump_json()))

    def get(self, object_id: str) -> UniversalObject:
        with self._connection() as db:
            return self._get(db, object_id)

    def list_objects(self, *, object_type=None, status=None):
        with self._connection() as db:
            items = [UniversalObject.model_validate_json(row["snapshot"])
                     for row in db.execute("SELECT snapshot FROM objects")]
        return sorted([item for item in items
                       if (object_type is None or item.object_type == object_type)
                       and (status is None or item.status == status)],
                      key=lambda item: item.updated_at, reverse=True)

    def history(self, object_id):
        with self._connection() as db:
            self._get(db, object_id)
            return [ObjectRecord.model_validate_json(row["record"]) for row in db.execute(
                "SELECT record FROM events WHERE object_id=? ORDER BY version", (object_id,))]

    @staticmethod
    def _definitions(db):
        from .governance import BASE_FIELD_MAP, FieldDefinition
        definitions = dict(BASE_FIELD_MAP)
        for row in db.execute("SELECT snapshot FROM objects"):
            item = UniversalObject.model_validate_json(row["snapshot"])
            if item.object_type == "field_definition" and item.status == ObjectStatus.active:
                field = FieldDefinition.model_validate(item.payload)
                if field.key not in definitions:
                    definitions[field.key] = field
        return definitions

    def definitions(self):
        with self._connection() as db:
            return self._definitions(db)

    def _mutate(self, operation, object_id, data, actor_id, actor_type,
                expected_version, idempotency_key, request_input=None):
        from .governance import validate_object
        if not actor_id:
            raise PermissionDeniedError("An attributable actor is required.")
        if idempotency_key is not None and not (8 <= len(idempotency_key) <= 160):
            raise ContractViolationError("Idempotency keys must contain 8-160 characters.")
        fingerprint = hashlib.sha256(json.dumps(
            [operation, object_id, request_input if request_input is not None else data, actor_id, actor_type.value, expected_version],
            sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
        request_key = f"{actor_type.value}:{actor_id}:{idempotency_key}" if idempotency_key else None
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                if request_key:
                    row = db.execute("SELECT * FROM requests WHERE request_key=?", (request_key,)).fetchone()
                    if row:
                        if row["fingerprint"] != fingerprint:
                            raise VersionConflictError("Idempotency key already used for different input.")
                        result = UniversalObject.model_validate_json(row["snapshot"])
                        db.commit()
                        return result
                if operation == "capture":
                    if db.execute("SELECT 1 FROM objects WHERE object_id=?", (object_id,)).fetchone():
                        raise DuplicateObjectError(f"Object already exists: {object_id}")
                    item = UniversalObject.model_validate(data)
                    item.status, item.version = ObjectStatus.captured, 1
                    item.created_by, item.recorded_at = actor_id, utc_now()
                    route = classify_review(item, operation="capture")
                    item.review = HumanReview(required=route.required)
                    item.metadata = {**item.metadata, "governance_route": route.model_dump()}
                    event_type = ObjectEventType.captured
                else:
                    current = self._get(db, object_id)
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
                            "reason": data["reason"], "restored_by": actor_id,
                            "restored_at": utc_now().isoformat()}}
                        route = classify_review(item, operation="curate")
                        item.review = HumanReview(required=route.required)
                        item.metadata = {**item.metadata, "governance_route": route.model_dump()}
                        event_type = ObjectEventType.curated
                    else:
                        raise ContractViolationError("Unknown operation.")
                item.updated_at = utc_now()
                try:
                    item = validate_object(item, self._definitions(db), lambda oid: self._get(db, oid))
                except ValueError as exc:
                    from pydantic import ValidationError
                    message = "; ".join(error["msg"] for error in exc.errors(include_input=False)) if isinstance(exc, ValidationError) else str(exc)
                    raise ContractViolationError(message) from exc
                if item.object_type == "field_definition" and item.status == ObjectStatus.active:
                    for row in db.execute("SELECT snapshot FROM objects WHERE object_id!=?", (item.object_id,)):
                        other = UniversalObject.model_validate_json(row["snapshot"])
                        if other.object_type == "field_definition" and other.status == ObjectStatus.active and other.payload.get("key") == item.payload["key"]:
                            raise ContractViolationError("Another active definition already uses this key.")
                record = ObjectRecord(event=ObjectEvent(event_type=event_type,
                    object_id=item.object_id, object_version=item.version, sequence=item.version,
                    actor_type=actor_type, actor_id=actor_id, data=data if operation != "capture" else {}),
                    snapshot=item)
                self._write_record(db, record)
                if request_key:
                    db.execute("INSERT INTO requests VALUES(?,?,?)",
                               (request_key, fingerprint, item.model_dump_json()))
                db.commit()
                return item
            except Exception:
                db.rollback()
                raise

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
