#!/usr/bin/env python3
"""Fail closed when repository candidates contain private publication classes."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    "", ".css", ".csv", ".env", ".html", ".ini", ".js", ".json",
    ".md", ".py", ".sh", ".sql", ".toml", ".tsv", ".txt", ".yaml", ".yml",
}
LOCAL_ROOTS = {".local", "artifacts", "data", "logs", "tmp"}
ALLOWED_ENV_FILES = {".env.example", ".env.template"}
DENIED_EXACT_NAMES = {
    "credentials.json", "service-account.json", "service_account.json",
    "token.json", "firebase-debug.log", "terraform.tfstate", "terraform.tfstate.backup",
    "id_rsa", "id_ed25519",
}
DENIED_SUFFIXES = {".p12", ".pem", ".pfx"}
PRIVATE_REPORT_PREFIXES = {"exploit-report", "private-vulnerability", "vulnerability-report"}
PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
SERVICE_ACCOUNT = re.compile(r'"type"\s*:\s*"service_account"[\s\S]{0,4000}"private_key"')
RESTRICTED_MARKER = re.compile(
    r"(?:privacy[_ -]?classification|data[_ -]?classification)\s*[\"']?\s*[:=]\s*[\"']?"
    r"(?:restricted|confidential|secret|personal_data)\b",
    re.IGNORECASE,
)


def path_reasons(relative: PurePosixPath) -> list[str]:
    reasons: list[str] = []
    parts = relative.parts
    name = relative.name.lower()
    if parts and parts[0] in LOCAL_ROOTS:
        reasons.append("local or private runtime path")
    if name.startswith(".env") and name not in ALLOWED_ENV_FILES:
        reasons.append("environment file")
    if name in DENIED_EXACT_NAMES or name.endswith("-oauth-token.json"):
        reasons.append("credential or runtime state filename")
    if relative.suffix.lower() in DENIED_SUFFIXES:
        reasons.append("private credential container")
    if any(part.lower() in {"private-security", "security-private"} for part in parts):
        reasons.append("private security report path")
    if any(name.startswith(prefix) for prefix in PRIVATE_REPORT_PREFIXES):
        reasons.append("private vulnerability or exploit report filename")
    return reasons


def content_reasons(text: str) -> list[str]:
    reasons: list[str] = []
    if PRIVATE_KEY.search(text):
        reasons.append("private key material")
    if SERVICE_ACCOUNT.search(text):
        reasons.append("service-account private key payload")
    if RESTRICTED_MARKER.search(text):
        reasons.append("restricted or personal data classification")
    return reasons


def git_paths(mode: str) -> list[Path]:
    commands = {
        "tracked": [["git", "ls-files", "-z"]],
        "staged": [["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"]],
        "worktree": [
            ["git", "ls-files", "-z"],
            ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        ],
    }
    discovered: set[Path] = set()
    for command in commands[mode]:
        result = subprocess.run(command, cwd=ROOT, check=True, capture_output=True)
        for raw in result.stdout.split(b"\0"):
            if raw:
                discovered.add(Path(raw.decode("utf-8", errors="strict")))
    return sorted(discovered)


def inspect(relative: Path) -> list[str]:
    reasons = path_reasons(PurePosixPath(relative.as_posix()))
    absolute = ROOT / relative
    if not absolute.exists() or not absolute.is_file():
        return reasons
    if absolute.is_symlink():
        return reasons + ["symbolic link requires explicit publication review"]
    if relative.suffix.lower() not in TEXT_SUFFIXES and relative.name not in {"Dockerfile", "README"}:
        return reasons
    try:
        text = absolute.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return reasons + ["text candidate is not valid UTF-8"]
    return reasons + content_reasons(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("tracked", "staged", "worktree"), required=True)
    args = parser.parse_args()
    failures: list[tuple[Path, list[str]]] = []
    for relative in git_paths(args.mode):
        reasons = inspect(relative)
        if reasons:
            failures.append((relative, sorted(set(reasons))))
    if failures:
        print("[BLOCKED] Repository publication guard found private candidates:")
        for path, reasons in failures:
            print(f"- {path}: {', '.join(reasons)}")
        print("Move the material to ignored local storage or publish a redacted safe summary.")
        return 1
    print(f"[OK] Repository publication guard passed for {args.mode} candidates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
