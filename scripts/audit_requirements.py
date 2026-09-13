#!/usr/bin/env python3
"""Check the requirements traceability registry without claiming runtime completion."""

import argparse
from collections import Counter
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=ROOT / "config" / "requirements-traceability.json")
    args = parser.parse_args()
    data = json.loads(args.registry.read_text(encoding="utf-8"))
    requirements = data.get("requirements", [])
    allowed = set(data.get("status_definitions", {}))
    ids = [item.get("id") for item in requirements]
    failures = []
    if len(ids) != len(set(ids)):
        failures.append("duplicate requirement IDs")
    for item in requirements:
        missing = [key for key in ("id", "requirement", "source", "status", "implementation_evidence",
                                   "runtime_evidence", "remaining_gap", "next_action") if not item.get(key)]
        if missing:
            failures.append(f"{item.get('id', 'unknown')}: missing {', '.join(missing)}")
        if item.get("status") not in allowed:
            failures.append(f"{item.get('id', 'unknown')}: unsupported status")
        for value in item.get("implementation_evidence", []):
            if not (ROOT / value).exists():
                failures.append(f"{item.get('id', 'unknown')}: evidence path missing: {value}")
    counts = Counter(item["status"] for item in requirements)
    print(json.dumps({"schema_version": data.get("schema_version"), "requirements": len(requirements),
                      "status_counts": dict(sorted(counts.items())), "registry_valid": not failures,
                      "failures": failures}, indent=2))
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
