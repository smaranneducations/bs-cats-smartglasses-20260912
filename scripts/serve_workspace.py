#!/usr/bin/env python3
"""Start the private operator workspace with only its authentication configuration."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    import argparse
    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    os.environ["ENVIRONMENT"] = "local"
    os.environ["ALLOW_LOCAL_OPERATOR"] = "1"
    os.environ["ALLOWED_HOSTS"] = "127.0.0.1,localhost,::1"
    os.environ.setdefault("OBJECT_STORE_PATH", str(ROOT / ".local/object-events.jsonl"))
    from scripts.env_config import EnvConfigError, parse_env
    auth_keys = {
        "FIREBASE_WEB_API_KEY", "FIREBASE_AUTH_DOMAIN", "FIREBASE_PROJECT_ID",
        "FIREBASE_WEB_APP_ID", "ADMIN_AUTH_REQUIRED", "ADMIN_ALLOWLIST_PATH",
    }
    env_path = ROOT / ".env"
    if env_path.exists():
        parsed = parse_env(env_path)
        if parsed.malformed_lines:
            lines = ", ".join(str(line) for line in parsed.malformed_lines)
            raise EnvConfigError(f"Malformed dotenv lines prevent safe auth startup: {lines}")
        for key, entry in parsed.effective.items():
            if key in auth_keys and entry.value:
                os.environ[key] = entry.value
    uvicorn.run("services.api.src.main:app", host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
