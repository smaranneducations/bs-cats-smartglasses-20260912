#!/usr/bin/env python3
"""Obtain a read-only Gmail OAuth token without printing credentials."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import sys
import tempfile
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.env_config import EnvConfigError, is_configured, parse_env

AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
DEFAULT_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


class SetupError(RuntimeError):
    pass


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(json.dumps(value, indent=2, ensure_ascii=True).encode() + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def configured(values, primary: str, fallback: str | None = None) -> str:
    for key in (primary, fallback):
        if key:
            entry = values.get(key)
            if entry and is_configured(entry.value):
                return entry.value
    raise SetupError(f"Configure {primary} in the local .env.")


def exchange_code(client_id: str, client_secret: str, redirect_uri: str, code: str, verifier: str) -> dict:
    body = urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "code_verifier": verifier,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }).encode()
    try:
        with urlopen(Request(TOKEN_URI, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}), timeout=30) as response:
            raw = response.read(1024 * 1024 + 1)
    except HTTPError as exc:
        raise SetupError(f"Google rejected the OAuth token exchange with HTTP {exc.code}.") from exc
    except (URLError, TimeoutError) as exc:
        raise SetupError("Google OAuth token exchange could not be reached.") from exc
    if not raw or len(raw) > 1024 * 1024:
        raise SetupError("Google OAuth token response was empty or too large.")
    payload = json.loads(raw)
    if not payload.get("access_token") or not payload.get("refresh_token"):
        raise SetupError("Google did not return an offline refresh token; revoke the prior grant and retry.")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=ROOT / ".env")
    args = parser.parse_args()
    try:
        parsed = parse_env(args.env)
        if parsed.malformed_lines or parsed.duplicate_counts:
            raise SetupError("Normalize the local .env before OAuth setup.")
        values = parsed.effective
        client_id = configured(values, "GMAIL_OAUTH_CLIENT_ID", "GDRIVE_OAUTH_CLIENT_ID")
        client_secret = configured(values, "GMAIL_OAUTH_CLIENT_SECRET", "GDRIVE_OAUTH_CLIENT_SECRET")
        redirect_uri = configured(values, "GMAIL_OAUTH_REDIRECT_URI", "GDRIVE_OAUTH_REDIRECT_URI")
        scope_entry = values.get("GMAIL_OAUTH_SCOPE")
        scope = scope_entry.value if scope_entry and is_configured(scope_entry.value) else DEFAULT_SCOPE
        if scope != DEFAULT_SCOPE:
            raise SetupError("Gmail setup is restricted to the read-only OAuth scope.")
        token_entry = values.get("GMAIL_OAUTH_TOKEN_PATH")
        token_path = Path(token_entry.value) if token_entry and is_configured(token_entry.value) else Path(".local/gmail-alerts/oauth-token.json")
        token_path = token_path if token_path.is_absolute() else ROOT / token_path
        parsed_redirect = urlparse(redirect_uri)
        if parsed_redirect.scheme != "http" or parsed_redirect.hostname not in {"127.0.0.1", "localhost"} or not parsed_redirect.port:
            raise SetupError("Gmail OAuth redirect must be an explicit localhost HTTP URI with a port.")
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        result = {}

        class Callback(BaseHTTPRequestHandler):
            def do_GET(self):
                query = parse_qs(urlparse(self.path).query)
                if query.get("state", [""])[0] != state:
                    result["error"] = "OAuth state did not match."
                    status = 400
                elif query.get("error"):
                    result["error"] = "Google consent was declined."
                    status = 400
                elif not query.get("code"):
                    result["error"] = "Google did not return an authorization code."
                    status = 400
                else:
                    result["code"] = query["code"][0]
                    status = 200
                message = b"<html><body><h1>Gmail connection received</h1><p>You may return to Codex.</p></body></html>"
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(message)))
                self.end_headers()
                self.wfile.write(message)

            def log_message(self, *_args):
                return

        server = HTTPServer((parsed_redirect.hostname, parsed_redirect.port), Callback)
        server.timeout = 300
        authorization_url = AUTH_URI + "?" + urlencode({
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope,
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "false",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        })
        print("[ACTION] Approve read-only Gmail access in the Google window. No email-send permission is requested.")
        if not webbrowser.open(authorization_url, new=2):
            print("[ACTION] Open the Google OAuth URL shown by your terminal.")
            print(authorization_url)
        server.handle_request()
        server.server_close()
        if result.get("error"):
            raise SetupError(result["error"])
        if not result.get("code"):
            raise SetupError("OAuth consent timed out without a callback.")
        token = exchange_code(client_id, client_secret, redirect_uri, result["code"], verifier)
        granted_scopes = set(token.get("scope", scope).split())
        if granted_scopes != {DEFAULT_SCOPE}:
            raise SetupError(
                "Google returned a combined OAuth grant. Use a Gmail-specific OAuth client or revoke the prior combined grant, then retry."
            )
        atomic_json(token_path, {
            "schema_version": "gmail-oauth-token-1",
            "access_token": token["access_token"],
            "refresh_token": token["refresh_token"],
            "expires_in": int(token.get("expires_in", 3600)),
            "obtained_at": __import__("time").time(),
            "scope": DEFAULT_SCOPE,
            "token_type": token.get("token_type", "Bearer"),
            "token_uri": TOKEN_URI,
        })
        print(f"[OK] Read-only Gmail OAuth token stored locally at {token_path}.")
        return 0
    except (SetupError, EnvConfigError, FileNotFoundError, json.JSONDecodeError, OSError, ValueError) as exc:
        print(f"[ERROR] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
