"""Rights-aware reusable image catalog with a bounded Gemini fallback."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import re
import sqlite3
import tempfile
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image

from packages.contracts.media import MediaAssetPayload
from packages.contracts.object import ActorType, UniversalObject
from packages.runtime.context import ROOT, reject_obvious_credentials

DEFAULT_CATALOG = ROOT / ".local/media-catalog/catalog.sqlite3"
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 4096 * 4096
TOKEN = re.compile(r"[a-z0-9][a-z0-9_-]{1,63}")


class MediaCatalogError(ValueError):
    pass


class PaidGenerationBlocked(MediaCatalogError):
    pass


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _tokens(value) -> set[str]:
    if isinstance(value, list):
        value = " ".join(str(item) for item in value)
    return set(TOKEN.findall(str(value).casefold()))


def _atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_json(path: Path, value) -> None:
    _atomic_bytes(path, json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False).encode() + b"\n")


def _allowed_path(path: Path, root: Path, policy: dict | None = None) -> Path:
    root = Path(root).resolve()
    resolved = Path(path).resolve()
    roots = (policy or {}).get("catalog", {}).get("allowed_asset_roots") or [
        ".local/assets/kinetic", "assets/media/commons", "assets/media/generated"
    ]
    allowed = [(root / item).resolve() for item in roots]
    if not any(resolved.is_relative_to(directory) for directory in allowed):
        raise MediaCatalogError("Image is outside the admitted media roots.")
    if not resolved.is_file():
        raise MediaCatalogError("Catalog image file does not exist.")
    return resolved


def _inspect_image(path: Path) -> tuple[str, int, int, str]:
    data = path.read_bytes()
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise MediaCatalogError("Image is empty or exceeds the catalog byte limit.")
    try:
        with Image.open(path) as image:
            width, height = image.size
            image_format = image.format
            image.verify()
    except Exception as exc:
        raise MediaCatalogError("Catalog file is not a valid supported image.") from exc
    if not image_format or width < 200 or height < 200 or width * height > MAX_IMAGE_PIXELS:
        raise MediaCatalogError("Image dimensions are outside the catalog envelope.")
    return _digest_bytes(data), width, height, image_format.casefold()


class MediaCatalog:
    def __init__(self, path: Path = DEFAULT_CATALOG, root: Path = ROOT, policy: dict | None = None):
        self.path = Path(path)
        self.root = Path(root).resolve()
        self.policy = policy or {}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self.path.parent, 0o700)
        descriptor = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(descriptor)
        os.chmod(self.path, 0o600)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS media_assets(
                    asset_id TEXT PRIMARY KEY,
                    sha256 TEXT NOT NULL UNIQUE,
                    asset_uri TEXT NOT NULL,
                    width INTEGER NOT NULL,
                    height INTEGER NOT NULL,
                    image_format TEXT NOT NULL,
                    origin TEXT NOT NULL,
                    rights_state TEXT NOT NULL,
                    commercial_use_allowed INTEGER,
                    representation TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_used_at TEXT,
                    use_count INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS media_usage(
                    usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_id TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    used_at TEXT NOT NULL,
                    FOREIGN KEY(asset_id) REFERENCES media_assets(asset_id)
                );
                CREATE INDEX IF NOT EXISTS media_asset_rights ON media_assets(rights_state, commercial_use_allowed);
            """)

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def register(self, path: Path, metadata: dict) -> dict:
        reject_obvious_credentials(metadata)
        admitted = _allowed_path(path, self.root, self.policy)
        sha256, width, height, image_format = _inspect_image(admitted)
        required = {"origin", "subject", "scene", "style", "purpose", "tags", "rights_state",
                    "commercial_use_allowed", "representation", "not_product_photography",
                    "depiction_limits", "cost_usd"}
        missing = sorted(required - set(metadata))
        if missing:
            raise MediaCatalogError("Catalog metadata is incomplete: " + ", ".join(missing))
        if metadata["rights_state"] not in {"unassessed", "documented", "denied"}:
            raise MediaCatalogError("Catalog rights state is invalid.")
        if metadata["commercial_use_allowed"] not in {True, False, None}:
            raise MediaCatalogError("Commercial-use state must be true, false or unknown.")
        if not isinstance(metadata["tags"], list) or not 1 <= len(metadata["tags"]) <= 40:
            raise MediaCatalogError("Catalog requires one to forty semantic tags.")
        if not isinstance(metadata["depiction_limits"], list) or not metadata["depiction_limits"]:
            raise MediaCatalogError("Catalog requires explicit depiction limits.")
        if float(metadata["cost_usd"]) < 0:
            raise MediaCatalogError("Catalog cost cannot be negative.")
        now = datetime.now(UTC).isoformat()
        aspect = width / height
        enriched = {
            **metadata,
            "sha256": sha256,
            "width": width,
            "height": height,
            "image_format": image_format,
            "aspect_ratio": round(aspect, 6),
            "orientation": "square" if 0.95 <= aspect <= 1.05 else "landscape" if aspect > 1 else "portrait",
        }
        asset_id = "media_" + sha256[:32]
        uri = str(admitted.relative_to(self.root))
        with self._connect() as db:
            row = db.execute("SELECT * FROM media_assets WHERE sha256=?", (sha256,)).fetchone()
            if row:
                previous = json.loads(row["metadata_json"])
                if previous.get("rights_state") == "denied" and metadata["rights_state"] != "denied":
                    raise MediaCatalogError("Denied media cannot be silently reclassified.")
                merged_tags = sorted(set(previous.get("tags", [])) | set(metadata["tags"]))[:40]
                enriched["tags"] = merged_tags
                db.execute("""UPDATE media_assets SET metadata_json=?,updated_at=?,
                              rights_state=?,commercial_use_allowed=? WHERE sha256=?""",
                           (_canonical(enriched), now, metadata["rights_state"],
                            None if metadata["commercial_use_allowed"] is None else int(metadata["commercial_use_allowed"]), sha256))
            else:
                db.execute("""INSERT INTO media_assets
                    (asset_id,sha256,asset_uri,width,height,image_format,origin,rights_state,
                     commercial_use_allowed,representation,metadata_json,created_at,updated_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (asset_id, sha256, uri, width, height, image_format, metadata["origin"],
                     metadata["rights_state"],
                     None if metadata["commercial_use_allowed"] is None else int(metadata["commercial_use_allowed"]),
                     metadata["representation"], _canonical(enriched), now, now))
            db.commit()
        return {"asset_id": asset_id, "sha256": sha256, "asset_uri": uri, "metadata": enriched}

    def search(self, request: dict, minimum_score: float | None = None) -> dict | None:
        normalized = normalize_request(request)
        threshold = minimum_score if minimum_score is not None else float(
            self.policy.get("catalog", {}).get("minimum_match_score", 0.45)
        )
        request_terms = _tokens([
            normalized["subject"], normalized["scene"], normalized["style"],
            normalized["purpose"], *normalized["required_tags"],
        ])
        candidates = []
        with self._connect() as db:
            rows = db.execute("SELECT * FROM media_assets WHERE rights_state!='denied'").fetchall()
            for row in rows:
                metadata = json.loads(row["metadata_json"])
                commercial = None if row["commercial_use_allowed"] is None else bool(row["commercial_use_allowed"])
                if normalized["for_publication"] and not (row["rights_state"] == "documented" and commercial is True):
                    continue
                if normalized["exact_product_identity"]:
                    if metadata.get("exact_product_identity") != normalized["exact_product_identity"]:
                        continue
                if metadata.get("not_product_photography") and normalized["representation"] == "product_photography":
                    continue
                asset_terms = _tokens([
                    metadata.get("subject", ""), metadata.get("scene", ""), metadata.get("style", ""),
                    metadata.get("purpose", ""), *metadata.get("tags", []),
                ])
                overlap = len(request_terms & asset_terms) / max(1, len(request_terms))
                required = set(normalized["required_tags"])
                tag_fit = len(required & set(metadata.get("tags", []))) / max(1, len(required)) if required else 1.0
                aspect_fit = 1.0 if normalized["orientation"] == metadata.get("orientation") else 0.4
                score = round(0.6 * overlap + 0.3 * tag_fit + 0.1 * aspect_fit, 6)
                if score >= threshold:
                    candidates.append((score, row, metadata))
            if not candidates:
                return None
            score, row, metadata = sorted(candidates, key=lambda item: (-item[0], item[1]["use_count"], item[1]["asset_id"]))[0]
            path = _allowed_path(self.root / row["asset_uri"], self.root, self.policy)
            current_sha, _, _, _ = _inspect_image(path)
            if current_sha != row["sha256"]:
                raise MediaCatalogError("Catalog bytes changed after registration.")
            now = datetime.now(UTC).isoformat()
            request_hash = hashlib.sha256(_canonical(normalized).encode()).hexdigest()
            db.execute("UPDATE media_assets SET last_used_at=?,use_count=use_count+1 WHERE asset_id=?",
                       (now, row["asset_id"]))
            db.execute("INSERT INTO media_usage(asset_id,request_hash,purpose,used_at) VALUES(?,?,?,?)",
                       (row["asset_id"], request_hash, normalized["purpose"], now))
            db.commit()
        return {
            "resolution": "catalog_reuse",
            "asset_id": row["asset_id"],
            "asset_uri": row["asset_uri"],
            "sha256": row["sha256"],
            "match_score": score,
            "metadata": metadata,
        }


def normalize_request(request: dict) -> dict:
    reject_obvious_credentials(request)
    required = {"subject", "scene", "style", "purpose", "aspect_ratio", "required_tags",
                "for_publication", "representation", "exact_product_identity"}
    if set(request) != required:
        raise MediaCatalogError("Image request must use the exact catalog request contract.")
    for key in ("subject", "scene", "style", "purpose", "representation"):
        if not isinstance(request[key], str) or not 2 <= len(request[key].strip()) <= 500:
            raise MediaCatalogError(f"Invalid image request field: {key}")
    if not re.fullmatch(r"\d{1,2}:\d{1,2}", request["aspect_ratio"]):
        raise MediaCatalogError("Aspect ratio must use W:H.")
    width, height = (int(value) for value in request["aspect_ratio"].split(":"))
    if width < 1 or height < 1:
        raise MediaCatalogError("Aspect ratio values must be positive.")
    if not isinstance(request["required_tags"], list) or len(request["required_tags"]) > 20:
        raise MediaCatalogError("Image request tags exceed their limit.")
    tags = sorted({_token for item in request["required_tags"] for _token in _tokens(item)})
    if not isinstance(request["for_publication"], bool):
        raise MediaCatalogError("Publication intent must be explicit.")
    identity = request["exact_product_identity"]
    if identity is not None and (not isinstance(identity, str) or not identity.strip()):
        raise MediaCatalogError("Exact product identity must be null or nonempty.")
    aspect = width / height
    return {
        **request,
        "subject": request["subject"].strip(),
        "scene": request["scene"].strip(),
        "style": request["style"].strip(),
        "purpose": request["purpose"].strip(),
        "required_tags": tags,
        "orientation": "square" if 0.95 <= aspect <= 1.05 else "landscape" if aspect > 1 else "portrait",
    }


def register_file(path: Path, metadata: dict, *, root: Path = ROOT, policy: dict | None = None) -> dict:
    catalog_path = Path(root) / ".local/media-catalog/catalog.sqlite3"
    return MediaCatalog(catalog_path, root, policy).register(path, metadata)


def resolve_image(request: dict, *, root: Path = ROOT, policy_path: Path | None = None, generator=None) -> dict:
    policy_file = Path(policy_path or (Path(root) / "config/media-generation-policy.json"))
    policy = json.loads(policy_file.read_text(encoding="utf-8"))
    catalog = MediaCatalog(Path(root) / policy["catalog"]["path"], root, policy)
    match = catalog.search(request)
    if match:
        return match
    normalized = normalize_request(request)
    if normalized["exact_product_identity"]:
        return {
            "resolution": "missing",
            "reason": "Exact named-product imagery cannot be synthesized by policy; obtain lawful exact-product media.",
        }
    if generator is None:
        return {
            "resolution": "generation_candidate",
            "reason": "No rights-compatible catalog match exists; generation requires shared-budget admission.",
            "request": normalized,
        }
    return generator.generate(normalized, catalog)


class GeminiImageGenerator:
    """Single-attempt Gemini adapter. Caller must provide shared-budget admission."""

    def __init__(self, api_key: str, policy: dict, admission, store=None, root: Path = ROOT):
        self.api_key = api_key
        self.policy = policy
        self.admission = admission
        self.store = store
        self.root = Path(root).resolve()

    def _estimate(self, prompt: str) -> float:
        pricing = self.policy["pricing"]
        if date.today() > date.fromisoformat(pricing["recheck_after"]):
            raise PaidGenerationBlocked("Gemini image pricing is stale; refresh it before paid generation.")
        estimated_tokens = math.ceil(len(prompt) / 4)
        estimate = float(pricing["image_output_usd"]) + (
            estimated_tokens * float(pricing["text_input_usd_per_million_tokens"]) / 1_000_000
        )
        conservative = max(estimate, float(pricing["conservative_complete_request_estimate_usd"]))
        if conservative > float(pricing["hard_maximum_per_image_usd"]):
            raise PaidGenerationBlocked("Complete image request estimate exceeds the USD 0.10 hard cap.")
        return conservative

    def generate(self, request: dict, catalog: MediaCatalog) -> dict:
        generation = self.policy["generation"]
        representation = self.policy["representation"]
        if not self.api_key.strip():
            raise PaidGenerationBlocked("GEMINI_API_KEY is not configured locally.")
        if request["exact_product_identity"]:
            raise PaidGenerationBlocked("Policy forbids synthesized exact named-product imagery.")
        constraints = ". ".join(representation["required_prompt_constraints"])
        prompt = (
            f"Create a {request['aspect_ratio']} {request['style']} image for {request['purpose']}. "
            f"Subject: {request['subject']}. Scene: {request['scene']}. "
            f"Visual tags: {', '.join(request['required_tags'])}. Constraints: {constraints}."
        )
        if len(prompt) > generation["maximum_prompt_characters"]:
            raise MediaCatalogError("Generated image prompt exceeds its bounded contract.")
        request_hash = hashlib.sha256(_canonical({"request": request, "prompt": prompt, "model": generation["model"]}).encode()).hexdigest()
        attempts = self.root / ".local/media-catalog/generation-attempts"
        attempts.mkdir(parents=True, exist_ok=True)
        os.chmod(attempts, 0o700)
        attempt_path = attempts / f"{request_hash}.json"
        if attempt_path.exists():
            raise PaidGenerationBlocked("This generation request already has an attempt receipt and cannot be retried automatically.")
        estimated_usd = self._estimate(prompt)
        self.admission(request_hash, estimated_usd)
        submitted = {
            "schema_version": "gemini-image-attempt-1",
            "request_hash": request_hash,
            "model": generation["model"],
            "estimated_cost_usd": estimated_usd,
            "state": "submitted",
            "submitted_at": datetime.now(UTC).isoformat(),
        }
        _atomic_json(attempt_path, submitted)
        body = _canonical({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": generation["response_modalities"]},
        }).encode()
        request_object = Request(
            generation["endpoint"],
            data=body,
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
        )
        try:
            with urlopen(request_object, timeout=60) as response:
                raw = response.read(generation["maximum_response_bytes"] + 1)
        except HTTPError as exc:
            submitted.update({"state": "provider_rejected", "http_status": exc.code, "completed_at": datetime.now(UTC).isoformat()})
            _atomic_json(attempt_path, submitted)
            raise MediaCatalogError(f"Gemini rejected the single image request with HTTP {exc.code}; it was not retried.") from exc
        except (URLError, TimeoutError) as exc:
            submitted.update({"state": "ambiguous_potentially_billable", "completed_at": datetime.now(UTC).isoformat()})
            _atomic_json(attempt_path, submitted)
            raise MediaCatalogError("Gemini image result is ambiguous and potentially billable; automatic retry is forbidden.") from exc
        if not raw or len(raw) > generation["maximum_response_bytes"]:
            submitted.update({"state": "ambiguous_potentially_billable", "completed_at": datetime.now(UTC).isoformat()})
            _atomic_json(attempt_path, submitted)
            raise MediaCatalogError("Gemini image response was empty or oversized; automatic retry is forbidden.")
        response = json.loads(raw)
        inline = None
        for candidate in response.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                data = part.get("inlineData") or part.get("inline_data")
                if data and data.get("data"):
                    inline = data
                    break
            if inline:
                break
        if not inline:
            submitted.update({"state": "completed_without_image", "completed_at": datetime.now(UTC).isoformat()})
            _atomic_json(attempt_path, submitted)
            raise MediaCatalogError("Gemini completed without an image; automatic retry is forbidden.")
        try:
            image_bytes = base64.b64decode(inline["data"], validate=True)
        except (ValueError, TypeError) as exc:
            submitted.update({"state": "ambiguous_invalid_image_data", "completed_at": datetime.now(UTC).isoformat()})
            _atomic_json(attempt_path, submitted)
            raise MediaCatalogError("Gemini returned invalid image bytes; automatic retry is forbidden.") from exc
        mime = str(inline.get("mimeType") or inline.get("mime_type") or "").casefold()
        extension = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}.get(mime)
        if extension is None or len(image_bytes) > MAX_IMAGE_BYTES:
            raise MediaCatalogError("Gemini output format or size is outside the media envelope.")
        sha256 = _digest_bytes(image_bytes)
        directory = self.root / "assets/media/generated" / sha256
        image_path = directory / ("image" + extension)
        _atomic_bytes(image_path, image_bytes)
        metadata = {
            "origin": "gemini_generated",
            "subject": request["subject"],
            "scene": request["scene"],
            "style": request["style"],
            "purpose": request["purpose"],
            "tags": request["required_tags"] or ["generated", "concept"],
            "rights_state": "unassessed",
            "commercial_use_allowed": None,
            "source_uri": self.policy["pricing"]["official_source"],
            "generator_model": generation["model"],
            "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest(),
            "request_hash": request_hash,
            "representation": "concept_illustration",
            "not_product_photography": True,
            "depiction_limits": [
                "AI-generated conceptual illustration; not a named product, camera sample or factual feature demonstration.",
                "Requires visual and rights review before public use.",
            ],
            "cost_usd": estimated_usd,
            "publication_allowed": False,
        }
        _atomic_json(directory / "metadata.json", metadata)
        registered = catalog.register(image_path, metadata)
        governed_id = None
        if self.store is not None:
            payload = MediaAssetPayload(
                summary="AI-generated conceptual background retained for reuse after a catalog miss.",
                asset_kind="image",
                asset_uri=registered["asset_uri"],
                sha256=registered["sha256"],
                provenance_kind="generated_recipe",
                provenance_reference=f"{generation['model']}; prompt hash {metadata['prompt_hash']}; attempt {request_hash}",
                representation="concept_illustration",
                private_preview_allowed=True,
                rights_state="unassessed",
                commercial_use_allowed=None,
                credit="AI-generated conceptual illustration; not product photography. Public use requires visual and rights review.",
            )
            item = UniversalObject(
                object_id=registered["asset_id"], object_type="media_asset",
                title="Generated visual: " + request["subject"][:200],
                purpose="Provide a reusable conceptual image only when no lawful catalog fit exists.",
                payload=payload.model_dump(mode="json"),
                metadata={**metadata, "publication_allowed": False},
            )
            existing = {obj.object_id for obj in self.store.list_objects()}
            if item.object_id not in existing:
                self.store.capture(item, actor_id="agent:media-catalog", actor_type=ActorType.agent,
                                   idempotency_key="generated-" + request_hash,
                                   request_input={"request_hash": request_hash, "sha256": registered["sha256"]})
            governed_id = item.object_id
        submitted.update({
            "state": "completed",
            "completed_at": datetime.now(UTC).isoformat(),
            "sha256": registered["sha256"],
            "catalog_asset_id": registered["asset_id"],
        })
        _atomic_json(attempt_path, submitted)
        return {
            "resolution": "generated_and_cataloged",
            "asset_id": registered["asset_id"],
            "asset_uri": registered["asset_uri"],
            "sha256": registered["sha256"],
            "governed_object_id": governed_id,
            "estimated_cost_usd": estimated_usd,
            "publication_allowed": False,
        }
