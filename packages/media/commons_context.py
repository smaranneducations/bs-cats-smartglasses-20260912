"""Bounded CC0 context-image acquisition with retained source evidence.

This is not a general stock-image scraper or a product-photo rights classifier.
"""

import hashlib
import io
import json
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from PIL import Image
from packages.media.catalog import register_file

ROOT = Path(__file__).resolve().parents[2]
LICENSE = "https://creativecommons.org/publicdomain/zero/1.0/"
MAX_IMAGE_BYTES = 6 * 1024 * 1024
MAX_IMAGE_PIXELS = 6_000_000
USER_AGENT = "SmartGlassesEvidencePrototype/0.1 (bounded public CC0 media research)"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain(value):
    parser = TextOnly()
    parser.feed(str(value))
    return " ".join(" ".join(parser.parts).split())


def allowed_url(url, *, image=False):
    parsed = urlparse(url)
    hosts = {"upload.wikimedia.org", "thumb.wikimedia.org"} if image else {"commons.wikimedia.org"}
    if (parsed.scheme != "https" or parsed.hostname not in hosts or parsed.username or parsed.password
            or parsed.port not in (None, 443) or parsed.fragment):
        raise ValueError("The source URL is outside the permitted Wikimedia endpoint")
    if image and not parsed.path.startswith("/wikipedia/commons/"):
        raise ValueError("The image path is outside Wikimedia Commons")
    if not image and parsed.path != "/w/api.php":
        raise ValueError("Only the metadata API is permitted")
    return url


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def fetch(url, *, image=False):
    allowed_url(url, image=image)
    opener = build_opener(ProxyHandler({}), NoRedirects())
    limit = MAX_IMAGE_BYTES if image else 1024 * 1024
    with opener.open(Request(url, headers={"User-Agent": USER_AGENT}), timeout=20) as response:
        body = response.read(limit + 1)
    if not body or len(body) > limit:
        raise ValueError("Source response is empty or exceeds the acquisition limit")
    return body


def validate_metadata(page):
    if not isinstance(page.get("pageid"), int) or not isinstance(page.get("lastrevid"), int) or page.get("missing"):
        raise ValueError("An exact source page and revision are required")
    info = page.get("imageinfo", [{}])[0]
    metadata = info.get("extmetadata", {})
    values = {key: plain(value.get("value", "")) for key, value in metadata.items()}
    license_url = urlparse(values.get("LicenseUrl", ""))
    if (values.get("LicenseShortName") != "CC0" or license_url.hostname != "creativecommons.org"
            or license_url.scheme not in ("https", "http") or license_url.username or license_url.password
            or license_url.port is not None or not license_url.path.startswith("/publicdomain/zero/1.0/")):
        raise ValueError("This importer only accepts an explicit file-level CC0 dedication")
    if values.get("Credit", "").casefold() != "own work" or not values.get("Artist"):
        raise ValueError("A named uploader-as-creator provenance record is required")
    if values.get("Restrictions", "").strip():
        raise ValueError("Additional stated restrictions require separate assessment")
    width, height = info.get("thumbwidth", 0), info.get("thumbheight", 0)
    if not isinstance(width, int) or not isinstance(height, int) or not 1280 <= width <= 1920 or not 1 <= height <= 3000 or width * height > MAX_IMAGE_PIXELS:
        raise ValueError("The provided thumbnail exceeds the image envelope")
    allowed_url(info.get("thumburl", ""), image=True)
    return {"creator": values["Artist"], "source_credit": values["Credit"],
            "license": "CC0-1.0", "license_uri": LICENSE,
            "download_uri": info["thumburl"], "width": width, "height": height}


def inspect_bytes(data, width, height):
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("The downloaded image exceeds the byte limit")
    with Image.open(io.BytesIO(data)) as image:
        if image.format != "JPEG" or image.size != (width, height) or width * height > MAX_IMAGE_PIXELS:
            raise ValueError("Downloaded pixels do not match the admitted JPEG metadata")
        image.verify()


