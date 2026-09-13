#!/usr/bin/env python3
"""Prepare one exact canonical distribution package and publication review request."""

import argparse
from hashlib import sha256
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.contracts import ActorType, LocalObjectStore
from packages.contracts.store import ObjectNotFoundError
from packages.publishing import build_distribution_objects, write_manual_kits


def retain(store, item):
    try:
        existing = store.get(item.object_id)
        if existing.payload != item.payload:
            raise ValueError(f"Existing object {item.object_id} has different pinned content.")
        return existing
    except ObjectNotFoundError:
        return store.capture(item, actor_id="distribution-orchestrator", actor_type=ActorType.agent,
            idempotency_key="distribution-" + sha256(item.object_id.encode()).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_id")
    parser.add_argument("--concept", required=True, help="The single primary ontology concept in the video")
    parser.add_argument("--product", action="append", dest="products", default=[])
    parser.add_argument("--destination", action="append", dest="destinations", default=[])
    parser.add_argument("--poster-uri")
    parser.add_argument("--captions-uri")
    parser.add_argument("--app-base-url", default=os.getenv("PUBLIC_APP_BASE_URL", "http://127.0.0.1:8766"))
    parser.add_argument("--store", type=Path, default=ROOT / ".local" / "object-events.jsonl")
    args = parser.parse_args()
    store = LocalObjectStore(args.store)
    package, request = build_distribution_objects(store, args.artifact_id, args.concept,
        product_ids=args.products or None, destinations=args.destinations or None,
        app_base_url=args.app_base_url, poster_uri=args.poster_uri, captions_uri=args.captions_uri)
    package, request = retain(store, package), retain(store, request)
    kits = write_manual_kits(package)
    print(f"Prepared package {package.object_id} and pending approval {request.object_id}.")
    print(f"Manual kits: {kits}")
    print("Nothing was uploaded or published. Approve only the exact publication_request.")


if __name__ == "__main__":
    main()
