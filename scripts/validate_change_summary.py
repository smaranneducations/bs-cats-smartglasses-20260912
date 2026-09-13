#!/usr/bin/env python3
"""Validate the compact four-section pull-request review card."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


HEADING = re.compile(r"^##\s+(.+?)\s*$")
ALIASES = {
    "problem_statement": {"problem statement"},
    "issue_or_change_identified": {
        "issue identified",
        "change identified",
        "issue/change identified",
        "issue or change identified",
    },
    "root_cause_or_opportunity_rationale": {
        "root cause",
        "root cause or opportunity",
        "root cause or opportunity rationale",
    },
    "key_steps": {"key steps", "key steps to fix"},
}


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower().rstrip(":."))


def parse_sections(body: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    active: str | None = None
    alias_to_key = {alias: key for key, aliases in ALIASES.items() for alias in aliases}
    in_comment = False
    for raw in body.splitlines():
        line = raw.strip()
        if "<!--" in line:
            in_comment = True
        if not in_comment:
            match = HEADING.match(line)
            if match:
                active = alias_to_key.get(normalized(match.group(1)))
                if active is not None:
                    sections.setdefault(active, [])
                continue
            if active is not None and line:
                sections[active].append(line)
        if "-->" in line:
            in_comment = False
    return sections


def validate(body: str, maximum_lines: int = 2) -> list[str]:
    sections = parse_sections(body)
    errors: list[str] = []
    for key in ALIASES:
        lines = sections.get(key, [])
        if not lines:
            errors.append(f"missing or empty section: {key}")
        elif len(lines) > maximum_lines:
            errors.append(f"section exceeds {maximum_lines} non-empty lines: {key}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", type=Path, required=True)
    args = parser.parse_args()
    event = json.loads(args.event.read_text(encoding="utf-8"))
    pull_request = event.get("pull_request")
    if pull_request is None:
        print("[OK] Change-summary validation not applicable to this event.")
        return 0
    errors = validate(pull_request.get("body") or "")
    if errors:
        print("[BLOCKED] Pull request summary does not satisfy the compact review contract:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[OK] Pull request summary satisfies the compact review contract.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
