"""Authenticated local agent access, without a human-role fallback."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

ACCESS_ROOT = Path("/private/tmp") / f"smartglasses-local-access-{os.getuid()}"
BASE_URL = "http://127.0.0.1:8766"
PROJECT_ID = "bs-cats-smartglasses-20260912"


class LocalApiError(RuntimeError):
    def __init__(self, status: int | None, message: str = "Local agent API request did not complete"):
        self.status = status
        super().__init__(message if status is None else f"{message}: HTTP {status}")


class LocalCredentialError(RuntimeError):
    pass


def load_local_credential(path: Path) -> dict[str, Any]:
    """Read a private temporary credential into memory; never return it to logs."""
    root = ACCESS_ROOT.resolve()
    if path.name != "agent.json" or not path.parent.name.startswith("session-") or path.parent.parent.resolve() != root:
        raise LocalCredentialError("Use a scoped launcher credential outside the project and synced folders")
    for directory in (ACCESS_ROOT, path.parent):
        details = directory.lstat()
        if not stat.S_ISDIR(details.st_mode) or details.st_uid != os.getuid() or stat.S_IMODE(details.st_mode) != 0o700:
            raise LocalCredentialError("Local credential directories must be private and owned by this user")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        details = os.fstat(descriptor)
        if not stat.S_ISREG(details.st_mode) or details.st_uid != os.getuid() or stat.S_IMODE(details.st_mode) != 0o600 or details.st_size > 16384:
            raise LocalCredentialError("Local credential file is not a private regular file")
        with os.fdopen(descriptor, "r", encoding="utf-8", closefd=False) as source:
            record = json.load(source)
    finally:
        os.close(descriptor)
    if record.get("format_version") != 1 or record.get("project_id") != PROJECT_ID or record.get("base_url") != BASE_URL:
        raise LocalCredentialError("Local credential does not belong to this application")
    token = record.get("agent_token")
    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", token):
        raise LocalCredentialError("Local agent credential has an invalid format")
    try:
        expiry = datetime.fromisoformat(record["expires_at"].replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError):
        raise LocalCredentialError("Local agent credential has no valid expiry") from None
    if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
        raise LocalCredentialError("Local agent credential has expired")
    return record


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class LocalAgentClient:
    def __init__(self, credential_file: Path):
        record = load_local_credential(credential_file)
        self._token = record["agent_token"]
        self._expiry = datetime.fromisoformat(record["expires_at"].replace("Z", "+00:00"))
        self._opener = build_opener(ProxyHandler({}), _NoRedirect())
        identity = self.get("/v1/session")
        if identity.get("actor_type") != "agent" or identity.get("role") != "editor" or identity.get("mode") != "token":
            raise LocalCredentialError("Authenticated agent editor identity is required; no human fallback is permitted")
        self.actor_id = identity["actor_id"]

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None, key: str | None = None) -> Any:
        if not path.startswith("/v1/") or ".." in path or "//" in path or len(path) > 2000:
            raise ValueError("Only bounded local application paths are permitted")
        if datetime.now(timezone.utc) >= self._expiry:
            raise LocalCredentialError("Local agent credential has expired")
        if method == "POST":
            if path != "/v1/objects" and not re.fullmatch(r"/v1/objects/[A-Za-z0-9_.:-]{3,128}/curate", path):
                raise ValueError("Agent client cannot review, publish or invoke arbitrary writes")
            if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_.:/-]{8,160}", key):
                raise ValueError("An explicit bounded idempotency key is required")
        elif method != "GET":
            raise ValueError("Unsupported local agent method")
        data = None if body is None else json.dumps(body, allow_nan=False).encode()
        if data is not None and len(data) > 524288:
            raise ValueError("Local agent request exceeds the application's byte limit")
        headers = {"X-BS-CATS-Key": self._token, "Accept": "application/json"}
        if data is not None:
            headers.update({"Content-Type": "application/json", "X-Workspace-Action": "1", "Idempotency-Key": key})
        request = Request(BASE_URL + path, data=data, method=method, headers=headers)
        try:
            with self._opener.open(request, timeout=12) as response:
                raw = response.read(2 * 1024 * 1024 + 1)
        except HTTPError as error:
            status = error.code
            error.close()
            raise LocalApiError(status) from None
        except (URLError, TimeoutError, OSError):
            raise LocalApiError(None) from None
        if len(raw) > 2 * 1024 * 1024:
            raise LocalApiError(None, "Local API response exceeds its byte limit")
        try:
            return json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            raise LocalApiError(None, "Local API returned invalid JSON") from None

    def get(self, path: str) -> Any:
        return self._request("GET", path)

    def capture(self, values: dict[str, Any], key: str) -> dict[str, Any]:
        values = dict(values)
        identity = {"actor_id": self.actor_id, "actor_type": "agent", "created_by": self.actor_id}
        for field, value in identity.items():
            if values.get(field) is not None and values[field] != value:
                raise ValueError("Capture identity must match the authenticated agent")
            values[field] = value
        return self._request("POST", "/v1/objects", values, key)

    def curate(self, object_id: str, patch: dict[str, Any], expected_version: int, key: str) -> dict[str, Any]:
        if type(expected_version) is not int or expected_version < 1:
            raise ValueError("Curation requires an exact positive object version")
        return self._request("POST", f"/v1/objects/{object_id}/curate", {"patch": patch, "expected_version": expected_version, "actor_id": self.actor_id, "actor_type": "agent"}, key)
