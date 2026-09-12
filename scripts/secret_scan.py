#!/usr/bin/env python3
"""Scan public-repository candidates for likely credentials without printing them."""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


MAX_FILE_BYTES = 5 * 1024 * 1024
SENSITIVE_FILENAMES = re.compile(
    r"(^|/)(\.env($|\.)|.*(?:service[-_]?account|credentials?|private[-_]?key).*(?:\.json|\.pem|\.p12|\.pfx)$)",
    re.IGNORECASE,
)
CONTENT_RULES = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "openai-key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}"),
    "google-oauth-secret": re.compile(r"\bGOCSPX-[A-Za-z0-9_-]{20,}"),
    "google-api-key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"),
    "github-token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    "discord-token": re.compile(r"\b(?:MTA|MTI|MTM|MTQ|MTU|MTY|MTc|MTg|MTk)[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{20,}"),
}
CONFIG_SUFFIXES = {".env", ".ini", ".json", ".toml", ".yaml", ".yml"}
ASSIGNMENT = re.compile(
    r"(?i)^\s*[\"']?([A-Z0-9_]+)[\"']?\s*[:=]\s*[\"']?([^\s\"',}]+)"
)
SECRET_KEY_SUFFIXES = (
    "API_KEY",
    "ACCESS_TOKEN",
    "REFRESH_TOKEN",
    "CLIENT_SECRET",
    "BOT_TOKEN",
    "PASSWORD",
    "SMTP_PASS",
    "PRIVATE_KEY",
)
PUBLIC_ENV_FILES = {".env.example", ".env.template"}
PLACEHOLDERS = ("null", "none", "false", "true", "changeme", "replace_me", "todo", "example", "your_")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str


def looks_like_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    if not lowered:
        return True
    return any(lowered == item or lowered.startswith(item) for item in PLACEHOLDERS)


def scan_text(path: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    suffix = Path(path).suffix.lower()
    for number, line in enumerate(text.splitlines(), start=1):
        for rule, pattern in CONTENT_RULES.items():
            if pattern.search(line):
                findings.append(Finding(path, number, rule))
        if suffix in CONFIG_SUFFIXES or Path(path).name.startswith(".env"):
            match = ASSIGNMENT.search(line)
            if (
                match
                and match.group(1).upper().endswith(SECRET_KEY_SUFFIXES)
                and not looks_like_placeholder(match.group(2))
            ):
                findings.append(Finding(path, number, "assigned-secret"))
    return findings


def git_paths(root: Path, mode: str) -> list[str]:
    if mode == "staged":
        command = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"]
    elif mode == "tracked":
        command = ["git", "ls-files", "-z"]
    else:
        command = ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
    output = subprocess.check_output(command, cwd=root)
    return sorted({part.decode("utf-8") for part in output.split(b"\0") if part})


def file_bytes(root: Path, path: str, mode: str) -> bytes:
    if mode == "staged":
        return subprocess.check_output(["git", "show", f":{path}"], cwd=root)
    return (root / path).read_bytes()


def scan_repository(root: Path, mode: str) -> list[Finding]:
    findings: list[Finding] = []
    for path in git_paths(root, mode):
        if SENSITIVE_FILENAMES.search(path) and Path(path).name not in PUBLIC_ENV_FILES:
            findings.append(Finding(path, 0, "sensitive-filename"))
            continue
        try:
            data = file_bytes(root, path, mode)
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
        if len(data) > MAX_FILE_BYTES or b"\0" in data:
            continue
        findings.extend(scan_text(path, data.decode("utf-8", errors="replace")))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--mode", choices=("worktree", "staged", "tracked"), default="worktree")
    args = parser.parse_args()
    findings = scan_repository(args.root.resolve(), args.mode)
    if findings:
        for finding in findings:
            location = finding.path if finding.line == 0 else f"{finding.path}:{finding.line}"
            print(f"[SECRET-RISK] {location} ({finding.rule})")
        print(f"[ERROR] Found {len(findings)} potential secret exposures. Values were not printed.")
        return 1
    print(f"[OK] No likely credentials found in {args.mode} repository candidates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
