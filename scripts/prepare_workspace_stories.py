#!/usr/bin/env python3
"""Create private local story drafts and blocked refresh plans, without network calls."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.contracts.object import ActorType
from packages.contracts.production import build_storyboard, refresh_job
from packages.contracts.workflows import compose_brief
from services.api.src.main import get_store
from services.api.src.workspace_planning import capture_once


def main() -> None:
    store = get_store()
    principal = SimpleNamespace(actor_id="local-production-planner", actor_type=ActorType.agent)
    products = [
        item for item in store.list_objects(object_type="product")
        if item.status.value not in {"archived", "rejected", "deprecated"}
    ]

    def product(title: str):
        matches = [item for item in products if item.title.casefold().strip() == title.casefold()]
        if len(matches) != 1:
            raise RuntimeError(f"Expected one existing product record named {title!r}; no substitute evidence will be invented.")
        return matches[0]

    # Resolve all inputs before writing. These are existing evidence records,
    # not imported specifications, independently tested claims or new sources.
    one_pro = product("XREAL One Pro")
    one = product("XREAL One")
    air = product("XREAL Air 2 Pro")
    requests = [
        ("comparison", [one_pro, one], "16:9"),
        ("product", [air], "9:16"),
        ("feature", [one_pro], "16:9"),
    ]
    output = []
    for family, inputs, aspect in requests:
        revisions = ",".join(f"{item.object_id}:{item.version}" for item in inputs)
        brief = compose_brief(
            family, inputs, actor_id=principal.actor_id,
            request_key=f"local-scene-preview-v1:{family}:{revisions}",
        )
        brief = capture_once(store, brief, principal)
        storyboard = capture_once(store, build_storyboard(brief, aspect), principal)
        output.append({
            "family": family, "storyboard_id": storyboard.object_id,
            "duration_seconds": storyboard.payload["duration_seconds"],
            "aspect_ratio": aspect,
            "local_url": f"http://127.0.0.1:8766/#object/{storyboard.object_id}",
        })

    plans = [
        capture_once(store, refresh_job(policy), principal)
        for policy in store.list_objects(object_type="source_policy")
    ]
    print(json.dumps({
        "storyboards": output,
        "saved_refresh_plans": len(plans),
        "collection_enabled": False,
        "publication_enabled": False,
        "paid_api_calls": 0,
        "note": "Private draft creation only; not a test run, MP4 render or approval.",
    }, indent=2))


if __name__ == "__main__":
    main()
