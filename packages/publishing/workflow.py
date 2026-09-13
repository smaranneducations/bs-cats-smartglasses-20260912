"""Exact-artifact packaging and fail-closed publication adapters."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from packages.contracts.distribution import ChannelCopy, DistributionPackagePayload, PublicationRequestPayload
from packages.contracts.media import RenderArtifactPayload
from packages.contracts.object import UniversalObject
from packages.contracts.store import ContractViolationError
from packages.media.release_review import assess_release

ROOT = Path(__file__).resolve().parents[2]
AUTO_DESTINATIONS = {"owned_app", "youtube", "linkedin"}
MANUAL_DESTINATIONS = {"instagram", "tiktok", "x"}


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return sha256(encoded).hexdigest()


def _safe_render_path(uri: str, suffixes: set[str]) -> Path:
    allowed = (ROOT / ".local" / "production-renders").resolve()
    path = (ROOT / uri).resolve()
    if not path.is_relative_to(allowed) or path.suffix.lower() not in suffixes or not path.is_file():
        raise ContractViolationError("A required artifact file is outside the governed render directory.")
    return path


def _file_hash(path: Path, maximum: int = 128 * 1024 * 1024) -> str:
    if not 0 < path.stat().st_size <= maximum:
        raise ContractViolationError("A distribution file is empty or exceeds the bounded size.")
    digest = sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _poster_for(artifact_id: str, video: Path, supplied_uri: str | None) -> Path:
    if supplied_uri:
        return _safe_render_path(supplied_uri, {".jpg", ".jpeg", ".png", ".webp"})
    target = ROOT / ".local" / "distribution-staging" / artifact_id / "poster.jpg"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        result = subprocess.run([
            "/opt/homebrew/bin/ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", "1", "-i", str(video), "-frames:v", "1", "-vf", "scale=720:-2", str(target),
        ], stdin=subprocess.DEVNULL, capture_output=True, timeout=30, check=False,
           env={"PATH": "/opt/homebrew/bin:/usr/bin:/bin", "LANG": "C"})
        if result.returncode != 0:
            raise ContractViolationError("A bounded poster extraction did not complete.")
    return target.resolve()


def _release_packet(store, artifact_id: str, artifact_version: int):
    candidates = [item for item in store.list_objects(object_type="release_review_packet")
                  if item.payload.get("artifact_id") == artifact_id
                  and item.payload.get("artifact_version") == artifact_version
                  and item.status.value not in {"rejected", "archived", "deprecated"}]
    if not candidates:
        raise ContractViolationError("Prepare a current release-review packet before distribution packaging.")
    return max(candidates, key=lambda item: (item.version, item.updated_at))


def _default_copy(destination: str, metadata: dict[str, Any], app_link: str, disclosure: str) -> ChannelCopy:
    title = str(metadata.get("title") or "Evidence-led product brief")[:240]
    description = str(metadata.get("description") or metadata.get("summary") or title).strip()
    tags = [str(value).lstrip("#")[:60] for value in metadata.get("tags", []) if str(value).strip()][:30]
    suffix = f"\n\nExplore the evidence and join the discussion: {app_link}\n\n{disclosure}"
    text = f"{description}\n\nWhat would you verify before choosing?{suffix}" if destination == "linkedin" else description + suffix
    if destination in MANUAL_DESTINATIONS:
        text = f"{title}\n\n{text}"
    return ChannelCopy(title=title, text=text[:5000], tags=tags, disclosure=disclosure,
                       canonical_app_link=app_link)


def build_distribution_objects(store, artifact_id: str, primary_concept_key: str, *,
                               product_ids: list[str] | None = None,
                               destinations: list[str] | None = None,
                               app_base_url: str = "http://127.0.0.1:8766",
                               poster_uri: str | None = None,
                               captions_uri: str | None = None,
                               disclosure: str = "Evidence-led analysis; source and media details are available in the app."):
    artifact = store.get(artifact_id)
    if artifact.object_type != "render_artifact":
        raise ContractViolationError("Distribution requires a governed render artifact.")
    payload = RenderArtifactPayload.model_validate(artifact.payload)
    if not 29.9 <= payload.duration_seconds <= 90.1 or abs((payload.width / payload.height) - (9 / 16)) > 0.01:
        raise ContractViolationError("Canonical distribution requires a 9:16 video lasting 30 to 90 seconds.")
    release = _release_packet(store, artifact.object_id, artifact.version)
    check_states = {item["check_id"]: item["state"] for item in release.payload.get("checks", [])}
    evidence_state = "passed" if release.payload.get("prerequisites_satisfied") else "blocked"
    rights_state = check_states.get("media_rights", "pending")
    video = _safe_render_path(payload.artifact_uri, {".mp4"})
    if _file_hash(video) != payload.video_sha256:
        raise ContractViolationError("The canonical video no longer matches its governed hash.")
    poster = _poster_for(artifact.object_id, video, poster_uri)
    captions = _safe_render_path(captions_uri, {".vtt", ".srt"}) if captions_uri else None
    products = list(dict.fromkeys(product_ids or [identifier for identifier in release.payload.get("input_versions", {})
                                                  if identifier.startswith("product_")]))[:2]
    if not products:
        raise ContractViolationError("A canonical product video requires at least one version-bound product.")
    shape = "one_product_one_attribute" if len(products) == 1 else "two_products_one_attribute"
    selected = list(dict.fromkeys(destinations or ["owned_app", "youtube", "linkedin", "instagram", "tiktok", "x"]))
    if not set(selected).issubset(AUTO_DESTINATIONS | MANUAL_DESTINATIONS):
        raise ContractViolationError("A distribution destination is unsupported.")
    app_link = app_base_url.rstrip("/") + "/discover?video=" + payload.video_sha256[:20]
    copy = {destination: _default_copy(destination, payload.publish_metadata, app_link, disclosure)
            for destination in selected}
    distribution = DistributionPackagePayload(
        summary=str(payload.publish_metadata.get("description") or payload.publish_metadata.get("title") or artifact.title),
        render_artifact_id=artifact.object_id, render_artifact_version=artifact.version,
        exact_video_sha256=payload.video_sha256, poster_sha256=_file_hash(poster, 16 * 1024 * 1024),
        captions_sha256=_file_hash(captions, 4 * 1024 * 1024) if captions else None,
        self_hosted_asset_uri="/discover-assets/media/" + payload.video_sha256 + ".mp4",
        duration_seconds=payload.duration_seconds, content_shape=shape, product_ids=products,
        primary_concept_keys=[primary_concept_key], destinations=selected, channel_copy=copy,
        manual_kit_destinations=[item for item in selected if item in MANUAL_DESTINATIONS],
        evidence_review_state=evidence_state,
        media_rights_state=rights_state if rights_state in {"pending", "passed", "blocked"} else "pending")
    package_json = distribution.model_dump(mode="json")
    package_id = "distribution_" + canonical_hash({"payload": package_json, "release": [release.object_id, release.version]})[:32]
    package = UniversalObject(
        object_id=package_id, object_type="distribution_package", title=f"Canonical distribution: {artifact.title}",
        purpose="Pin one exact video, evidence state, rights state, channel copy and destination set for review.",
        parent_ids=[artifact.object_id, release.object_id, *products], sources=artifact.sources,
        payload=package_json, metadata={"publication_allowed": False, "release_review_id": release.object_id,
            "release_review_version": release.version, "video_source_path": str(video.relative_to(ROOT)),
            "poster_source_path": str(poster.relative_to(ROOT)),
            "captions_source_path": str(captions.relative_to(ROOT)) if captions else None})
    package_hash = canonical_hash(package_json)
    request_payload = PublicationRequestPayload(
        summary=f"Approve or reject the exact package {package_id}; approval authorizes only its pinned destinations.",
        distribution_package_id=package_id, distribution_package_version=package.version,
        exact_package_sha256=package_hash, destinations=selected,
        requested_actions=["stage_owned_copy" if item == "owned_app" else
                           "api_upload_and_publish" if item in {"youtube", "linkedin"} else
                           "prepare_manual_posting_kit" for item in selected])
    request_id = "publication_" + canonical_hash({"package_id": package_id, "package_hash": package_hash})[:32]
    publication_request = UniversalObject(
        object_id=request_id, object_type="publication_request", title=f"Publication approval: {artifact.title}",
        purpose="Require human approval of the exact canonical video, metadata, disclosure and destinations.",
        parent_ids=[package_id, artifact.object_id, release.object_id], sources=artifact.sources,
        payload=request_payload.model_dump(mode="json"), metadata={"publication_allowed": False, "no_implicit_approval": True})
    return package, publication_request


def write_manual_kits(package: UniversalObject, root: Path = ROOT) -> Path:
    payload = DistributionPackagePayload.model_validate(package.payload)
    target = root / ".local" / "manual-posting-kits" / package.object_id
    target.mkdir(parents=True, exist_ok=True)
    os.chmod(target, 0o700)
    for destination in payload.manual_kit_destinations:
        copy = payload.channel_copy[destination]
        data = {"schema_version": "manual-posting-kit-1", "package_id": package.object_id,
                "exact_video_sha256": payload.exact_video_sha256, "video_uri": payload.self_hosted_asset_uri,
                "destination": destination, "title": copy.title, "text": copy.text, "tags": copy.tags,
                "disclosure": copy.disclosure, "canonical_app_link": copy.canonical_app_link,
                "instruction": "Upload the exact approved canonical video and paste this destination-specific copy."}
        path = target / f"{destination}.json"
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        os.chmod(path, 0o600)
    return target


def _receipt_path(request_id: str, destination: str) -> Path:
    target = ROOT / ".local" / "publishing" / "receipts" / request_id
    target.mkdir(parents=True, exist_ok=True)
    os.chmod(target, 0o700)
    return target / f"{destination}.json"


def _write_receipt(path: Path, value: dict[str, Any]):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def _token(name: str, file_name: str) -> str:
    direct = os.getenv(name, "").strip()
    if direct:
        return direct
    configured = os.getenv(file_name, "").strip()
    if configured:
        path = Path(configured).expanduser()
        if path.is_file():
            token = str(json.loads(path.read_text(encoding="utf-8")).get("access_token", "")).strip()
            if token:
                return token
    raise ContractViolationError(f"{name} or its local OAuth token file is not configured.")


def _request_json(url: str, method: str, body: dict[str, Any], headers: dict[str, str], timeout: int = 20):
    request = Request(url, data=json.dumps(body).encode(), method=method,
                      headers={"Content-Type": "application/json", **headers})
    with urlopen(request, timeout=timeout) as response:
        content = response.read(1024 * 1024)
        return response.status, dict(response.headers), json.loads(content) if content else {}


def _stage_owned(package, video: Path, poster: Path):
    target = ROOT / "apps" / "public" / "media"
    target.mkdir(parents=True, exist_ok=True)
    digest = package.payload["exact_video_sha256"]
    video_target, poster_target = target / f"{digest}.mp4", target / f"{digest}.jpg"
    if not video_target.exists():
        shutil.copyfile(video, video_target)
    if not poster_target.exists():
        shutil.copyfile(poster, poster_target)
    if _file_hash(video_target) != digest or _file_hash(poster_target, 16 * 1024 * 1024) != package.payload["poster_sha256"]:
        raise ContractViolationError("The owned-app copy failed exact hash verification.")
    copy = package.payload["channel_copy"]["owned_app"]
    manifest = {"schema_version": "canonical-video-public-1", "publication_state": "published",
                "package_id": package.object_id, "title": copy.get("title") or package.title,
                "summary": package.payload["summary"], "content_shape": package.payload["content_shape"],
                "products": package.payload["product_ids"], "primary_concepts": package.payload["primary_concept_keys"],
                "video_url": package.payload["self_hosted_asset_uri"],
                "poster_url": f"/discover-assets/media/{digest}.jpg", "exact_video_sha256": digest,
                "evidence_review_state": package.payload["evidence_review_state"],
                "media_rights_state": package.payload["media_rights_state"],
                "published_at": datetime.now(UTC).isoformat()}
    (target / f"{digest}.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"asset_uri": package.payload["self_hosted_asset_uri"]}


def _publish_youtube(package, video: Path):
    token = _token("YOUTUBE_OAUTH_ACCESS_TOKEN", "YOUTUBE_OAUTH_TOKEN_FILE")
    copy = package.payload["channel_copy"]["youtube"]
    metadata = {"snippet": {"title": (copy.get("title") or package.title)[:100],
                            "description": copy["text"][:5000], "tags": copy.get("tags", [])[:30],
                            "categoryId": os.getenv("YOUTUBE_CATEGORY_ID", "28")},
                "status": {"privacyStatus": os.getenv("YOUTUBE_PRIVACY_STATUS", "private"),
                           "selfDeclaredMadeForKids": False}}
    encoded = json.dumps(metadata).encode()
    init = Request("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                   data=encoded, method="POST", headers={"Authorization": "Bearer " + token,
                   "Content-Type": "application/json; charset=UTF-8", "Content-Length": str(len(encoded)),
                   "X-Upload-Content-Length": str(video.stat().st_size), "X-Upload-Content-Type": "video/mp4"})
    with urlopen(init, timeout=20) as response:
        location = response.headers.get("Location")
    if not location:
        raise ContractViolationError("YouTube did not return a resumable upload location.")
    upload = Request(location, data=video.read_bytes(), method="PUT",
                     headers={"Authorization": "Bearer " + token, "Content-Type": "video/mp4",
                              "Content-Length": str(video.stat().st_size)})
    with urlopen(upload, timeout=180) as response:
        result = json.loads(response.read(1024 * 1024))
    return {"provider_id": result.get("id"), "url": "https://www.youtube.com/watch?v=" + str(result.get("id"))}


def _publish_linkedin(package, video: Path):
    token = _token("LINKEDIN_ACCESS_TOKEN", "LINKEDIN_OAUTH_TOKEN_FILE")
    owner = os.getenv("LINKEDIN_PERSON_URN", "").strip()
    version = os.getenv("LINKEDIN_API_VERSION", "202608").strip()
    if not owner.startswith(("urn:li:person:", "urn:li:organization:")):
        raise ContractViolationError("LINKEDIN_PERSON_URN must identify the approved author.")
    headers = {"Authorization": "Bearer " + token, "Linkedin-Version": version,
               "X-Restli-Protocol-Version": "2.0.0"}
    _, _, initialized = _request_json("https://api.linkedin.com/rest/videos?action=initializeUpload", "POST",
        {"initializeUploadRequest": {"owner": owner, "fileSizeBytes": video.stat().st_size,
                                     "uploadCaptions": False, "uploadThumbnail": False}}, headers)
    value, etags = initialized["value"], []
    with video.open("rb") as source:
        for instruction in value["uploadInstructions"]:
            first, last = int(instruction["firstByte"]), int(instruction["lastByte"])
            source.seek(first)
            body = source.read(last - first + 1)
            request = Request(instruction["uploadUrl"], data=body, method="PUT",
                              headers={"Content-Type": "application/octet-stream", "Content-Length": str(len(body))})
            with urlopen(request, timeout=120) as response:
                etag = response.headers.get("ETag") or response.headers.get("etag")
            if not etag:
                raise ContractViolationError("LinkedIn did not acknowledge an uploaded video part.")
            etags.append(etag)
    _request_json("https://api.linkedin.com/rest/videos?action=finalizeUpload", "POST",
        {"finalizeUploadRequest": {"video": value["video"], "uploadToken": value.get("uploadToken", ""),
                                   "uploadedPartIds": etags}}, headers)
    copy = package.payload["channel_copy"]["linkedin"]
    status, response_headers, _ = _request_json("https://api.linkedin.com/rest/posts", "POST",
        {"author": owner, "commentary": copy["text"], "visibility": "PUBLIC",
         "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
         "content": {"media": {"title": copy.get("title") or package.title, "id": value["video"]}},
         "lifecycleState": "PUBLISHED", "isReshareDisabledByAuthor": False}, headers)
    return {"provider_id": response_headers.get("x-restli-id"), "video_urn": value["video"], "status": status}


def execute_approved_publication(store, request_id: str, destinations: list[str] | None = None):
    if os.getenv("ALLOW_APPROVED_PUBLICATION") != "1":
        raise ContractViolationError("Publishing kill switch is closed; enable it only for an approved run.")
    publication = store.get(request_id)
    if publication.object_type != "publication_request" or publication.review.state.value != "approved":
        raise ContractViolationError("A human-approved publication_request is required.")
    request_payload = PublicationRequestPayload.model_validate(publication.payload)
    package = store.get(request_payload.distribution_package_id)
    distribution = DistributionPackagePayload.model_validate(package.payload)
    if package.version != request_payload.distribution_package_version or canonical_hash(distribution.model_dump(mode="json")) != request_payload.exact_package_sha256:
        raise ContractViolationError("The approved package version or hash changed.")
    selected = destinations or request_payload.destinations
    if not set(selected).issubset(set(request_payload.destinations)):
        raise ContractViolationError("Execution cannot add an unapproved destination.")
    artifact = store.get(distribution.render_artifact_id)
    if artifact.version != distribution.render_artifact_version or artifact.review.state.value != "approved":
        raise ContractViolationError("The exact render artifact is not currently human-approved.")
    live = assess_release(store, artifact.object_id)
    if not all(item["state"] == "passed" for item in live["packet"]["checks"]):
        raise ContractViolationError("A current release check is not passing; publication is blocked.")
    artifact_payload = RenderArtifactPayload.model_validate(artifact.payload)
    video = _safe_render_path(artifact_payload.artifact_uri, {".mp4"})
    poster = (ROOT / package.metadata["poster_source_path"]).resolve()
    if not poster.is_relative_to((ROOT / ".local").resolve()):
        raise ContractViolationError("The approved poster path is outside local governed storage.")
    if _file_hash(video) != distribution.exact_video_sha256 or _file_hash(poster, 16 * 1024 * 1024) != distribution.poster_sha256:
        raise ContractViolationError("An approved media file changed before publication.")
    results = {}
    for destination in selected:
        receipt = _receipt_path(publication.object_id, destination)
        if receipt.exists():
            results[destination] = json.loads(receipt.read_text(encoding="utf-8"))
            continue
        started = {"schema_version": "publication-receipt-1", "request_id": publication.object_id,
                   "package_id": package.object_id, "destination": destination,
                   "exact_package_sha256": request_payload.exact_package_sha256,
                   "state": "started", "started_at": datetime.now(UTC).isoformat(), "automatic_retry": False}
        _write_receipt(receipt, started)
        try:
            if destination == "owned_app":
                detail, state = _stage_owned(package, video, poster), "published"
            elif destination == "youtube":
                detail, state = _publish_youtube(package, video), "published"
            elif destination == "linkedin":
                detail, state = _publish_linkedin(package, video), "published"
            else:
                detail, state = {"kit_directory": str(write_manual_kits(package).relative_to(ROOT))}, "manual_kit_ready"
            completed = started | {"state": state, "completed_at": datetime.now(UTC).isoformat(), "detail": detail}
            _write_receipt(receipt, completed)
            results[destination] = completed
        except HTTPError as error:
            failed = started | {"state": "provider_rejected", "completed_at": datetime.now(UTC).isoformat(),
                                "http_status": error.code, "automatic_retry": False}
            _write_receipt(receipt, failed)
            results[destination] = failed
        except (URLError, TimeoutError, OSError, KeyError, ValueError, ContractViolationError) as error:
            ambiguous = started | {"state": "ambiguous_blocked", "completed_at": datetime.now(UTC).isoformat(),
                                   "error_type": type(error).__name__, "automatic_retry": False}
            _write_receipt(receipt, ambiguous)
            results[destination] = ambiguous
    return results
