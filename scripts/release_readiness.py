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


def assess_repository(root=ROOT):
    """Assess repository structure, never infer deployment from file presence."""
    missing = [name for name in REQUIRED if not (root / name).is_file()]
    invalid_json = []
    for name in JSON_FILES:
        try:
            json.loads((root / name).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            invalid_json.append({"file": name, "error": str(error)})

    ignore_path = root / ".gitignore"
    ignore = ignore_path.read_text(encoding="utf-8") if ignore_path.is_file() else ""
    safety = {
        "env_ignored": any(line.strip() == ".env" for line in ignore.splitlines()),
        "local_ignored": any(line.strip() in {".local/", ".local"} for line in ignore.splitlines()),
        "github_change_control": (root / ".github/ISSUE_TEMPLATE/change-request.yml").is_file(),
        "production_claim_blocked": True
    }
    candidate_ready = not missing and not invalid_json and all(safety.values())
    return {
        "schema_version": "release-readiness-report-2",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "assessment_scope": "repository file presence, JSON syntax and ignore declarations only",
        "candidate_version": "1.0.0-rc.1",
        "repository_candidate_ready": candidate_ready,
        "production_ready": False,
        "production_readiness_assessed": False,
        "production_status": "not_assessed_by_this_check",
        "missing_files": missing,
        "invalid_json": invalid_json,
        "safety_checks": safety,
        "production_blockers": ["production_admission_not_assessed_by_repository_check"],
        "next_checks": [
            "Run scripts/check_hosted_app.py for bounded live HTTP and first-party asset checks.",
            "Use authenticated browser acceptance for login, persistence and media playback.",
            "Review deployment, backup, security, cost, rights and exact-publication evidence separately."
        ],
        "latest_acceptance_record": "docs/acceptance/2026-09-14-hosted-workflows.md"
    }


def main() -> None:
    report = assess_repository()
    target = ROOT / "docs/V1_RELEASE_READINESS_REPORT.json"
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    raise SystemExit(0 if report["repository_candidate_ready"] else 1)


if __name__ == "__main__":
    main()
