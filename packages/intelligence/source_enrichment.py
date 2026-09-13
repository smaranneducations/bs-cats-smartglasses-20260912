"""Budgeted, provider-neutral source discovery for unresolved knowledge fields.

Search output is discovery metadata only. This module intentionally does not
turn snippets into assertions or retain full provider responses.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree


class EnrichmentError(RuntimeError):
    pass


class ProviderError(EnrichmentError):
    pass


class AdmissionError(EnrichmentError):
    pass


@dataclass(frozen=True)
class Discovery:
    provider_id: str
    url: str
    title: str = ""
    published_at: str | None = None


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_url(value: str) -> str | None:
    try:
        parsed = urlsplit(value.strip())
    except ValueError:
        return None
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
        return None
    host = parsed.hostname.casefold().rstrip(".")
    path = re.sub(r"/+", "/", parsed.path or "/")
    return urlunsplit((parsed.scheme.casefold(), host, path.rstrip("/") or "/", parsed.query, ""))


def _request_json(url: str, *, timeout: int, maximum_bytes: int, headers=None, body=None):
    request_headers = {"Accept": "application/json", "User-Agent": "BS-CATS-Source-Enrichment/1.0"}
    request_headers.update(headers or {})
    payload = None
    if body is not None:
        payload = json.dumps(body, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    try:
        with urlopen(Request(url, data=payload, headers=request_headers), timeout=timeout) as response:
            raw = response.read(maximum_bytes + 1)
    except HTTPError as exc:
        raise ProviderError(f"Provider returned HTTP {exc.code}.") from exc
    except (URLError, TimeoutError) as exc:
        raise ProviderError("Provider could not be reached.") from exc
    if not raw or len(raw) > maximum_bytes:
        raise ProviderError("Provider response was empty or exceeded its byte limit.")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProviderError("Provider returned invalid JSON.") from exc


def _request_xml(url: str, *, timeout: int, maximum_bytes: int) -> ElementTree.Element:
    try:
        with urlopen(Request(url, headers={"User-Agent": "BS-CATS-Source-Enrichment/1.0"}), timeout=timeout) as response:
            raw = response.read(maximum_bytes + 1)
    except HTTPError as exc:
        raise ProviderError(f"Feed returned HTTP {exc.code}.") from exc
    except (URLError, TimeoutError) as exc:
        raise ProviderError("Feed could not be reached.") from exc
    if not raw or len(raw) > maximum_bytes:
        raise ProviderError("Feed was empty or exceeded its byte limit.")
    try:
        return ElementTree.fromstring(raw)
    except ElementTree.ParseError as exc:
        raise ProviderError("Feed returned invalid XML.") from exc


class EnrichmentLedger:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self.path.parent, 0o700)
        descriptor = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(descriptor)
        os.chmod(self.path, 0o600)
        with sqlite3.connect(self.path) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS runs(
                    run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL,
                    completed_at TEXT, task_count INTEGER NOT NULL,
                    query_count INTEGER NOT NULL DEFAULT 0,
                    estimated_cost_usd REAL NOT NULL DEFAULT 0,
                    state TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS queries(
                    query_sha256 TEXT NOT NULL, provider_id TEXT NOT NULL,
                    task_id TEXT NOT NULL, attempted_at TEXT NOT NULL,
                    estimated_cost_usd REAL NOT NULL, state TEXT NOT NULL,
                    result_count INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(query_sha256, provider_id));
                CREATE TABLE IF NOT EXISTS discoveries(
                    url_sha256 TEXT NOT NULL, provider_id TEXT NOT NULL,
                    canonical_url TEXT NOT NULL, source_host TEXT NOT NULL,
                    query_sha256 TEXT NOT NULL, first_discovered_at TEXT NOT NULL,
                    last_discovered_at TEXT NOT NULL, occurrence_count INTEGER NOT NULL,
                    PRIMARY KEY(url_sha256, provider_id));
            """)

    def recently_attempted(self, query_hash: str, provider_id: str, cache_days: int) -> bool:
        cutoff = datetime.now(UTC) - timedelta(days=cache_days)
        with sqlite3.connect(self.path) as db:
            row = db.execute(
                "SELECT attempted_at FROM queries WHERE query_sha256=? AND provider_id=?",
                (query_hash, provider_id),
            ).fetchone()
        return bool(row and datetime.fromisoformat(row[0]) >= cutoff)

    def start_run(self, run_id: str, task_count: int) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO runs(run_id,started_at,task_count,state) VALUES(?,?,?,'running')",
                       (run_id, datetime.now(UTC).isoformat(), task_count))

    def record_attempt(self, task_id: str, provider_id: str, query_hash: str,
                       estimated_cost: float, state: str, discoveries: list[Discovery]) -> None:
        now = datetime.now(UTC).isoformat()
        with sqlite3.connect(self.path) as db:
            db.execute(
                "INSERT OR REPLACE INTO queries VALUES(?,?,?,?,?,?,?)",
                (query_hash, provider_id, task_id, now, estimated_cost, state, len(discoveries)),
            )
            for result in discoveries:
                normalized = canonical_url(result.url)
                if not normalized:
                    continue
                url_hash = _sha256(normalized)
                host = urlsplit(normalized).hostname or ""
                db.execute("""
                    INSERT INTO discoveries VALUES(?,?,?,?,?,?,?,1)
                    ON CONFLICT(url_sha256,provider_id) DO UPDATE SET
                      last_discovered_at=excluded.last_discovered_at,
                      occurrence_count=discoveries.occurrence_count+1
                """, (url_hash, provider_id, normalized, host, query_hash, now, now))

    def finish_run(self, run_id: str, query_count: int, estimated_cost: float, state: str) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("""UPDATE runs SET completed_at=?,query_count=?,estimated_cost_usd=?,state=?
                          WHERE run_id=?""",
                       (datetime.now(UTC).isoformat(), query_count, estimated_cost, state, run_id))


