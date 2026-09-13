"""Incremental Google Alerts ingestion through the read-only Gmail API."""

from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import sqlite3
import tempfile
import time
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from packages.contracts.object import ActorType, SourceReference, UniversalObject

API_ROOT = "https://gmail.googleapis.com/gmail/v1/users/me"
TOKEN_URI = "https://oauth2.googleapis.com/token"
TRACKING_KEYS = {"gclid", "fbclid", "mc_cid", "mc_eid", "ref", "source"}
BLOCKED_HOST_SUFFIXES = ("google.com", "googleusercontent.com", "gstatic.com", "youtube.com", "youtu.be")


class GmailAlertError(RuntimeError):
    pass


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag.casefold() == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)


def _post_form(uri: str, values: dict, byte_limit: int = 1024 * 1024) -> dict:
    try:
        with urlopen(Request(uri, data=urlencode(values).encode(), headers={"Content-Type": "application/x-www-form-urlencoded"}), timeout=30) as response:
            raw = response.read(byte_limit + 1)
    except HTTPError as exc:
        raise GmailAlertError(f"Google token refresh failed with HTTP {exc.code}.") from exc
    except (URLError, TimeoutError) as exc:
        raise GmailAlertError("Google token service could not be reached.") from exc
    if not raw or len(raw) > byte_limit:
        raise GmailAlertError("Google token response was empty or too large.")
    return json.loads(raw)


def _atomic_json(path: Path, value: dict) -> None:
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


class GmailClient:
    def __init__(self, token_path: Path, client_id: str, client_secret: str, max_bytes: int):
        self.token_path = Path(token_path)
        self.client_id = client_id
        self.client_secret = client_secret
        self.max_bytes = max_bytes
        self.token = json.loads(self.token_path.read_text(encoding="utf-8"))
        if self.token.get("scope") != "https://www.googleapis.com/auth/gmail.readonly":
            raise GmailAlertError("Stored Gmail token does not have the exact read-only scope.")

    def access_token(self) -> str:
        expires_at = float(self.token.get("obtained_at", 0)) + int(self.token.get("expires_in", 0))
        if self.token.get("access_token") and expires_at - time.time() > 120:
            return self.token["access_token"]
        refreshed = _post_form(TOKEN_URI, {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.token.get("refresh_token", ""),
            "grant_type": "refresh_token",
        })
        if not refreshed.get("access_token"):
            raise GmailAlertError("Google did not return a refreshed Gmail access token.")
        self.token["access_token"] = refreshed["access_token"]
        self.token["expires_in"] = int(refreshed.get("expires_in", 3600))
        self.token["obtained_at"] = time.time()
        _atomic_json(self.token_path, self.token)
        return self.token["access_token"]

    def get(self, suffix: str, parameters: dict) -> dict:
        if not suffix.startswith(("messages", "messages/")):
            raise GmailAlertError("Gmail client attempted an unapproved endpoint.")
        uri = f"{API_ROOT}/{suffix}?{urlencode(parameters)}"
        request = Request(uri, headers={"Authorization": f"Bearer {self.access_token()}", "Accept": "application/json"})
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read(self.max_bytes + 1)
        except HTTPError as exc:
            raise GmailAlertError(f"Gmail API request failed with HTTP {exc.code}.") from exc
        except (URLError, TimeoutError) as exc:
            raise GmailAlertError("Gmail API could not be reached.") from exc
        if not raw or len(raw) > self.max_bytes:
            raise GmailAlertError("Gmail API response was empty or exceeded its byte limit.")
        return json.loads(raw)


