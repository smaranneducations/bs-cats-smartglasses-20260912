#!/usr/bin/env python3
"""Bounded anonymous HTTP checks, not browser or full release acceptance."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx

ORIGINS = {"https://bs-cats-smartglasses-20260912.web.app", "https://bs-cats-smartglasses-20260912.firebaseapp.com"}
DEFAULT_ORIGIN = "https://bs-cats-smartglasses-20260912.web.app"
MAX_BYTES = 2 * 1024 * 1024
MAX_ASSETS = 32
CHECKS = (("/health", 200), ("/discover", 200), ("/operator", 200),
          ("/v1/session", 401), ("/v1/operator/workflow", 401),
          ("/v1/semantic/ontology", 401), ("/v1/audience/preview", 401),
          ("/v1/media/artifacts", 401), ("/v1/public/feed", 200), ("/v1/public/videos", 200))


class AssetLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and attrs.get("src"):
            self.links.append((attrs["src"], "javascript"))
        if tag == "link" and "stylesheet" in attrs.get("rel", "").lower().split() and attrs.get("href"):
            self.links.append((attrs["href"], "css"))


def fetch(client, url):
    with client.stream("GET", url, follow_redirects=False) as response:
        body = bytearray()
        for chunk in response.iter_bytes():
            if len(body) + len(chunk) > MAX_BYTES:
                raise ValueError("Response exceeds the bounded limit")
            body.extend(chunk)
        mime = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        return response.status_code, mime, bytes(body)


def run_checks(client, origin=DEFAULT_ORIGIN):
    if origin not in ORIGINS:
        raise ValueError("Use a supported project Hosting origin")
    results, assets = [], set()
    external_count = 0
    for path, expected in CHECKS:
        result = {"path": path, "passed": False}
        try:
            status, mime, body = fetch(client, origin + path)
            result["http_status"] = status
            if status != expected:
                raise ValueError("Unexpected HTTP status")
            if path in {"/operator", "/discover"}:
                if mime != "text/html":
                    raise ValueError("Page is not HTML")
                parser = AssetLinks()
                parser.feed(body.decode("utf-8"))
                local_count = 0
                for reference, kind in parser.links:
                    url = urljoin(origin + path, reference)
                    parts = urlsplit(url)
                    if parts.scheme + "://" + parts.netloc != origin or parts.username or parts.password:
                        external_count += 1
                        continue
                    assets.add((url.split("#", 1)[0], kind))
                    local_count += 1
                if not local_count or len(assets) > MAX_ASSETS:
                    raise ValueError("Missing or excessive application assets")
            elif expected == 200:
                if mime != "application/json":
                    raise ValueError("API is not JSON")
                value = json.loads(body)
                if not isinstance(value, dict):
                    raise ValueError("Unexpected API envelope")
                if path == "/health" and (value.get("status") != "healthy" or value.get("object_store") != "firestore"):
                    raise ValueError("Healthy durable object store not reported")
                key = {"/v1/public/feed": "cards", "/v1/public/videos": "videos"}.get(path)
                if key and (value.get("mode") != "public" or not isinstance(value.get(key), list)):
                    raise ValueError("Unexpected public projection")
            result["passed"] = True
        except Exception as error:
            result["failure_type"] = type(error).__name__
        results.append(result)
    if len(assets) <= MAX_ASSETS:
        for url, kind in sorted(assets):
            result = {"path": urlsplit(url).path, "asset_kind": kind, "passed": False}
            try:
                status, mime, body = fetch(client, url)
                result["http_status"] = status
                valid_mime = {"text/css"} if kind == "css" else {"text/javascript", "application/javascript"}
                if status != 200 or mime not in valid_mime or not body.strip():
                    raise ValueError("Missing or invalid static asset")
                if body.lstrip().lower().startswith((b"<!doctype", b"<html")):
                    raise ValueError("HTML fallback returned for a static asset")
                result["passed"] = True
            except Exception as error:
                result["failure_type"] = type(error).__name__
            results.append(result)
    return {
        "schema_version": "hosted-smoke-1", "observed_at": datetime.now(timezone.utc).isoformat(),
        "origin": origin, "scope": "anonymous HTTP boundaries and directly linked first-party assets only",
        "passed": all(item["passed"] for item in results), "checks": results,
        "external_asset_references_not_checked": external_count,
        "not_assessed": ["authenticated browser workflows", "record persistence", "media playback",
                         "external authentication dependencies", "publishing", "backups", "costs", "revenue"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", choices=sorted(ORIGINS), default=DEFAULT_ORIGIN)
    parser.add_argument("--output", type=Path, help="Optional local sanitized JSON receipt")
    args = parser.parse_args()
    with httpx.Client(timeout=15, follow_redirects=False, trust_env=False) as client:
        report = run_checks(client, args.origin)
    serialized = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
