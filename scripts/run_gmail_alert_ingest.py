#!/usr/bin/env python3
"""Ingest SmartGlasses Google Alerts through the read-only Gmail API."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.intelligence.gmail_alerts import GmailAlertError, GmailClient, ingest
from scripts.env_config import EnvConfigError, is_configured, parse_env
from services.api.src.main import get_store


def selected(values, primary: str, fallback: str | None = None, default: str | None = None) -> str:
    for key in (primary, fallback):
        if key:
            entry = values.get(key)
            if entry and is_configured(entry.value):
                return entry.value
    if default is not None:
        return default
    raise GmailAlertError(f"Configure {primary} in the local .env.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=ROOT / ".env")
    parser.add_argument("--config", type=Path, default=ROOT / "config/workflows/gmail-alert-intelligence.json")
    args = parser.parse_args()
    try:
        parsed = parse_env(args.env)
        if parsed.malformed_lines or parsed.duplicate_counts:
            raise GmailAlertError("Normalize the local .env before Gmail API access.")
        values = parsed.effective
        workflow = json.loads(args.config.read_text(encoding="utf-8"))
        client_id = selected(values, "GMAIL_OAUTH_CLIENT_ID", "GDRIVE_OAUTH_CLIENT_ID")
        client_secret = selected(values, "GMAIL_OAUTH_CLIENT_SECRET", "GDRIVE_OAUTH_CLIENT_SECRET")
        token_value = selected(values, "GMAIL_OAUTH_TOKEN_PATH", default=workflow["storage"]["oauth_token"])
        token_path = Path(token_value)
        token_path = token_path if token_path.is_absolute() else ROOT / token_path
        database_path = ROOT / workflow["storage"]["database"]
        query = selected(values, "GMAIL_ALERT_QUERY", default=workflow["source"]["query"])
        client = GmailClient(token_path, client_id, client_secret, workflow["source"]["max_message_bytes"])
        result = ingest(client, get_store(), workflow, database_path, query)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    except (GmailAlertError, EnvConfigError, FileNotFoundError, json.JSONDecodeError, OSError, ValueError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
