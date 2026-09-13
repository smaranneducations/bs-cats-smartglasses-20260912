#!/usr/bin/env python3
"""Local preview with an expiring, private agent credential and human UI access."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import secrets
import stat
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.runtime.local_api import ACCESS_ROOT, BASE_URL, PROJECT_ID


def main() -> None:
    if os.getenv("API_AGENT_TOKEN"):
        raise SystemExit("An agent credential is already configured; refusing to replace it implicitly.")
    try:
        ACCESS_ROOT.mkdir(mode=0o700)
    except FileExistsError:
        pass
    details = ACCESS_ROOT.lstat()
    if not stat.S_ISDIR(details.st_mode) or details.st_uid != os.getuid() or stat.S_IMODE(details.st_mode) != 0o700:
        raise SystemExit("The local credential directory must be a private user-owned directory.")
    session = Path(tempfile.mkdtemp(prefix="session-", dir=ACCESS_ROOT))
    credential = session / "agent.json"
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=8)
    descriptor = os.open(credential, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        json.dump({"format_version": 1, "project_id": PROJECT_ID, "base_url": BASE_URL, "agent_token": token, "created_at": now.isoformat(), "expires_at": expires.isoformat()}, output)
    os.environ["API_AGENT_TOKEN"] = token
    os.environ["ENVIRONMENT"] = "local"
    os.environ["ALLOW_LOCAL_OPERATOR"] = "1"

    def retire() -> None:
        if os.environ.get("API_AGENT_TOKEN") == token:
            os.environ.pop("API_AGENT_TOKEN", None)
        try:
            credential.unlink(missing_ok=True)
            session.rmdir()
        except OSError:
            pass

    expiry_timer = threading.Timer(8 * 60 * 60, retire)
    expiry_timer.daemon = True
    expiry_timer.start()
    print(json.dumps({"state": "local_agent_access_prepared", "credential_file": str(credential), "expires_at": expires.isoformat(), "agent_can_review": False, "cloud_credentials_copied": False}), flush=True)
    try:
        import uvicorn
        uvicorn.run("services.api.src.main:app", host="127.0.0.1", port=8766, access_log=False)
    finally:
        expiry_timer.cancel()
        retire()


if __name__ == "__main__":
    main()
