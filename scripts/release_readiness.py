#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "AGENTS.md",
    "README.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "governance/personas-and-authority.md",
    "docs/V1_SYSTEM_SPECIFICATION.md",
    "docs/ONTOLOGY_ARCHITECTURE.md",
    "docs/GITHUB_CHANGE_CONTROL.md",
    "docs/V1_RELEASE_READINESS.md",
    "config/project-architecture.json",
    "config/ontology-standards-profile.json",
    "config/revenue-portfolio.json",
    "config/release-policy.json",
    ".github/ISSUE_TEMPLATE/change-request.yml",
    ".github/pull_request_template.md"
]
JSON_FILES = [
    "config/project-architecture.json",
    "config/ontology-standards-profile.json",
    "config/revenue-portfolio.json",
    "config/release-policy.json",
    "config/requirements-traceability.json",
    "firebase.json"
]


def main() -> None:
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    invalid_json = []
    for name in JSON_FILES:
        try:
            json.loads((ROOT / name).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            invalid_json.append({"file": name, "error": str(error)})

    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    safety = {
        "env_ignored": any(line.strip() == ".env" for line in ignore.splitlines()),
        "local_ignored": any(line.strip() in {".local/", ".local"} for line in ignore.splitlines()),
        "github_change_control": (ROOT / ".github/ISSUE_TEMPLATE/change-request.yml").is_file(),
        "production_claim_blocked": True
    }
    candidate_ready = not missing and not invalid_json and all(safety.values())
    report = {
        "schema_version": "release-readiness-report-1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "candidate_version": "1.0.0-rc.1",
        "repository_candidate_ready": candidate_ready,
        "production_ready": False,
        "missing_files": missing,
        "invalid_json": invalid_json,
        "safety_checks": safety,
        "production_blockers": [
            "credential_rotation",
            "cost_reconciliation",
            "durable_firestore_cutover",
            "cloud_run_deployment",
            "firebase_hosting_deployment",
            "approved_rights_cleared_media",
            "provider_publication_receipt",
            "production_metric_return",
            "repository_license_decision"
        ]
    }
    target = ROOT / "docs/V1_RELEASE_READINESS_REPORT.json"
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    raise SystemExit(0 if candidate_ready else 1)


if __name__ == "__main__":
    main()
