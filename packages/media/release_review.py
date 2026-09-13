"""Bounded file, lineage and review evidence for an existing rendered artifact."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit

from packages.contracts.media import RenderArtifactPayload
from packages.contracts.release_review import ReleaseCheck, ReleaseReviewPayload
from packages.media.planning import admit_recipe

ROOT = Path(__file__).resolve().parents[2]


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class FileObservation:
    path: Path | None
    sha256: str | None
    content: bytes | None
    error: str | None


def observe_render_file(root: Path, uri: str, suffix: str, maximum_bytes: int, *, retain: bool = False) -> FileObservation:
    try:
        allowed = (root / ".local" / "production-renders").resolve()
        path = (root / uri).resolve()
        if not path.is_relative_to(allowed) or path.suffix.lower() != suffix:
            return FileObservation(None, None, None, "File is outside the allowed render output scope.")
        hasher = hashlib.sha256()
        chunks = []
        length = 0
        with path.open("rb") as source:
            before = os.fstat(source.fileno())
            if not 0 < before.st_size <= maximum_bytes:
                return FileObservation(None, None, None, "File is empty or exceeds the inspection byte budget.")
            while chunk := source.read(65536):
                length += len(chunk)
                if length > maximum_bytes:
                    return FileObservation(None, None, None, "File grew beyond the inspection byte budget.")
                hasher.update(chunk)
                if retain:
                    chunks.append(chunk)
            after = os.fstat(source.fileno())
            current = path.stat()
            if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns) or current.st_ino != after.st_ino:
                return FileObservation(None, None, None, "File changed during inspection.")
        return FileObservation(path, hasher.hexdigest(), b"".join(chunks) if retain else None, None)
    except (OSError, ValueError):
        return FileObservation(None, None, None, "Render file is unavailable within the allowed output scope.")


def probe_video(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["/opt/homebrew/bin/ffprobe", "-v", "error", "-protocol_whitelist", "file,pipe", "-show_entries", "stream=codec_name,codec_type,width,height:format=duration", "-of", "json", str(path)],
        stdin=subprocess.DEVNULL, capture_output=True, timeout=15, check=False,
        env={"PATH": "/opt/homebrew/bin:/usr/bin:/bin", "LANG": "C"},
    )
    if result.returncode != 0 or len(result.stdout) > 262144:
        raise ValueError("Bounded media probe did not complete")
    return json.loads(result.stdout)


def technical_media_matches(payload: RenderArtifactPayload, inspection: dict[str, Any]) -> bool:
    try:
        videos = [stream for stream in inspection["streams"] if stream.get("codec_type") == "video"]
        audio = [stream for stream in inspection["streams"] if stream.get("codec_type") == "audio"]
        duration = float(inspection["format"]["duration"])
        return len(videos) == 1 and len(audio) == 1 and videos[0].get("codec_name") == "h264" and audio[0].get("codec_name") == "aac" and videos[0].get("width") == payload.width and videos[0].get("height") == payload.height and math.isfinite(duration) and 29.9 <= duration <= 90.1 and abs(duration - payload.duration_seconds) <= 0.12
    except (KeyError, TypeError, ValueError):
        return False


def source_uri(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("An explicit web source URI is required")
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, parsed.query, ""))


def instant(value: Any) -> datetime:
    result = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("A source-policy timezone is required")
    return result


def assess_release(store: Any, artifact_id: str, *, root: Path = ROOT, now: datetime | None = None, admission: Callable = admit_recipe, prober: Callable = probe_video) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("An explicit check timezone is required")
    records: dict[str, dict[str, Any]] = {}
    objects: dict[str, Any] = {}
    missing = []

    def get(identifier: str) -> dict[str, Any]:
        if identifier not in records:
            if len(records) >= 40:
                raise ValueError("Artifact lineage exceeds the bounded review packet")
            item = store.get(identifier)
            objects[identifier] = item
            records[identifier] = item.model_dump(mode="json")
        return records[identifier]

    artifact = get(artifact_id)
    if artifact["object_type"] != "render_artifact":
        raise ValueError("An existing governed render artifact is required")
    payload = RenderArtifactPayload.model_validate(artifact["payload"])
    recipe_record = get(payload.recipe_object_id)
    if recipe_record["object_type"] != "render_recipe":
        raise ValueError("Artifact parent is not a governed render recipe")
    recipe = recipe_record["payload"]
    for identifier in recipe["input_versions"]:
        try:
            get(identifier)
        except Exception:
            missing.append(identifier)

    checks = []
    observed: dict[str, str | None] = {}

    def check(identifier: str, state: str, reason: str, ids: list[str] | None = None):
        checks.append(ReleaseCheck(check_id=identifier, state=state, reason=reason, object_ids=ids or []))

    video = observe_render_file(root, payload.artifact_uri, ".mp4", 128 * 1024 * 1024)
    manifest_file = observe_render_file(root, payload.manifest_uri, ".json", 2 * 1024 * 1024, retain=True)
    observed.update({"video": video.sha256, "manifest": manifest_file.sha256, "metadata": canonical_hash(payload.publish_metadata)})
    video_ok = video.sha256 == payload.video_sha256
    manifest_ok = manifest_file.sha256 == payload.manifest_sha256
    check("video_integrity", "passed" if video_ok else "blocked", "Video bytes match the governed artifact hash." if video_ok else video.error or "Video bytes differ from the governed artifact.")
    check("manifest_integrity", "passed" if manifest_ok else "blocked", "Manifest bytes match the governed artifact hash." if manifest_ok else manifest_file.error or "Manifest bytes differ from the governed artifact.")
    manifest = None
    if manifest_ok:
        try:
            manifest = json.loads(manifest_file.content)
            if not isinstance(manifest, dict) or manifest.get("schema_version") != "render-manifest-1":
                manifest = None
        except (TypeError, ValueError):
            manifest = None
    metadata_ok = observed["metadata"] == payload.metadata_sha256 and manifest is not None and manifest.get("publish_metadata") == payload.publish_metadata and manifest.get("metadata_sha256") == payload.metadata_sha256
    check("metadata_integrity", "passed" if metadata_ok else "blocked", "Exact metadata matches its compact, sorted JSON hash and the verified manifest." if metadata_ok else "Metadata or its manifest binding differs from the governed artifact.")
    observed["recipe"] = canonical_hash(recipe)
    binding_ok = manifest is not None and manifest.get("recipe") == recipe and manifest.get("recipe_sha256") == observed["recipe"] and manifest.get("recipe_object_id") == payload.recipe_object_id and manifest.get("recipe_version") == payload.recipe_version == recipe_record["version"] and manifest.get("video_sha256") == payload.video_sha256
    check("recipe_binding", "passed" if binding_ok else "blocked", "Manifest, recipe version and output video are bound to the same render." if binding_ok else "The artifact, manifest and recipe no longer describe the same render.", [payload.recipe_object_id])
    soundtrack_uri = str(Path(payload.artifact_uri).parent / "soundtrack.wav")
    soundtrack = observe_render_file(root, soundtrack_uri, ".wav", 16 * 1024 * 1024)
    observed["soundtrack"] = soundtrack.sha256
    soundtrack_ok = manifest is not None and soundtrack.sha256 is not None and soundtrack.sha256 == manifest.get("soundtrack_sha256")
    check("soundtrack_integrity", "passed" if soundtrack_ok else "blocked", "The original soundtrack file matches the verified render manifest." if soundtrack_ok else soundtrack.error or "The soundtrack is missing or differs from the manifest.")

    probe_ok = False
    if video_ok and video.path is not None:
        try:
            probe_ok = technical_media_matches(payload, prober(video.path))
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    check("technical_media", "passed" if probe_ok else "blocked", "A fresh bounded probe found the expected duration, dimensions, H.264 video and AAC audio. This does not evaluate visual or musical quality." if probe_ok else "The bounded media probe did not establish the required technical properties.")
    delivery_ready = min(payload.width, payload.height) >= 720 and max(payload.width, payload.height) >= 1280
    check("delivery_resolution", "passed" if delivery_ready else "needs_review", "The render meets the current 720p-or-higher review delivery size." if delivery_ready else "This is a low-resolution preview; a final-quality render is still required.")

    products = [record for record in records.values() if record["object_type"] == "product"]
    facts_ready = bool(products) and all(record.get("review", {}).get("state") == "approved" and record.get("status") not in {"rejected", "deprecated", "archived"} for record in products)
    check("factual_review", "passed" if facts_ready else "needs_review", "The exact product-record versions have approved factual reviews; manufacturer statements remain distinct from hands-on tests." if facts_ready else "The source-bound product statements still need factual review.", [record["object_id"] for record in products])

    source_refs = artifact.get("sources", [])
    source_ids = {reference.get("source_id") for reference in source_refs}
    used_source_ids = {identifier for beat in recipe.get("beats", []) for cell in beat.get("cells", []) for identifier in cell.get("source_ids", [])}
    lineage_ok = bool(source_refs) and used_source_ids.issubset(source_ids)
    check("source_lineage", "passed" if lineage_ok else "blocked", "Source references include the identifiers used by the rendered comparison cells; recipe admission separately checks factual statements." if lineage_ok else "Rendered claim sources are absent from the artifact's source references.")

    policies = [item.model_dump(mode="json") for item in store.list_objects(object_type="source_policy")]
    if len(policies) > 100:
        raise ValueError("Source-policy inventory exceeds the bounded review scope")
    policy_state = "passed" if source_refs else "needs_review"
    policy_ids = []
    for reference in source_refs:
        try:
            matching = [policy for policy in policies if source_uri(policy["payload"]["source_uri"]) == source_uri(reference["uri"])]
            if not matching:
                policy_state = "needs_review" if policy_state != "blocked" else policy_state
                continue
            selected = max(matching, key=lambda item: (instant(item["updated_at"]), item["object_id"]))
            selected = get(selected["object_id"])
            policy_ids.append(selected["object_id"])
            value = selected["payload"]
            if value.get("commercial_reuse") == "denied" or selected.get("review", {}).get("state") == "rejected":
                policy_state = "blocked"
                continue
            observed_at = instant(value["last_observed_at"])
            expires = instant(value["permission_expires_at"]) if value.get("permission_expires_at") else None
            valid = selected.get("review", {}).get("state") == "approved" and selected.get("status") not in {"deprecated", "archived", "rejected"} and value.get("commercial_reuse") == "allowed" and observed_at <= now < observed_at + timedelta(days=value["refresh_days"]) and (expires is None or now < expires)
            if not valid and policy_state != "blocked":
                policy_state = "needs_review"
        except (KeyError, TypeError, ValueError):
            if policy_state != "blocked":
                policy_state = "needs_review"
    check("source_policy", policy_state, "Applicable source-policy records are current and approved for commercial reuse; this does not grant automated collection or media rights." if policy_state == "passed" else "Applicable source-policy evidence is missing, unreviewed, expired or denies commercial reuse. No permission is inferred from public availability.", list(dict.fromkeys(policy_ids)))

    rights_state = "passed"
    unresolved_assets = []
    for identifier, embedded in recipe["assets"].items():
        record = records.get(identifier)
        current = record["payload"] if record else {}
        denied = current.get("rights_state") == "denied" or current.get("commercial_use_allowed") is False or (record or {}).get("review", {}).get("state") == "rejected"
        documented = current == embedded and current.get("rights_state") == "documented" and current.get("commercial_use_allowed") is True and bool(current.get("provenance_reference")) and bool(current.get("credit"))
        if not documented or denied:
            unresolved_assets.append(identifier)
            if denied:
                rights_state = "blocked"
            elif rights_state != "blocked":
                rights_state = "needs_review"
    check("media_rights", rights_state, "Version-bound media records contain documented permission and attribution evidence. Final human artifact review remains separate." if rights_state == "passed" else "Some rendered media lacks documented commercial permission or has adverse rights evidence. Font licensing does not clear background images.", unresolved_assets)

    current_recipe = not missing and all(records.get(identifier, {}).get("version") == version for identifier, version in recipe["input_versions"].items())
    try:
        admission(store, objects[payload.recipe_object_id])
    except Exception:
        current_recipe = False
    check("recipe_current", "passed" if current_recipe else "blocked", "The existing renderer admission check and exact input-version checks pass." if current_recipe else "Recipe admission or an exact input-version check failed; do not reuse this render as current evidence.")
    stable = True
    for identifier, record in records.items():
        try:
            if store.get(identifier).version != record["version"]:
                stable = False
        except Exception:
            stable = False
    check("input_stability", "passed" if stable else "blocked", "No object-version change was detected across the bounded checks. This is not an atomic cross-object snapshot and must be rechecked before use." if stable else "An input changed or became unavailable during inspection.")
    review = artifact.get("review", {}).get("state")
    check("human_artifact_review", "passed" if review == "approved" else "blocked" if review == "rejected" else "needs_review", "The recorded exact-artifact review is approved; this packet still grants no publication permission." if review == "approved" else "Human viewing/listening review of the exact final video and metadata has not been approved.", [artifact_id])

    prerequisite = all(item.state == "passed" for item in checks if item.check_id != "human_artifact_review")
    versions = {identifier: record["version"] for identifier, record in records.items()}
    fingerprint = canonical_hash({"policy": "artifact-review-1", "versions": versions, "observed_hashes": observed, "checks": [item.model_dump(mode="json") for item in checks], "missing": sorted(missing)})
    packet = ReleaseReviewPayload(summary=f"{sum(item.state == 'passed' for item in checks)} of {len(checks)} artifact checks passed. This packet is evidence for review, not permission to publish.", checked_at=now, artifact_id=artifact_id, artifact_version=artifact["version"], recipe_id=payload.recipe_object_id, recipe_version=recipe_record["version"], video_sha256=payload.video_sha256, metadata_sha256=payload.metadata_sha256, manifest_sha256=payload.manifest_sha256, input_versions=versions, input_fingerprint=fingerprint, missing_input_ids=missing, observed_hashes=observed, checks=checks, prerequisites_satisfied=prerequisite)
    return {"packet": packet.model_dump(mode="json"), "sources": source_refs, "private_player_url": f"/media-review/{artifact_id}"}