def validate_task(task: dict) -> dict:
    required = {"task_id", "entity_id", "source_class", "attribute_keys", "query", "commercial_priority"}
    missing = sorted(required - set(task))
    if missing:
        raise EnrichmentError("Task is missing fields: " + ", ".join(missing))
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{8,160}", str(task["task_id"])):
        raise EnrichmentError("task_id must be a stable 8-160 character identifier.")
    if not isinstance(task["attribute_keys"], list) or not task["attribute_keys"]:
        raise EnrichmentError("attribute_keys must be a nonempty list.")
    if not isinstance(task["query"], str) or not 3 <= len(task["query"].strip()) <= 500:
        raise EnrichmentError("query must contain 3-500 characters.")
    if task["commercial_priority"] not in {"low", "medium", "high"}:
        raise EnrichmentError("commercial_priority must be low, medium or high.")
    task.setdefault("preferred_domains", [])
    task.setdefault("feed_urls", [])
    if len(task["preferred_domains"]) > 20 or len(task["feed_urls"]) > 20:
        raise EnrichmentError("A task may specify at most 20 domains or feeds.")
    return task


class SourceEnrichmentRouter:
    def __init__(self, config: dict, environment: dict[str, str], root: Path):
        self.config = config
        self.environment = environment
        self.root = Path(root)
        self.limits = config["limits"]
        self.providers = {item["provider_id"]: item for item in config["providers"]}
        self.ledger = EnrichmentLedger(self.root / config["storage"]["ledger"])

    def _available(self, provider: dict, task: dict, allow_paid: bool) -> tuple[bool, str]:
        if not provider["enabled"]:
            return False, "disabled_by_policy"
        if task["source_class"] not in provider["source_classes"]:
            return False, "unsupported_source_class"
        if provider["adapter"] == "rss" and not task.get("feed_urls"):
            return False, "no_feed_urls"
        missing = [name for name in provider["required_environment"] if not self.environment.get(name, "").strip()]
        if missing:
            return False, "missing_credentials:" + ",".join(missing)
        if provider["paid"] and not allow_paid:
            return False, "paid_run_not_admitted"
        return True, "available"

    def plan(self, task: dict, *, allow_paid: bool = False) -> list[dict]:
        task = validate_task(dict(task))
        planned = []
        for provider in sorted(self.providers.values(), key=lambda item: item["priority"]):
            available, reason = self._available(provider, task, allow_paid)
            planned.append({
                "provider_id": provider["provider_id"],
                "available": available,
                "reason": reason,
                "estimated_cost_usd": provider["estimated_cost_per_request_usd"],
            })
        return planned

    def _discover(self, provider: dict, task: dict) -> list[Discovery]:
        adapter = provider["adapter"]
        method = getattr(self, "_discover_" + adapter, None)
        if method is None:
            raise ProviderError(f"No executable adapter exists for {adapter}.")
        return method(provider, task)

    def _discover_rss(self, provider: dict, task: dict) -> list[Discovery]:
        del provider
        tokens = {token for token in re.findall(r"[a-z0-9]+", task["query"].casefold()) if len(token) > 2}
        results = []
        for feed_url in task["feed_urls"]:
            root = _request_xml(feed_url, timeout=self.limits["request_timeout_seconds"],
                                maximum_bytes=self.limits["maximum_response_bytes"])
            for item in root.findall(".//item") + root.findall(".//{*}entry"):
                title = (item.findtext("title") or item.findtext("{*}title") or "").strip()
                link = item.findtext("link") or item.findtext("{*}link")
                if not link:
                    link_node = item.find("{*}link")
                    link = link_node.attrib.get("href") if link_node is not None else None
                text = title.casefold()
                if link and (not tokens or tokens.intersection(re.findall(r"[a-z0-9]+", text))):
                    results.append(Discovery("rss", link, title))
        return results[:self.limits["maximum_results_per_provider"]]

    def _discover_gdelt(self, provider: dict, task: dict) -> list[Discovery]:
        del provider
        parameters = urlencode({"query": task["query"], "mode": "ArtList", "format": "json",
                                "maxrecords": self.limits["maximum_results_per_provider"], "sort": "HybridRel"})
        payload = _request_json("https://api.gdeltproject.org/api/v2/doc/doc?" + parameters,
                                timeout=self.limits["request_timeout_seconds"],
                                maximum_bytes=self.limits["maximum_response_bytes"])
        return [Discovery("gdelt", item.get("url", ""), item.get("title", ""), item.get("seendate"))
                for item in payload.get("articles", []) if item.get("url")]

    def _discover_tavily(self, provider: dict, task: dict) -> list[Discovery]:
        del provider
        body = {"query": task["query"], "search_depth": "basic", "max_results": self.limits["maximum_results_per_provider"],
                "include_answer": False, "include_raw_content": False, "include_images": False}
        if task["preferred_domains"]:
            body["include_domains"] = task["preferred_domains"]
        payload = _request_json("https://api.tavily.com/search", timeout=self.limits["request_timeout_seconds"],
                                maximum_bytes=self.limits["maximum_response_bytes"],
                                headers={"Authorization": "Bearer " + self.environment["TAVILY_API_KEY"]}, body=body)
        return [Discovery("tavily", item.get("url", ""), item.get("title", ""), item.get("published_date"))
                for item in payload.get("results", []) if item.get("url")]

    def _discover_exa(self, provider: dict, task: dict) -> list[Discovery]:
        del provider
        payload = _request_json("https://api.exa.ai/search", timeout=self.limits["request_timeout_seconds"],
                                maximum_bytes=self.limits["maximum_response_bytes"],
                                headers={"x-api-key": self.environment["EXA_API_KEY"]},
                                body={"query": task["query"], "type": "auto",
                                      "numResults": self.limits["maximum_results_per_provider"]})
        return [Discovery("exa", item.get("url", ""), item.get("title", ""), item.get("publishedDate"))
                for item in payload.get("results", []) if item.get("url")]

    def _discover_serper(self, provider: dict, task: dict) -> list[Discovery]:
        del provider
        payload = _request_json("https://google.serper.dev/search", timeout=self.limits["request_timeout_seconds"],
                                maximum_bytes=self.limits["maximum_response_bytes"],
                                headers={"X-API-KEY": self.environment["SERPER_API_KEY"]},
                                body={"q": task["query"], "num": self.limits["maximum_results_per_provider"]})
        return [Discovery("serper", item.get("link", ""), item.get("title", ""), item.get("date"))
                for item in payload.get("organic", []) if item.get("link")]

    def _discover_brave(self, provider: dict, task: dict) -> list[Discovery]:
        del provider
        parameters = urlencode({"q": task["query"], "count": self.limits["maximum_results_per_provider"]})
        payload = _request_json("https://api.search.brave.com/res/v1/web/search?" + parameters,
                                timeout=self.limits["request_timeout_seconds"],
                                maximum_bytes=self.limits["maximum_response_bytes"],
                                headers={"X-Subscription-Token": self.environment["BRAVE_SEARCH_API_KEY"]})
        return [Discovery("brave", item.get("url", ""), item.get("title", ""), item.get("page_age"))
                for item in payload.get("web", {}).get("results", []) if item.get("url")]

    def _discover_dataforseo(self, provider: dict, task: dict) -> list[Discovery]:
        del provider
        credentials = f"{self.environment['DATAFORSEO_LOGIN']}:{self.environment['DATAFORSEO_PASSWORD']}"
        authorization = "Basic " + base64.b64encode(credentials.encode("utf-8")).decode("ascii")
        payload = _request_json("https://api.dataforseo.com/v3/serp/google/organic/live/advanced",
                                timeout=self.limits["request_timeout_seconds"],
                                maximum_bytes=self.limits["maximum_response_bytes"],
                                headers={"Authorization": authorization},
                                body=[{"keyword": task["query"], "language_code": "en",
                                       "depth": self.limits["maximum_results_per_provider"]}])
        items = []
        for api_task in payload.get("tasks", []):
            for result in api_task.get("result") or []:
                items.extend(result.get("items") or [])
        return [Discovery("dataforseo", item.get("url", ""), item.get("title", ""), item.get("timestamp"))
                for item in items if item.get("type") == "organic" and item.get("url")]

    def execute(self, tasks: list[dict], *, allow_paid: bool = False) -> dict:
        normalized = [validate_task(dict(task)) for task in tasks]
        run_id = "enrich_" + _sha256(datetime.now(UTC).isoformat())[:24]
        self.ledger.start_run(run_id, len(normalized))
        query_count = 0
        estimated_cost = 0.0
        task_summaries = []
        try:
            for task in normalized:
                task_cost = 0.0
                unique_urls = set()
                attempts = []
                for provider in sorted(self.providers.values(), key=lambda item: item["priority"]):
                    available, reason = self._available(provider, task, allow_paid)
                    if not available:
                        attempts.append({"provider_id": provider["provider_id"], "state": reason})
                        continue
                    if len([item for item in attempts if item.get("executed")]) >= self.limits["maximum_providers_per_task"]:
                        break
                    cost = float(provider["estimated_cost_per_request_usd"])
                    if task_cost + cost > self.limits["maximum_estimated_cost_per_task_usd"]:
                        attempts.append({"provider_id": provider["provider_id"], "state": "task_cost_cap"})
                        continue
                    if estimated_cost + cost > self.limits["maximum_estimated_cost_per_run_usd"]:
                        raise AdmissionError("Run cost cap reached before submitting another provider request.")
                    if query_count >= self.limits["maximum_queries_per_run"]:
                        raise AdmissionError("Run query cap reached before submitting another provider request.")
                    query_hash = _sha256(json.dumps([task["query"], task["preferred_domains"], task["feed_urls"]],
                                                    sort_keys=True, separators=(",", ":")))
                    if self.ledger.recently_attempted(query_hash, provider["provider_id"], self.limits["query_cache_days"]):
                        attempts.append({"provider_id": provider["provider_id"], "state": "cached_recent_attempt"})
                        continue
                    query_count += 1
                    task_cost += cost
                    estimated_cost += cost
                    try:
                        discovered = self._discover(provider, task)
                        state = "completed"
                    except ProviderError:
                        discovered = []
                        state = "provider_error_no_retry"
                    self.ledger.record_attempt(task["task_id"], provider["provider_id"], query_hash, cost, state, discovered)
                    for item in discovered:
                        normalized_url = canonical_url(item.url)
                        if normalized_url:
                            unique_urls.add(normalized_url)
                    attempts.append({"provider_id": provider["provider_id"], "state": state,
                                     "executed": True, "result_count": len(discovered),
                                     "estimated_cost_usd": cost})
                    if len(unique_urls) >= self.limits["target_unique_candidates_per_task"]:
                        break
                task_summaries.append({"task_id": task["task_id"], "entity_id": task["entity_id"],
                                       "candidate_url_count": len(unique_urls), "estimated_cost_usd": round(task_cost, 6),
                                       "resolution_state": "discovery_candidates_found" if unique_urls else "not_available",
                                       "attempts": attempts})
            self.ledger.finish_run(run_id, query_count, estimated_cost, "completed")
        except Exception:
            self.ledger.finish_run(run_id, query_count, estimated_cost, "failed")
            raise
        return {"run_id": run_id, "state": "completed", "task_count": len(normalized),
                "query_count": query_count, "estimated_cost_usd": round(estimated_cost, 6),
                "tasks": task_summaries,
                "evidence_state": self.config["evidence_policy"]["search_result_state"]}
