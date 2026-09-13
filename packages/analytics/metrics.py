"""Normalize owned-app engagement and creative primitives to warehouse-shaped rows."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
from hashlib import sha256
import json
import os
from pathlib import Path


def _hash(*values) -> str:
    return sha256(":".join(str(value) for value in values).encode()).hexdigest()


def _write_private(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)


class OwnedMetricsCollector:
    def __init__(self, root: Path, store):
        self.root = root.resolve()
        self.store = store
        self.events_path = self.root / ".local" / "audience-events.jsonl"
        self.output_root = self.root / ".local" / "analytics"

    def _events(self):
        if not self.events_path.is_file():
            return []
        if self.events_path.stat().st_size > 16 * 1024 * 1024:
            raise ValueError("Audience event log exceeds the bounded local collection size.")
        events = []
        for line in self.events_path.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
            except ValueError:
                continue
            content_id = item.get("content_id")
            if content_id and item.get("content_kind") == "canonical_video":
                events.append({"content_id": content_id, "event_type": item.get("event_type"),
                               "recorded_at": item.get("recorded_at")})
        return events

    def collect(self, captured_at: datetime | None = None):
        captured_at = captured_at or datetime.now(UTC)
        if captured_at.tzinfo is None:
            raise ValueError("Metrics collection requires an explicit timezone.")
        grouped = defaultdict(Counter)
        first_seen, last_seen = {}, {}
        invalid_subjects = set()
        for event in self._events():
            try:
                package = self.store.get(event["content_id"])
                if package.object_type != "distribution_package":
                    raise ValueError
            except Exception:
                invalid_subjects.add(event["content_id"])
                continue
            grouped[event["content_id"]][event["event_type"]] += 1
            stamp = str(event["recorded_at"])
            first_seen[event["content_id"]] = min(first_seen.get(event["content_id"], stamp), stamp)
            last_seen[event["content_id"]] = max(last_seen.get(event["content_id"], stamp), stamp)

        metric_rows, primitive_rows = [], []
        for package_id, counts in sorted(grouped.items()):
            package = self.store.get(package_id)
            artifact = self.store.get(package.payload["render_artifact_id"])
            recipe = self.store.get(artifact.payload["recipe_object_id"])
            values = dict(sorted(counts.items())) | {
                "first_event_at": first_seen[package_id], "last_event_at": last_seen[package_id],
                "total_events": sum(counts.values()), "factual_quality_signal": None}
            metric_rows.append({
                "row_id": _hash("owned_app", package_id, captured_at.date().isoformat()),
                "recorded_at": captured_at.isoformat(), "video_id": package_id, "platform": "owned_app",
                "post_id": package_id, "captured_at": captured_at.isoformat(),
                "metric_values": values, "collection_method": "internal_event_log"})
            for beat in recipe.payload.get("beats", []):
                primitive_rows.append({
                    "row_id": _hash(package_id, beat.get("beat_id"), beat.get("primitive"), recipe.version),
                    "recorded_at": captured_at.isoformat(), "video_id": package_id,
                    "scene_id": beat.get("beat_id"), "primitive_id": beat.get("primitive"),
                    "primitive_version": recipe.payload.get("recipe_version"),
                    "parameters": {"duration_seconds": beat.get("duration_seconds"),
                                   "accent": beat.get("accent"), "image_asset_id": beat.get("image_asset_id")}})

        result = {
            "schema_version": "owned-metrics-snapshot-1", "captured_at": captured_at.isoformat(),
            "metric_rows": metric_rows, "primitive_usage_rows": primitive_rows,
            "invalid_subject_count": len(invalid_subjects), "comment_text_retained": False,
            "session_ids_retained": False, "factual_quality_separate": True,
            "warehouse_write_performed": False}
        _write_private(self.output_root / "current-owned-metrics.json", result)
        receipt = {
            "schema_version": "owned-metrics-receipt-1", "captured_at": captured_at.isoformat(),
            "videos": len(metric_rows), "metric_rows": len(metric_rows),
            "primitive_usage_rows": len(primitive_rows), "invalid_subject_count": len(invalid_subjects),
            "warehouse_write_performed": False, "paid_calls": 0}
        _write_private(self.output_root / "latest-receipt.json", receipt)
        return receipt