def acquire(titles, *, root=ROOT, fetcher=fetch):
    if not 1 <= len(titles) <= 3 or len(set(titles)) != len(titles) or any(not title.startswith("File:") or len(title) > 240 for title in titles):
        raise ValueError("Supply one to three unique explicit Commons file titles")
    parameters = {"action": "query", "format": "json", "formatversion": "2",
                  "prop": "imageinfo|info", "titles": "|".join(titles),
                  "iiprop": "url|size|sha1|extmetadata", "iiurlwidth": "1920", "maxlag": "5"}
    api_uri = "https://commons.wikimedia.org/w/api.php?" + urlencode(parameters)
    body = json.loads(fetcher(api_uri))
    if "error" in body:
        raise ValueError("The source API declined this bounded request")
    pages = body.get("query", {}).get("pages", [])
    if len(pages) != len(titles) or {page.get("title") for page in pages} != set(titles):
        raise ValueError("The source response did not identify the exact requested files")
    candidates = [(page, validate_metadata(page)) for page in pages]
    root = Path(root).resolve()
    base = (root / "assets/media/commons").resolve()
    if not base.is_relative_to(root):
        raise ValueError("The media destination escapes the workspace")
    results = []
    for page, admission in candidates:
        image = fetcher(admission["download_uri"], image=True)
        inspect_bytes(image, admission["width"], admission["height"])
        image_hash = digest(image)
        directory = base / f"{page['pageid']}-{page['lastrevid']}-{image_hash[:12]}"
        directory.mkdir(parents=True, exist_ok=False)
        image_path = directory / "context.jpg"
        image_path.write_bytes(image)
        permalink = f"https://commons.wikimedia.org/w/index.php?curid={page['pageid']}&oldid={page['lastrevid']}"
        receipt = {"schema_version": "commons-context-receipt-1",
                   "observed_at": datetime.now(timezone.utc).isoformat(),
                   "title": page["title"], "page_id": page["pageid"], "page_revision": page["lastrevid"],
                   "source_permalink": permalink, "api_uri": api_uri, **admission,
                   "asset_uri": str(image_path.relative_to(root)), "sha256": image_hash,
                   "evidence_metadata_sha256": digest(canonical(page)), "evidence_metadata": page,
                   "representation_detail": "context_photograph", "visual_risk_review": "pending",
                   "not_product_photography": True, "not_camera_sample": True,
                   "publication_approval": False}
        receipt_path = directory / "receipt.json"
        receipt_path.write_bytes(json.dumps(receipt, indent=2, ensure_ascii=True).encode() + b"\n")
        catalog = register_file(image_path, {
            "origin": "open_license",
            "subject": receipt["title"][5:],
            "scene": "licensed context photograph",
            "style": "photographic",
            "purpose": "reusable visual context",
            "tags": sorted({"context", "photograph", *plain(receipt["title"][5:]).casefold().split()}),
            "rights_state": "documented",
            "commercial_use_allowed": True,
            "license_uri": LICENSE,
            "source_uri": permalink,
            "creator": admission["creator"],
            "representation": "concept_illustration",
            "not_product_photography": True,
            "depiction_limits": ["Context photograph only; do not identify it as a product image or camera sample."],
            "cost_usd": 0.0,
        }, root=root)
        results.append({"receipt": str(receipt_path), "image": str(image_path),
                        "creator": admission["creator"], "title": page["title"], "sha256": image_hash,
                        "catalog_asset_id": catalog["asset_id"]})
    return results


def candidate(receipt_path, visual_note, *, root=ROOT):
    root = Path(root).resolve()
    base = (root / "assets/media/commons").resolve()
    path = Path(receipt_path).resolve()
    if not base.is_relative_to(root) or not path.is_relative_to(base) or path.name != "receipt.json":
        raise ValueError("The receipt is outside the governed media directory")
    raw = path.read_bytes()
    if len(raw) > 1024 * 1024:
        raise ValueError("Receipt exceeds its size limit")
    receipt = json.loads(raw)
    if receipt.get("schema_version") != "commons-context-receipt-1":
        raise ValueError("Unsupported media receipt")
    page = receipt["evidence_metadata"]
    admission = validate_metadata(page)
    if digest(canonical(page)) != receipt["evidence_metadata_sha256"] or any(receipt.get(key) != value for key, value in admission.items()):
        raise ValueError("Receipt metadata has changed")
    image_path = (root / receipt["asset_uri"]).resolve()
    if not image_path.is_relative_to(base):
        raise ValueError("The image escapes the governed media directory")
    image = image_path.read_bytes()
    inspect_bytes(image, admission["width"], admission["height"])
    if digest(image) != receipt["sha256"]:
        raise ValueError("The image no longer matches its provenance receipt")
    if not 30 <= len(visual_note.strip()) <= 1000:
        raise ValueError("Record a bounded visual-risk assessment, not an automatic clearance")
    credit = f"{receipt['title'][5:]} by {admission['creator']}. CC0 1.0. {receipt['source_permalink']} . Context photograph, not product imagery or camera output."
    return {"object_id": "media_" + receipt["sha256"][:32], "object_type": "media_asset",
            "title": "CC0 context photograph: " + receipt["title"][5:],
            "purpose": "Provide traceable contextual imagery without claiming to depict a product or its camera performance.",
            "payload": {"summary": "Creator-attributed CC0 context photograph; source dedication is documented, not a guarantee against all third-party claims.",
                        "asset_kind": "image", "asset_uri": receipt["asset_uri"], "sha256": receipt["sha256"],
                        "provenance_kind": "open_license",
                        "provenance_reference": receipt["source_permalink"] + " ; receipt: " + str(path.relative_to(root)),
                        "representation": "concept_illustration", "private_preview_allowed": True,
                        "rights_state": "documented", "commercial_use_allowed": True, "credit": credit},
            "metadata": {"provenance_receipt_sha256": digest(raw), "license_uri": LICENSE,
                         "representation_detail": "context_photograph", "not_product_photography": True,
                         "not_camera_sample": True, "visual_risk_review_note": visual_note.strip(),
                         "source_observed_at": receipt["observed_at"], "human_approval_granted": False}}
