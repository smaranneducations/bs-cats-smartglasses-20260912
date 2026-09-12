#!/usr/bin/env python3
"""Read and maintain dotenv files as data without executing their contents."""

from __future__ import annotations

import argparse
import ast
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


ASSIGNMENT = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$")
SAFE_OUTPUT_KEYS = {
    "BIGQUERY_DATASET_SMART_GLASSES",
    "BIGQUERY_LOCATION",
    "BIGQUERY_PROJECT_ID",
    "CLOUD_STORAGE_REGION",
    "FIREBASE_PROJECT_ID",
    "FIRESTORE_DATABASE_ID",
    "FIRESTORE_PROJECT_ID",
    "GCP_PROJECT_ID",
    "GCP_REGION",
    "STORAGE_DEFAULT_BUCKET",
}

FOUNDATION_KEYS = (
    "GCP_PROJECT_ID",
    "GCP_REGION",
    "FIREBASE_PROJECT_ID",
    "FIREBASE_WEB_API_KEY",
    "FIREBASE_AUTH_DOMAIN",
    "FIREBASE_STORAGE_BUCKET",
    "FIREBASE_MESSAGING_SENDER_ID",
    "FIREBASE_APP_ID",
    "FIRESTORE_PROJECT_ID",
    "FIRESTORE_DATABASE_ID",
    "BIGQUERY_PROJECT_ID",
    "BIGQUERY_DATASET_SMART_GLASSES",
    "STORAGE_DEFAULT_BUCKET",
    "APP_SECRET_KEY",
    "JWT_SECRET",
    "GITHUB_OWNER",
    "GITHUB_REPO",
)

YOUTUBE_KEYS = (
    "YOUTUBE_API_CLIENT_ID",
    "YOUTUBE_API_CLIENT_SECRET",
    "YOUTUBE_REFRESH_TOKEN",
    "YOUTUBE_CHANNEL_ID",
)


class EnvConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Entry:
    key: str
    raw_value: str
    line_number: int

    @property
    def value(self) -> str:
        return decode_value(self.raw_value, self.line_number)


@dataclass
class ParsedEnv:
    entries: list[Entry]
    malformed_lines: list[int]

    @property
    def effective(self) -> dict[str, Entry]:
        result: dict[str, Entry] = {}
        for entry in self.entries:
            result[entry.key] = entry
        return result

    @property
    def duplicate_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entry in self.entries:
            counts[entry.key] = counts.get(entry.key, 0) + 1
        return {key: count for key, count in counts.items() if count > 1}


def decode_value(raw_value: str, line_number: int = 0) -> str:
    raw_value = raw_value.strip()
    if not raw_value:
        return ""
    if raw_value[0] in {"'", '"'}:
        if len(raw_value) < 2 or raw_value[-1] != raw_value[0]:
            raise EnvConfigError(f"Unclosed quoted value on line {line_number}.")
        try:
            decoded = ast.literal_eval(raw_value)
        except (SyntaxError, ValueError) as error:
            raise EnvConfigError(f"Invalid quoted value on line {line_number}.") from error
        if not isinstance(decoded, str):
            raise EnvConfigError(f"Quoted value on line {line_number} is not text.")
        return decoded
    return raw_value


def parse_env(path: Path) -> ParsedEnv:
    entries: list[Entry] = []
    malformed: list[int] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = ASSIGNMENT.match(line)
        if not match:
            malformed.append(number)
            continue
        entry = Entry(match.group(1), match.group(2).strip(), number)
        _ = entry.value
        entries.append(entry)
    return ParsedEnv(entries, malformed)


def render_canonical(template_path: Path, values: dict[str, str]) -> str:
    lines: list[str] = []
    template_keys: set[str] = set()
    for line in template_path.read_text(encoding="utf-8").splitlines():
        match = ASSIGNMENT.match(line)
        if not match:
            lines.append(line)
            continue
        key = match.group(1)
        template_keys.add(key)
        lines.append(f"{key}={values.get(key, match.group(2).strip())}")

    extras = sorted(set(values) - template_keys)
    if extras:
        lines.extend(["", "# ------------------------------", "# Additional local values", "# ------------------------------"])
        lines.extend(f"{key}={values[key]}" for key in extras)
    return "\n".join(lines).rstrip() + "\n"


def write_atomic(path: Path, content: str) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def normalize(env_path: Path, template_path: Path, updates: dict[str, str] | None = None) -> tuple[int, int]:
    parsed = parse_env(env_path)
    if parsed.malformed_lines:
        lines = ", ".join(str(number) for number in parsed.malformed_lines)
        raise EnvConfigError(f"Malformed dotenv lines: {lines}.")

    effective_values = {key: entry.raw_value for key, entry in parsed.effective.items()}
    effective_values.update(updates or {})
    content = render_canonical(template_path, effective_values)

    descriptor, candidate_name = tempfile.mkstemp(prefix=".env-candidate.", dir=env_path.parent)
    os.close(descriptor)
    candidate = Path(candidate_name)
    try:
        candidate.write_text(content, encoding="utf-8")
        reparsed = parse_env(candidate)
        if reparsed.malformed_lines or reparsed.duplicate_counts:
            raise EnvConfigError("Canonical dotenv validation failed.")
        actual = {key: entry.raw_value for key, entry in reparsed.effective.items()}
        for key, raw_value in effective_values.items():
            if actual.get(key) != raw_value:
                raise EnvConfigError(f"Canonical dotenv lost the value for {key}.")
    finally:
        candidate.unlink(missing_ok=True)

    duplicates_removed = sum(count - 1 for count in parsed.duplicate_counts.values())
    write_atomic(env_path, content)
    return duplicates_removed, len(effective_values)


