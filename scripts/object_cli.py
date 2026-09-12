#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.contracts import (  # noqa: E402
    ActorType,
    CurationPatch,
    LocalObjectStore,
    ObjectStatus,
    ObjectStoreError,
    ReviewDecision,
    SourceReference,
    UniversalObject,
)


def json_object(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"Invalid JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise argparse.ArgumentTypeError("Value must be a JSON object.")
    return value


def emit(value: Any) -> None:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    elif isinstance(value, list):
        value = [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            for item in value
        ]
    print(json.dumps(value, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    default_store = Path(
        os.getenv(
            "BS_CATS_LOCAL_OBJECT_STORE",
            PROJECT_ROOT / ".local" / "object-events.jsonl",
        )
    )
    parser = argparse.ArgumentParser(
        description="Cost-free local capture, curation, and human-review workflow."
    )
    parser.add_argument("--store", type=Path, default=default_store)
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture = subparsers.add_parser("capture", help="Capture a new domain object.")
    capture.add_argument("--id", dest="object_id")
    capture.add_argument("--type", dest="object_type", required=True)
    capture.add_argument("--domain", default="smart_glasses")
    capture.add_argument("--title", required=True)
    capture.add_argument("--purpose", required=True)
    capture.add_argument("--payload-json", type=json_object, default={})
    capture.add_argument("--tag", action="append", default=[])
    capture.add_argument("--source-url")
    capture.add_argument("--source-title")
    capture.add_argument("--actor", default="founder")
    capture.add_argument(
        "--actor-type", choices=[item.value for item in ActorType], default="human"
    )

    curate = subparsers.add_parser("curate", help="Curate an object and request review.")
    curate.add_argument("object_id")
    curate.add_argument("--title")
    curate.add_argument("--purpose")
    curate.add_argument("--confidence", type=float)
    curate.add_argument("--tag", action="append")
    curate.add_argument("--payload-json", type=json_object)
    curate.add_argument("--metadata-json", type=json_object)
    curate.add_argument("--actor", default="curation-agent")
    curate.add_argument(
        "--actor-type", choices=[item.value for item in ActorType], default="agent"
    )

    review = subparsers.add_parser("review", help="Apply the mandatory human gate.")
    review.add_argument("object_id")
    review.add_argument("--decision", choices=[item.value for item in ReviewDecision], required=True)
    review.add_argument("--reviewer", default="founder")
    review.add_argument("--notes")

    show = subparsers.add_parser("show", help="Show the current object snapshot.")
    show.add_argument("object_id")

    history = subparsers.add_parser("history", help="Show the append-only object history.")
    history.add_argument("object_id")

    listing = subparsers.add_parser("list", help="List current object snapshots.")
    listing.add_argument("--type", dest="object_type")
    listing.add_argument("--status", choices=[item.value for item in ObjectStatus])
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    store = LocalObjectStore(args.store)
    try:
        if args.command == "capture":
            sources = []
            source_uris = []
            if args.source_url:
                sources.append(SourceReference(uri=args.source_url, title=args.source_title))
                source_uris.append(args.source_url)
            values = {
                "object_type": args.object_type,
                "domain": args.domain,
                "title": args.title,
                "purpose": args.purpose,
                "created_by": args.actor,
                "source": source_uris,
                "sources": sources,
                "tags": args.tag,
                "payload": args.payload_json,
            }
            if args.object_id:
                values["object_id"] = args.object_id
            item = UniversalObject(**values)
            emit(
                store.capture(
                    item,
                    actor_id=args.actor,
                    actor_type=ActorType(args.actor_type),
                )
            )
        elif args.command == "curate":
            patch_values = {
                "title": args.title,
                "purpose": args.purpose,
                "confidence": args.confidence,
                "tags": args.tag,
                "payload": args.payload_json,
                "metadata": args.metadata_json,
            }
            patch = CurationPatch(**patch_values)
            if not patch.model_dump(exclude_none=True):
                parser.error("curate requires at least one changed field")
            emit(
                store.curate(
                    args.object_id,
                    patch,
                    actor_id=args.actor,
                    actor_type=ActorType(args.actor_type),
                )
            )
        elif args.command == "review":
            emit(
                store.review(
                    args.object_id,
                    ReviewDecision(args.decision),
                    reviewer_id=args.reviewer,
                    notes=args.notes,
                )
            )
        elif args.command == "show":
            emit(store.get(args.object_id))
        elif args.command == "history":
            emit(store.history(args.object_id))
        else:
            status = ObjectStatus(args.status) if args.status else None
            emit(store.list_objects(object_type=args.object_type, status=status))
    except (ObjectStoreError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
