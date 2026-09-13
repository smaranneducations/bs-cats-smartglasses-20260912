#!/usr/bin/env python3
"""Capture a non-authorizing commerce assessment as an authenticated agent."""

from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.runtime.local_api import LocalAgentClient, LocalApiError, LocalCredentialError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credential-file", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--path-id", action="append")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{8,100}", args.run_id):
        parser.error("run-id must be a bounded task identifier")
    try:
        client = LocalAgentClient(args.credential_file)
        suffix = "?" + urlencode({"path_id": args.path_id}, doseq=True) if args.path_id else ""
        report = client.get("/v1/intelligence/commerce" + suffix)
        payload = report["assessment"]
        object_id = "commerce_assessment_" + hashlib.sha256(args.run_id.encode()).hexdigest()[:32]
        try:
            existing = client.get("/v1/objects/" + object_id)
        except LocalApiError as error:
            if error.status != 404:
                raise
            existing = None
        if existing is not None:
            if existing["payload"]["input_fingerprint"] != payload["input_fingerprint"] or datetime.fromisoformat(existing["payload"]["valid_until"].replace("Z", "+00:00")) <= datetime.now(timezone.utc):
                raise ValueError("Run identifier belongs to changed or expired inputs; use a new bounded task run")
            print(json.dumps({"state": "existing_assessment_reused", "object_id": object_id, "version": existing["version"], "review": existing["review"]["state"], "publication_authorized": False}))
            return
        for identifier, version in payload["input_versions"].items():
            if client.get("/v1/objects/" + identifier)["version"] != version:
                raise ValueError("An input changed during assessment; no result was captured")
        result = client.capture({"object_id": object_id, "object_type": "commerce_assessment", "title": "Commercial readiness: evidence before revenue assumptions", "purpose": "Inspect version-bound commercial gates and prepare the smallest necessary human decisions without granting permissions.", "parent_ids": list(payload["input_versions"]), "payload": payload, "sources": report["sources"], "metadata": {"source_versions": payload["input_versions"], "policy_version": payload["policy_version"], "source": "deterministic_commerce_adviser", "external_provider_calls": 0, "permission_expansion": False}}, args.run_id)
        print(json.dumps({"state": "assessment_captured", "object_id": result["object_id"], "version": result["version"], "created_by": result["created_by"], "review": result["review"]["state"], "path_stages": [{"path_id": path["path_id"], "stage": path["stage"]} for path in payload["paths"]], "publication_authorized": False, "review_url": "http://127.0.0.1:8766/commerce"}, indent=2))
    except (LocalApiError, LocalCredentialError, OSError, ValueError) as error:
        print(json.dumps({"state": "not_completed", "error": str(error), "automatic_retry": False}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