def _decode(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    try:
        return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
    except (ValueError, UnicodeError):
        return ""


def _body_parts(payload: dict) -> list[str]:
    result = []
    body = payload.get("body", {}).get("data")
    mime_type = payload.get("mimeType", "")
    if body and mime_type in {"text/plain", "text/html"}:
        result.append(_decode(body))
    for part in payload.get("parts", []) or []:
        result.extend(_body_parts(part))
    return result


def _canonical_link(raw_link: str) -> str | None:
    value = html.unescape(raw_link.strip())
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    host = parsed.hostname.casefold().rstrip(".")
    if host.endswith("google.com") and parsed.path == "/url":
        values = parse_qs(parsed.query)
        target = (values.get("url") or values.get("q") or [""])[0]
        if target:
            parsed = urlsplit(target)
            host = (parsed.hostname or "").casefold().rstrip(".")
    if parsed.scheme not in {"http", "https"} or not host:
        return None
    if any(host == suffix or host.endswith("." + suffix) for suffix in BLOCKED_HOST_SUFFIXES):
        return None
    clean_query = []
    for key, values in parse_qs(parsed.query, keep_blank_values=False).items():
        lowered = key.casefold()
        if lowered.startswith("utm_") or lowered in TRACKING_KEYS:
            continue
        clean_query.extend((key, value) for value in values)
    query = urlencode(sorted(clean_query))
    path = re.sub(r"/+", "/", parsed.path or "/")
    return urlunsplit((parsed.scheme.casefold(), host, path.rstrip("/") or "/", query, ""))


def extract_links(message: dict) -> list[str]:
    links = set()
    for body in _body_parts(message.get("payload", {})):
        parser = LinkParser()
        parser.feed(body)
        candidates = parser.links + re.findall(r"https?://[^\s<>\"']+", body)
        for candidate in candidates:
            normalized = _canonical_link(candidate.rstrip(").,;"))
            if normalized:
                links.add(normalized)
    return sorted(links)


def _connect(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    os.close(descriptor)
    os.chmod(path, 0o600)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS messages(
            message_id TEXT PRIMARY KEY,
            internal_date_ms INTEGER NOT NULL,
            processed_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS articles(
            url_hash TEXT PRIMARY KEY,
            canonical_url TEXT NOT NULL UNIQUE,
            source_host TEXT NOT NULL,
            first_alerted_at TEXT NOT NULL,
            last_alerted_at TEXT NOT NULL,
            alert_count INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS article_alerts(
            url_hash TEXT NOT NULL,
            message_id TEXT NOT NULL,
            alerted_at TEXT NOT NULL,
            PRIMARY KEY(url_hash, message_id),
            FOREIGN KEY(url_hash) REFERENCES articles(url_hash),
            FOREIGN KEY(message_id) REFERENCES messages(message_id)
        );
        CREATE TABLE IF NOT EXISTS runs(
            run_id TEXT PRIMARY KEY,
            completed_at TEXT NOT NULL,
            messages_seen INTEGER NOT NULL,
            messages_new INTEGER NOT NULL,
            links_seen INTEGER NOT NULL,
            articles_new INTEGER NOT NULL
        );
    """)
    return connection


def ingest(client: GmailClient, store, workflow: dict, database_path: Path, query: str, now: datetime | None = None) -> dict:
    observed_at = (now or datetime.now(UTC)).astimezone(UTC)
    run_id = "gmail_alert_" + observed_at.strftime("%Y%m%dT%H%M%SZ")
    source = workflow["source"]
    message_refs = []
    page_token = None
    for _ in range(source["max_pages_per_run"]):
        parameters = {"q": query, "maxResults": min(100, source["max_messages_per_run"])}
        if page_token:
            parameters["pageToken"] = page_token
        response = client.get("messages", parameters)
        message_refs.extend(response.get("messages", []))
        if len(message_refs) >= source["max_messages_per_run"] or not response.get("nextPageToken"):
            break
        page_token = response["nextPageToken"]
    message_refs = message_refs[:source["max_messages_per_run"]]
    connection = _connect(database_path)
    messages_new = links_seen = articles_new = 0
    new_urls = []
    try:
        connection.execute("BEGIN IMMEDIATE")
        for reference in message_refs:
            message_id = str(reference.get("id", ""))
            if not message_id or connection.execute("SELECT 1 FROM messages WHERE message_id=?", (message_id,)).fetchone():
                continue
            message = client.get(f"messages/{message_id}", {
                "format": "full",
                "fields": "id,internalDate,payload(mimeType,headers,body/data,parts)",
            })
            internal_date = int(message.get("internalDate", 0))
            connection.execute("INSERT INTO messages VALUES(?,?,?)", (message_id, internal_date, observed_at.isoformat()))
            messages_new += 1
            for url in extract_links(message):
                links_seen += 1
                url_hash = hashlib.sha256(url.encode()).hexdigest()
                host = urlsplit(url).hostname or ""
                existing = connection.execute("SELECT 1 FROM articles WHERE url_hash=?", (url_hash,)).fetchone()
                if existing:
                    connection.execute("UPDATE articles SET last_alerted_at=?,alert_count=alert_count+1 WHERE url_hash=?",
                                       (observed_at.isoformat(), url_hash))
                else:
                    connection.execute("INSERT INTO articles VALUES(?,?,?,?,?,1)",
                                       (url_hash, url, host, observed_at.isoformat(), observed_at.isoformat()))
                    articles_new += 1
                    new_urls.append(url)
                connection.execute("INSERT OR IGNORE INTO article_alerts VALUES(?,?,?)",
                                   (url_hash, message_id, observed_at.isoformat()))
        connection.execute("INSERT INTO runs VALUES(?,?,?,?,?,?)",
                           (run_id, observed_at.isoformat(), len(message_refs), messages_new, links_seen, articles_new))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    object_id = run_id
    sources = [
        SourceReference(source_id="alert_" + hashlib.sha256(url.encode()).hexdigest()[:24],
                        uri=url, captured_at=observed_at,
                        notes="Discovered through Google Alerts; source admission and factual review remain pending.")
        for url in new_urls[:30]
    ]
    observation = UniversalObject(
        object_id=object_id, object_type="market_observation", domain=workflow["domain"],
        title="Google Alerts industry discovery " + observed_at.date().isoformat(),
        purpose="Record one compact discovery run without creating a human review item for every link.",
        sources=sources,
        payload={
            "summary": f"Processed {messages_new} new matching alert messages and found {articles_new} previously unseen canonical article URLs.",
            "raw_note": "Email and alert snippets are discovery inputs only. Original articles require source-policy, credibility and rights assessment before factual or commercial use.",
        },
        metadata={
            "workflow_id": workflow["workflow_id"], "run_id": run_id,
            "messages_seen": len(message_refs), "messages_new": messages_new,
            "links_seen": links_seen, "articles_new": articles_new,
            "full_email_retained": False, "attachments_retained": False,
            "human_review_required": False,
        },
    )
    store.capture(observation, actor_id="agent:gmail-alert-ingest", actor_type=ActorType.agent,
                  idempotency_key="capture-" + object_id,
                  request_input={"run_id": run_id, "message_ids": sorted(ref.get("id", "") for ref in message_refs)})
    return {
        "status": "completed", "run_id": run_id, "messages_seen": len(message_refs),
        "messages_new": messages_new, "links_seen": links_seen, "articles_new": articles_new,
        "new_article_urls": new_urls[:10], "market_observation_id": object_id,
        "human_approvals_created": 0, "paid_model_calls": 0,
    }