def is_configured(value: str) -> bool:
    stripped = value.strip()
    lowered = stripped.lower()
    if not stripped:
        return False
    placeholder_prefixes = ("/path/to/", "replace", "changeme", "your_", "todo", "<")
    return not lowered.startswith(placeholder_prefixes)


def github_authenticated(values: dict[str, Entry]) -> tuple[bool, str]:
    token = values.get("GITHUB_TOKEN")
    if token and is_configured(token.value):
        return True, "local environment token"
    gh = shutil.which("gh")
    if not gh:
        return False, "no token and GitHub CLI unavailable"
    result = subprocess.run(
        [gh, "auth", "status", "--hostname", "github.com"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=10,
    )
    return result.returncode == 0, "GitHub CLI keychain" if result.returncode == 0 else "GitHub CLI is not authenticated"


def command_check(args: argparse.Namespace) -> int:
    parsed = parse_env(args.env)
    if parsed.malformed_lines:
        for number in parsed.malformed_lines:
            print(f"[INVALID] line {number}: not a dotenv assignment")
        return 1
    if parsed.duplicate_counts:
        for key, count in sorted(parsed.duplicate_counts.items()):
            print(f"[DUPLICATE] {key}: {count} assignments")
        return 1

    values = parsed.effective
    requested = list(FOUNDATION_KEYS)
    if args.phase in {"youtube", "all"}:
        requested.extend(YOUTUBE_KEYS)

    missing = False
    for key in requested:
        entry = values.get(key)
        if entry and is_configured(entry.value):
            print(f"[OK] {key}")
        else:
            print(f"[MISSING] {key}")
            missing = True

    github_ok, github_source = github_authenticated(values)
    if github_ok:
        print(f"[OK] GITHUB_AUTH ({github_source})")
    elif args.require_github_auth:
        print(f"[MISSING] GITHUB_AUTH ({github_source})")
        missing = True
    else:
        print(f"[UNVERIFIED] GITHUB_AUTH ({github_source}; keychain access may be unavailable in this sandbox)")

    if args.phase == "youtube":
        print("[INFO] YouTube field status does not validate OAuth scopes, channel ownership, or token freshness.")
    else:
        print("[INFO] Foundation status validates syntax and configured fields, not external permissions or resource existence.")
    return 1 if missing else 0


def command_get(args: argparse.Namespace) -> int:
    if args.key not in SAFE_OUTPUT_KEYS:
        raise EnvConfigError(f"Refusing to print sensitive or unapproved key: {args.key}.")
    parsed = parse_env(args.env)
    entry = parsed.effective.get(args.key)
    if not entry or not is_configured(entry.value):
        raise EnvConfigError(f"Missing required value: {args.key}.")
    print(entry.value)
    return 0


def command_normalize(args: argparse.Namespace) -> int:
    updates: dict[str, str] = {}
    for item in args.set_value:
        if "=" not in item:
            raise EnvConfigError("--set values must use KEY=VALUE.")
        key, raw_value = item.split("=", 1)
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise EnvConfigError(f"Invalid key: {key}.")
        _ = decode_value(raw_value)
        updates[key] = raw_value
    removed, preserved = normalize(args.env, args.template, updates)
    print(f"[OK] Canonical dotenv written with mode 0600; removed {removed} duplicate assignments; preserved {preserved} configured keys.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    normalize_parser = subparsers.add_parser("normalize", help="Canonicalize an env file atomically.")
    normalize_parser.add_argument("--env", type=Path, default=root / ".env")
    normalize_parser.add_argument("--template", type=Path, default=root / ".env.template")
    normalize_parser.add_argument("--set", dest="set_value", action="append", default=[])
    normalize_parser.set_defaults(handler=command_normalize)

    check_parser = subparsers.add_parser("check", help="Report field status without values.")
    check_parser.add_argument("--env", type=Path, default=root / ".env")
    check_parser.add_argument("--phase", choices=("foundation", "youtube", "all"), default="foundation")
    check_parser.add_argument(
        "--require-github-auth",
        action="store_true",
        help="Fail when neither GITHUB_TOKEN nor authenticated gh CLI is available.",
    )
    check_parser.set_defaults(handler=command_check)

    get_parser = subparsers.add_parser("get", help="Print one allow-listed non-secret value.")
    get_parser.add_argument("key")
    get_parser.add_argument("--env", type=Path, default=root / ".env")
    get_parser.set_defaults(handler=command_get)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.handler(args)
    except (EnvConfigError, FileNotFoundError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f"[ERROR] {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
