#!/usr/bin/env python3
"""Replay allowlisted local governed history into Firestore using atomic receipts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.cloud.firestore_journal import FirestoreJournal
from packages.cloud.firestore_transport import FirestoreTransport, ShortLivedGoogleToken
from packages.contracts.object import ObjectRecord, UniversalObject
from packages.contracts.store import LocalObjectStore
from packages.runtime.context import canonical, fingerprint, reject_obvious_credentials


class MigrationAdmission:
    def __init__(self, maximum_units=5000):
        self.maximum_units = maximum_units
        self.units = 0

    def __call__(self, operation, units):
        if operation not in {"transaction_begin", "transaction_rollback", "document_read", "document_write"}:
            raise RuntimeError("Migration attempted an unapproved cloud operation.")
        if isinstance(units, bool) or not isinstance(units, int) or not 1 <= units <= 20:
            raise RuntimeError("Migration operation exceeded its bounded request size.")
        self.units += units
        if self.units > self.maximum_units:
            raise RuntimeError("Migration exceeded its total admitted Firestore operation budget.")


def records_for(source, allowed_types):
    records = []
    for item in source.list_objects():
        if item.object_type not in allowed_types:
            continue
        records.extend(source.history(item.object_id))
    records.sort(key=lambda record: (record.event.occurred_at, record.event.object_id, record.event.sequence))
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / ".local/object-events.jsonl")
    parser.add_argument("--policy", type=Path, default=ROOT / "config/production-object-types.json")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--maximum-units", type=int, default=5000)
    args = parser.parse_args()
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    allowed_types = set(policy["allowed_types"])
    source = LocalObjectStore(args.source)
    records = records_for(source, allowed_types)
    summary = {
        "objects": len({record.snapshot.object_id for record in records}),
        "versions": len(records),
        "types": sorted({record.snapshot.object_type for record in records}),
        "execute": args.execute,
    }
    if not args.execute:
        print(json.dumps(summary, indent=2))
        return 0
    admission = MigrationAdmission(args.maximum_units)
    transport = FirestoreTransport(
        token_source=ShortLivedGoogleToken(allow_local_cli=True), admission=admission,
    )
    migrated = skipped = 0
    previous_by_object = {}
    for record in records:
        record = ObjectRecord.model_validate(record)
        snapshot = UniversalObject.model_validate(record.snapshot).model_dump(mode="json")
        reject_obvious_credentials({"snapshot": snapshot})
        object_id = snapshot["object_id"]
        current = FirestoreJournal(lambda *_args: False, transport).get(object_id)
        if current and current["version"] >= snapshot["version"]:
            if current["version"] == snapshot["version"] and canonical(current) != canonical(snapshot):
                raise RuntimeError(f"Production object diverges at {object_id} version {snapshot['version']}.")
            previous_by_object[object_id] = current
            skipped += 1
            continue
        expected_previous = previous_by_object.get(object_id)
        if snapshot["version"] != (expected_previous["version"] if expected_previous else 0) + 1:
            raise RuntimeError(f"Local history is not contiguous for {object_id}.")
        actor = {"actor_id": record.event.actor_id, "actor_type": record.event.actor_type.value}
        expected_hash = fingerprint(expected_previous) if expected_previous else None
        proposed_hash = fingerprint(snapshot)

        def approve(previous, proposed, supplied_actor, _parents,
                    before=expected_hash, after=proposed_hash, expected_actor=actor):
            return ((fingerprint(previous) if previous else None) == before
                    and fingerprint(proposed) == after and supplied_actor == expected_actor)

        journal = FirestoreJournal(approve, transport)
        journal.compare_and_swap(
            snapshot, snapshot["version"] - 1, actor,
            f"migration:{object_id}:{snapshot['version']}", record=record.model_dump(mode="json"),
            request_payload={"migration": "local-v1", "object_id": object_id,
                             "version": snapshot["version"], "snapshot_hash": proposed_hash},
        )
        previous_by_object[object_id] = snapshot
        migrated += 1
    print(json.dumps(summary | {"migrated_versions": migrated, "skipped_versions": skipped,
                                "admitted_operation_units": admission.units}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
