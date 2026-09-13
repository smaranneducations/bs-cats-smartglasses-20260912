#!/usr/bin/env python3
"""Create a zero-network private card and Shorts-plan review package."""
from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.audience.composer import compose_audience_package
from packages.contracts import ActorType, LocalObjectStore
from packages.contracts.store import ObjectNotFoundError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=ROOT / ".local" / "object-events.jsonl")
    parser.add_argument("--product-id")
    args = parser.parse_args()
    store = LocalObjectStore(args.store)
    products = [item for item in store.list_objects() if item.object_type == "product"
                and item.status.value == "active" and item.review.state.value == "approved"]
    product = next((item for item in products if item.object_id == args.product_id), None) if args.product_id else (products[0] if products else None)
    if product is None:
        raise SystemExit("No active, human-approved product is available for a private audience preview.")
    cards, bundle, plan = compose_audience_package(store, product, max_cards=6, duration_seconds=60)
    inserted = []
    for item in [*cards, bundle, plan]:
        try:
            store.get(item.object_id)
        except ObjectNotFoundError:
            store.capture(item, actor_id="audience-card-composer", actor_type=ActorType.agent,
                idempotency_key="audience-preview-" + sha256(item.object_id.encode()).hexdigest())
            inserted.append(item.object_id)
    print(f"Prepared {len(inserted)} new private review object(s) for {product.title}.")
    print("Open http://127.0.0.1:8766/discover?preview=1. Nothing was published or uploaded.")


if __name__ == "__main__":
    main()
