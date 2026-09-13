#!/usr/bin/env python3
"""Acquire small CC0 context images or register visually assessed candidates."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from packages.media.commons_context import acquire, candidate
from packages.runtime.local_api import LocalAgentClient, LocalApiError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    download = commands.add_parser("acquire")
    download.add_argument("--title", action="append", required=True)
    register = commands.add_parser("register")
    register.add_argument("--receipt", action="append", type=Path, required=True)
    register.add_argument("--visual-note", required=True)
    register.add_argument("--credential-file", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "acquire":
        print(json.dumps({"state": "downloaded_for_visual_assessment", "images": acquire(args.title)}, indent=2))
        return
    if not 1 <= len(args.receipt) <= 3:
        parser.error("Register one to three assessed receipts")
    client = LocalAgentClient(args.credential_file)
    results = []
    for path in args.receipt:
        item = candidate(path, args.visual_note)
        try:
            existing = client.get("/v1/objects/" + item["object_id"])
        except LocalApiError as error:
            if error.status != 404:
                raise
            existing = None
        if existing is not None:
            if existing["payload"] != item["payload"]:
                raise ValueError("Existing asset has different provenance; do not overwrite it")
            record = existing
        else:
            record = client.capture(item, "commons-context:" + item["payload"]["sha256"])
        results.append({"object_id": record["object_id"], "version": record["version"],
                        "created_by": record["created_by"], "review": record["review"],
                        "rights_state": record["payload"]["rights_state"]})
    print(json.dumps({"state": "governed_context_assets_available", "assets": results, "publication_approval": False}, indent=2))


if __name__ == "__main__":
    main()
