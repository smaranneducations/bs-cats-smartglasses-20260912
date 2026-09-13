"""Bounded, metadata-only YouTube market discovery with 29-day retention."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class YouTubeMarketError(RuntimeError):
    pass


def _instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise YouTubeMarketError("YouTube snapshot timestamps require a timezone.")
    return parsed


def _fingerprint(value) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return sha256(encoded).hexdigest()


def _safe_text(value, maximum: int) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(value or ""))[:maximum]


def _write_private(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def _api_key(root: Path) -> str:
    direct = os.getenv("YOUTUBE_API_KEY", "").strip()
    if direct:
        return direct
    env_path = root / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            if key.strip() == "YOUTUBE_API_KEY":
                result = value.strip().strip('"').strip("'")
                if result:
                    return result
    raise YouTubeMarketError("YOUTUBE_API_KEY is not configured locally.")


class YouTubeMarketPipeline:
    def __init__(self, root: Path, config_path: Path):
        self.root = root.resolve()
        self.config = json.loads(config_path.read_text(encoding="utf-8"))
        self.state_root = self.root / ".local" / "youtube-market-learning"
        self.snapshot_path = self.state_root / "current-snapshot.json"
        self.runs_root = self.state_root / "runs"

    def _fetch(self, query: str, published_after: str, key: str) -> tuple[list[dict], int]:
        source = self.config["source"]
        params = {"part": "snippet", "type": "video", "order": "relevance", "safeSearch": "moderate",
                  "q": query, "maxResults": source["max_results_per_query"],
                  "relevanceLanguage": source["relevance_language"], "publishedAfter": published_after,
                  "fields": "items(id/videoId,snippet/channelId,snippet/channelTitle,snippet/title,snippet/description,snippet/publishedAt)",
                  "key": key}
        request = Request("https://www.googleapis.com/youtube/v3/search?" + urlencode(params),
                          headers={"Accept": "application/json", "User-Agent": "BS-CATS-Market-Learning/1.0"})
        maximum = int(self.config["budgets"]["max_api_response_bytes"])
        with urlopen(request, timeout=15) as response:
            raw = response.read(maximum + 1)
        if len(raw) > maximum:
            raise YouTubeMarketError("YouTube response exceeded the bounded byte budget.")
        payload = json.loads(raw)
        return payload.get("items", []), len(raw)

    def run(self, now: datetime | None = None) -> dict:
        now = now or datetime.now(UTC)
        if now.tzinfo is None:
            raise YouTubeMarketError("An explicit timezone is required.")
        self.runs_root.mkdir(parents=True, exist_ok=True)
        cycle = now.strftime("%Y-%m")
        receipt_path = self.runs_root / f"{cycle}.json"
        if receipt_path.is_file():
            existing = json.loads(receipt_path.read_text(encoding="utf-8"))
            completed = _instant(existing["completed_at"])
            if now - completed < timedelta(days=28):
                return existing | {"idempotent_replay": True}

        previous = None
        if self.snapshot_path.is_file():
            candidate = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
            if _instant(candidate["expires_at"]) > now:
                previous = candidate
            else:
                self.snapshot_path.unlink()

        source = self.config["source"]
        queries = source["queries"][:int(self.config["budgets"]["max_search_requests_per_run"])]
        after = (now - timedelta(days=int(source["lookback_days"]))).isoformat().replace("+00:00", "Z")
        key = _api_key(self.root)
        records, response_bytes = {}, 0
        query_hits = {query: 0 for query in queries}
        for query in queries:
            items, length = self._fetch(query, after, key)
            response_bytes += length
            if response_bytes > int(self.config["budgets"]["max_api_response_bytes"]):
                raise YouTubeMarketError("Combined YouTube responses exceeded the run byte budget.")
            for item in items:
                identifier = _safe_text(item.get("id", {}).get("videoId"), 32)
                snippet = item.get("snippet", {})
                channel_id = _safe_text(snippet.get("channelId"), 32)
                if not identifier or not channel_id:
                    continue
                query_hits[query] += 1
                record = records.setdefault(identifier, {
                    "video_id": identifier, "channel_id": channel_id,
                    "channel_title": _safe_text(snippet.get("channelTitle"), 160),
                    "title": _safe_text(snippet.get("title"), 300),
                    "description": _safe_text(snippet.get("description"), 1200),
                    "published_at": _safe_text(snippet.get("publishedAt"), 40), "matched_queries": []})
                if query not in record["matched_queries"]:
                    record["matched_queries"].append(query)

        ordered = sorted(records.values(), key=lambda item: item["video_id"])
        previous_records = {item["video_id"]: item for item in (previous or {}).get("videos", [])}
        new = sum(identifier not in previous_records for identifier in records)
        changed = sum(identifier in previous_records and _fingerprint(records[identifier]) != _fingerprint(previous_records[identifier]) for identifier in records)
        unchanged = len(records) - new - changed
        channel_counts = {}
        for item in ordered:
            current = channel_counts.setdefault(item["channel_id"], {"channel_id": item["channel_id"],
                "channel_title": item["channel_title"], "matched_videos": 0, "matched_queries": set()})
            current["matched_videos"] += 1
            current["matched_queries"].update(item["matched_queries"])
        channels = [{**value, "matched_queries": sorted(value["matched_queries"])} for value in channel_counts.values()]
        channels.sort(key=lambda item: (-item["matched_videos"], -len(item["matched_queries"]), item["channel_id"]))
        channels = channels[:int(source["max_candidate_channels"])]

        topic_counts = {}
        for topic, terms in self.config["topic_taxonomy"].items():
            matches = [item["video_id"] for item in ordered if any(term.lower() in (item["title"] + " " + item["description"]).lower() for term in terms)]
            topic_counts[topic] = len(set(matches))
        ontology_signals = []
        for candidate in self.config.get("ontology_candidates", []):
            matches = [item for item in ordered if any(term.lower() in (item["title"] + " " + item["description"]).lower()
                                                       for term in candidate["trigger_terms"])]
            channel_total = len({item["channel_id"] for item in matches})
            if len(matches) >= candidate["minimum_distinct_videos"] and channel_total >= candidate["minimum_distinct_channels"]:
                ontology_signals.append({"key": candidate["key"], "matched_videos": len(matches),
                                         "matched_channels": channel_total,
                                         "disposition": "corroboration_required_before_governed_proposal"})

        expires = now + timedelta(days=int(self.config["retention"]["current_snapshot_days"]))
        snapshot = {"schema_version": "youtube-market-snapshot-1", "captured_at": now.isoformat(),
                    "expires_at": expires.isoformat(), "provider": "YouTube Data API v3",
                    "policy": "non_authorized_metadata_delete_or_refresh_before_30_days",
                    "videos": ordered, "candidate_channels": channels, "topic_counts": topic_counts,
                    "ontology_signals": ontology_signals, "not_product_evidence": True,
                    "no_audiovisual_or_transcript_content": True}
        _write_private(self.snapshot_path, snapshot)
        receipt = {"schema_version": "youtube-market-run-receipt-1", "cycle": cycle,
                   "completed_at": now.isoformat(), "snapshot_expires_at": expires.isoformat(),
                   "search_requests": len(queries), "response_bytes": response_bytes,
                   "unique_videos": len(ordered), "candidate_channels": len(channels),
                   "new_since_current_snapshot": new, "changed_since_current_snapshot": changed,
                   "unchanged_since_current_snapshot": unchanged, "query_result_counts": query_hits,
                   "snapshot_fingerprint": _fingerprint(snapshot), "stored_titles_or_descriptions": False,
                   "stored_video_or_channel_ids": False, "paid_model_calls": 0, "media_downloads": 0,
                   "product_facts_written": 0, "ontology_changes_written": 0, "idempotent_replay": False}
        _write_private(receipt_path, receipt)
        return receipt
