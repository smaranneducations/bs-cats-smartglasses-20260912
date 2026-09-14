"""Bounded private render retrieval using the service's short-lived identity."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile
import threading
from urllib.parse import quote

import httpx

from packages.cloud.firestore_transport import ShortLivedGoogleToken

BUCKET = "bs-cats-smartglasses-20260912-assets"
_lock = threading.Lock()


def render_path(root: Path, uri: str) -> Path:
    allowed = (root / ".local/production-renders").resolve()
    path = (root / uri).resolve()
    if not path.is_relative_to(allowed) or path == allowed:
        raise ValueError("Render path is outside the private output scope.")
    return path


def materialize_render(root: Path, uri: str, expected_hash: str | None = None,
                       maximum_bytes: int = 64 * 1024 * 1024, *, client=None, token_source=None) -> Path:
    path = render_path(root, uri)
    with _lock:
        if path.is_file():
            if not 0 < path.stat().st_size <= maximum_bytes:
                raise ValueError("Render exceeds the bounded file size.")
            if expected_hash and hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
                raise ValueError("Render bytes do not match the recorded identity.")
            return path
        if os.getenv("PRIVATE_MEDIA_BUCKET") != BUCKET:
            raise FileNotFoundError("Private cloud media storage is not configured.")
        relative = path.relative_to((root / ".local/production-renders").resolve())
        object_name = "private-renders/" + relative.as_posix()
        url = "https://storage.googleapis.com/storage/v1/b/" + BUCKET + "/o/" + quote(object_name, safe="")
        identity = token_source or ShortLivedGoogleToken()
        headers = {"Authorization": "Bearer " + identity()}
        owned = client is None
        session = client or httpx.Client(timeout=20, follow_redirects=False, trust_env=False)
        temporary = None
        try:
            metadata = session.get(url, headers=headers)
            if metadata.status_code != 200:
                raise FileNotFoundError("Private media is unavailable to this service identity.")
            value = metadata.json()
            size = int(value["size"])
            generation = str(value["generation"])
            if not generation.isdigit() or not 0 < size <= maximum_bytes:
                raise ValueError("Cloud media exceeds the bounded file size.")
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
                temporary = Path(output.name)
                hasher, length = hashlib.sha256(), 0
                with session.stream("GET", url, headers=headers,
                                    params={"alt": "media", "generation": generation}) as response:
                    if response.status_code != 200:
                        raise FileNotFoundError("Pinned private media generation is unavailable.")
                    for chunk in response.iter_bytes(65536):
                        length += len(chunk)
                        if length > maximum_bytes or length > size:
                            raise ValueError("Cloud media exceeded its declared size.")
                        output.write(chunk)
                        hasher.update(chunk)
                if length != size or (expected_hash and hasher.hexdigest() != expected_hash):
                    raise ValueError("Downloaded media does not match its recorded identity.")
            os.replace(temporary, path)
            temporary = None
            return path
        except (httpx.HTTPError, KeyError, TypeError, OverflowError) as exc:
            raise FileNotFoundError("Private media retrieval did not complete.") from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            if owned:
                session.close()
