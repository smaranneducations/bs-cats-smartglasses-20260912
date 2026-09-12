from __future__ import annotations

import os
from pathlib import Path

from .object import (
    ActorType,
    CurationPatch,
    HumanReview,
    ObjectEvent,
    ObjectEventType,
    ObjectRecord,
    ObjectStatus,
    ReviewDecision,
    ReviewState,
    UniversalObject,
    utc_now,
)


class ObjectStoreError(RuntimeError):
    pass


class ObjectNotFoundError(ObjectStoreError):
    pass


class DuplicateObjectError(ObjectStoreError):
    pass


class InvalidTransitionError(ObjectStoreError):
    pass


class LocalObjectStore:
    """Append-only local event store for a single-founder development workflow."""

    def __init__(self, path: Path):
        self.path = path

    def _records(self) -> list[ObjectRecord]:
        if not self.path.exists():
            return []

        records: list[ObjectRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    records.append(ObjectRecord.model_validate_json(line))
                except ValueError as exc:
                    raise ObjectStoreError(
                        f"Invalid object-store record at line {line_number}."
                    ) from exc
        return records

    def _append(self, record: ObjectRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            os.chmod(self.path, 0o600)
            handle.write(record.model_dump_json())
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _latest_record(self, object_id: str) -> ObjectRecord:
        for record in reversed(self._records()):
            if record.snapshot.object_id == object_id:
                return record
        raise ObjectNotFoundError(f"Object not found: {object_id}")

    def get(self, object_id: str) -> UniversalObject:
        return self._latest_record(object_id).snapshot

    def list_objects(
        self,
        *,
        object_type: str | None = None,
        status: ObjectStatus | None = None,
    ) -> list[UniversalObject]:
        latest: dict[str, UniversalObject] = {}
        for record in self._records():
            latest[record.snapshot.object_id] = record.snapshot
        objects = latest.values()
        if object_type is not None:
            objects = (item for item in objects if item.object_type == object_type)
        if status is not None:
            objects = (item for item in objects if item.status == status)
        return sorted(objects, key=lambda item: item.updated_at, reverse=True)

    def history(self, object_id: str) -> list[ObjectRecord]:
        records = [
            record for record in self._records() if record.snapshot.object_id == object_id
        ]
        if not records:
            raise ObjectNotFoundError(f"Object not found: {object_id}")
        return records

    def capture(
        self,
        item: UniversalObject,
        *,
        actor_id: str,
        actor_type: ActorType = ActorType.human,
    ) -> UniversalObject:
        try:
            self.get(item.object_id)
        except ObjectNotFoundError:
            pass
        else:
            raise DuplicateObjectError(f"Object already exists: {item.object_id}")

        captured = UniversalObject.model_validate(item.model_dump(mode="python"))
        captured.status = ObjectStatus.captured
        captured.version = 1
        captured.updated_at = utc_now()
        record = ObjectRecord(
            event=ObjectEvent(
                event_type=ObjectEventType.captured,
                object_id=captured.object_id,
                object_version=captured.version,
                sequence=1,
                actor_type=actor_type,
                actor_id=actor_id,
            ),
            snapshot=captured,
        )
        self._append(record)
        return captured

    def curate(
        self,
        object_id: str,
        patch: CurationPatch,
        *,
        actor_id: str,
        actor_type: ActorType = ActorType.agent,
    ) -> UniversalObject:
        latest_record = self._latest_record(object_id)
        current = latest_record.snapshot
        if current.status in {
            ObjectStatus.rejected,
            ObjectStatus.archived,
            ObjectStatus.deprecated,
        }:
            raise InvalidTransitionError(
                f"Cannot curate an object with status {current.status.value}."
            )

        curated = current.model_copy(deep=True)
        updates = patch.model_dump(exclude_none=True)
        for field in ("title", "purpose", "confidence", "tags"):
            if field in updates:
                setattr(curated, field, updates[field])
        if patch.payload is not None:
            curated.payload = {**curated.payload, **patch.payload}
        if patch.metadata is not None:
            curated.metadata = {**curated.metadata, **patch.metadata}
        curated.status = ObjectStatus.proposed
        curated.version += 1
        curated.updated_at = utc_now()
        curated.review = HumanReview(required=True, state=ReviewState.pending)

        record = ObjectRecord(
            event=ObjectEvent(
                event_type=ObjectEventType.curated,
                object_id=curated.object_id,
                object_version=curated.version,
                sequence=latest_record.event.sequence + 1,
                actor_type=actor_type,
                actor_id=actor_id,
                data=updates,
            ),
            snapshot=curated,
        )
        self._append(record)
        return curated

    def review(
        self,
        object_id: str,
        decision: ReviewDecision,
        *,
        reviewer_id: str,
        notes: str | None = None,
    ) -> UniversalObject:
        latest_record = self._latest_record(object_id)
        current = latest_record.snapshot
        if current.status in {ObjectStatus.archived, ObjectStatus.deprecated}:
            raise InvalidTransitionError(
                f"Cannot review an object with status {current.status.value}."
            )

        reviewed = current.model_copy(deep=True)
        reviewed.version += 1
        reviewed.updated_at = utc_now()
        reviewed.review = HumanReview(
            required=True,
            state=ReviewState(decision.value),
            requested_at=current.review.requested_at,
            reviewed_at=reviewed.updated_at,
            reviewed_by=reviewer_id,
            notes=notes,
        )
        if decision == ReviewDecision.approved:
            reviewed.status = ObjectStatus.active
        elif decision == ReviewDecision.rejected:
            reviewed.status = ObjectStatus.rejected
        else:
            reviewed.status = ObjectStatus.proposed

        record = ObjectRecord(
            event=ObjectEvent(
                event_type=ObjectEventType.reviewed,
                object_id=reviewed.object_id,
                object_version=reviewed.version,
                sequence=latest_record.event.sequence + 1,
                actor_type=ActorType.human,
                actor_id=reviewer_id,
                data={"decision": decision.value, "notes": notes},
            ),
            snapshot=reviewed,
        )
        self._append(record)
        return reviewed
