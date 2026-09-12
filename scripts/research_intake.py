#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pydantic import ValidationError  # noqa: E402

from packages.contracts import (  # noqa: E402
    ActorType,
    CurationPatch,
    LocalObjectStore,
    ObjectStoreError,
)
from packages.contracts.research import ResearchManifest  # noqa: E402


def ingest_manifest(
    manifest_path: Path,
    store_path: Path,
    *,
    actor_id: str = "research-agent",
    validate_only: bool = False,
) -> dict[str, str | int]:
    manifest = ResearchManifest.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    item = manifest.to_object()
    if validate_only:
        return {
            "object_id": item.object_id,
            "status": "valid",
            "version": item.version,
        }

    store = LocalObjectStore(store_path)
    captured = store.capture(
        item,
        actor_id=actor_id,
        actor_type=ActorType.agent,
    )
    proposed = store.curate(
        captured.object_id,
        CurationPatch(
            metadata={
                "research_stage": "ready_for_human_review",
                "human_review_required": True,
            }
        ),
        actor_id=actor_id,
        actor_type=ActorType.agent,
    )
    return {
        "object_id": proposed.object_id,
        "status": proposed.status.value,
        "version": proposed.version,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and ingest a provenance-first research manifest."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--store",
        type=Path,
        default=PROJECT_ROOT / ".local" / "object-events.jsonl",
    )
    parser.add_argument("--actor", default="research-agent")
    parser.add_argument("--validate-only", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = ingest_manifest(
            args.manifest,
            args.store,
            actor_id=args.actor,
            validate_only=args.validate_only,
        )
    except (OSError, ValidationError, ObjectStoreError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
