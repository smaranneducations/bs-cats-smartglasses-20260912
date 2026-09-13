#!/usr/bin/env python3
"""Capture exact-artifact prerequisite evidence without approving publication."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.runtime.local_api import LocalAgentClient, LocalApiError, LocalCredentialError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_id")
    parser.add_argument("--credential-file", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{3,128}", args.artifact_id) or not re.fullmatch(r"[A-Za-z0-9_.:-]{8,100}", args.run_id):
        parser.error("A bounded artifact ID and task run ID are required")
    try:
        client = LocalAgentClient(args.credential_file)
        report = client.get(f"/v1/media/artifacts/{args.artifact_id}/release-review")
        packet = report["packet"]
        object_id = "release_review_" + hashlib.sha256(args.run_id.encode()).hexdigest()[:32]
        try:
            existing = client.get("/v1/objects/" + object_id)
        except LocalApiError as error:
            if error.status != 404:
                raise
            existing = None
        if existing is not None:
            if existing["payload"]["input_fingerprint"] != packet["input_fingerprint"]:
                raise ValueError("The existing run belongs to different checks or inputs; use a new bounded task run")
            print(json.dumps({"state": "existing_packet_matches_current_checks", "object_id": object_id, "version": existing["version"], "permission_granted": False}))
            return
        for identifier, version in packet["input_versions"].items():
            if client.get("/v1/objects/" + identifier)["version"] != version:
                raise ValueError("An input changed before capture; no packet was written")
        result = client.capture({"object_id": object_id, "object_type": "release_review_packet", "title": "Exact video review packet: comparison preview", "purpose": "Review the actual video bytes, metadata, lineage, technical checks and separate unresolved permission gates.", "payload": packet, "sources": report["sources"], "parent_ids": list(packet["input_versions"]), "metadata": {"source_versions": packet["input_versions"], "publication_permission": False, "external_provider_calls": 0}}, args.run_id)
        print(json.dumps({"state": "release_packet_captured", "object_id": result["object_id"], "version": result["version"], "created_by": result["created_by"], "review": result["review"]["state"], "prerequisites_satisfied": packet["prerequisites_satisfied"], "check_states": {item["check_id"]: item["state"] for item in packet["checks"]}, "permission_granted": False}, indent=2))
    except (LocalApiError, LocalCredentialError, OSError, ValueError) as error:
        print(json.dumps({"state": "not_completed", "error": str(error), "automatic_retry": False}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
