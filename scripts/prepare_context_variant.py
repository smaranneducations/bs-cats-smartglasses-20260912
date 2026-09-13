#!/usr/bin/env python3
"""Create a separately versioned recipe using documented context images."""

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.runtime.local_api import LocalAgentClient, LocalApiError


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe_id")
    parser.add_argument("--replace", action="append", required=True, metavar="OLD_ASSET=NEW_ASSET")
    parser.add_argument("--credential-file", required=True, type=Path)
    args = parser.parse_args()
    replacements = dict(item.split("=", 1) for item in args.replace)
    if not 1 <= len(replacements) <= 3 or len(replacements) != len(args.replace):
        parser.error("Supply one to three unique image replacements")
    client = LocalAgentClient(args.credential_file)
    source = client.get("/v1/objects/" + args.recipe_id)
    if source["object_type"] != "render_recipe":
        raise ValueError("The source must be a governed render recipe")
    payload = copy.deepcopy(source["payload"])
    original_hash = canonical_hash(payload)
    for old_id, new_id in replacements.items():
        if old_id not in payload["assets"] or payload["assets"][old_id]["asset_kind"] != "image":
            raise ValueError("Only existing image slots can be replaced")
        new = client.get("/v1/objects/" + new_id)
        media = new["payload"]
        if (new["object_type"] != "media_asset" or media.get("asset_kind") != "image"
                or media.get("rights_state") != "documented" or media.get("commercial_use_allowed") is not True
                or new.get("metadata", {}).get("representation_detail") != "context_photograph"
                or new["review"].get("state") == "rejected"):
            raise ValueError("Replacement requires a documented, non-rejected context image")
        del payload["assets"][old_id]
        del payload["input_versions"][old_id]
        payload["assets"][new_id] = media
        payload["input_versions"][new_id] = new["version"]
    for beat in payload["beats"]:
        if beat["image_asset_id"] in replacements:
            beat["image_asset_id"] = replacements[beat["image_asset_id"]]
            beat["crop"] = [0.0, 0.0, 1.0, 1.0]
    payload["summary"] = "Private comparison variant with creator-attributed CC0 context photographs, music and unchanged factual cells."
    payload["adaptation_reason"] = "Replace undocumented legacy images with traceable context photographs. These are not product photos, camera samples or evidence of screen quality. Preserve the earlier creative variant and all factual caveats."
    payload_hash = canonical_hash(payload)
    object_id = "recipe_" + payload_hash[:32]
    metadata = {key: (payload_hash if value == original_hash else value) for key, value in source["metadata"].items()}
    metadata.update({"recipe_sha256": payload_hash, "context_variant_of": source["object_id"],
                     "source_versions": {**payload["input_versions"], source["object_id"]: source["version"]},
                     "publication_permission": False})
    item = {"object_id": object_id, "object_type": "render_recipe",
            "title": "Licensed-context comparison video recipe", "purpose": source["purpose"],
            "sources": source["sources"], "parent_ids": list(dict.fromkeys([source["object_id"], *payload["input_versions"]])),
            "payload": payload, "metadata": metadata}
    try:
        existing = client.get("/v1/objects/" + object_id)
    except LocalApiError as error:
        if error.status != 404:
            raise
        existing = None
    if existing is not None and existing["payload"] != payload:
        raise ValueError("Recipe identity collision; no existing record was overwritten")
    record = existing or client.capture(item, "context-variant:" + payload_hash)
    print(json.dumps({"recipe_id": record["object_id"], "version": record["version"],
                      "created_by": record["created_by"], "review": record["review"],
                      "publication_allowed": False}, indent=2))


if __name__ == "__main__":
    main()
