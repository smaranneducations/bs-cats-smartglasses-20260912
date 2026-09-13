#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import shutil


ROOT = Path(__file__).resolve().parents[1]


def version_entrypoint_assets(root):
    """Keep browsers from mixing an updated entrypoint with an older local bundle."""
    import hashlib
    import html
    import re
    from html.parser import HTMLParser
    from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

    root = Path(root).resolve()
    routes = {"/": "index.html", "/operator": "operator/index.html", "/discover": "discover/index.html"}
    for route, filename in routes.items():
        entry = root / filename
        text = entry.read_text(encoding="utf-8")
        offsets = [0]
        for line in text.splitlines(keepends=True):
            offsets.append(offsets[-1] + len(line))
        edits = []

        class Assets(HTMLParser):
            def handle_starttag(self, tag, attrs):
                attributes = dict(attrs)
                key = "src" if tag == "script" else "href"
                if tag != "script" and not (tag == "link" and "stylesheet" in attributes.get("rel", "").lower().split()):
                    return
                address = attributes.get(key)
                if not address:
                    return
                resolved = urlsplit(urljoin("https://hosting.invalid" + route, address))
                if resolved.scheme != "https" or resolved.netloc != "hosting.invalid":
                    return
                from urllib.parse import unquote
                asset = (root / unquote(resolved.path).lstrip("/")).resolve()
                if not asset.is_relative_to(root) or not asset.is_file():
                    raise ValueError("Cannot version a missing or out-of-bundle asset")
                digest = hashlib.sha256(asset.read_bytes()).hexdigest()[:16]
                original = urlsplit(address)
                query = [(name, value) for name, value in parse_qsl(original.query, keep_blank_values=True) if name != "v"]
                updated = urlunsplit(original._replace(query=urlencode(query + [("v", digest)])))
                raw = self.get_starttag_text()
                pattern = re.compile(r"(\b" + key + r"\s*=\s*)([\"'])(.*?)(\2)", re.IGNORECASE | re.DOTALL)
                replacement, count = pattern.subn(lambda match: match[1] + match[2] + html.escape(updated, quote=True) + match[2], raw, count=1)
                if count != 1:
                    raise ValueError("Local asset references must use quoted attributes")
                row, column = self.getpos()
                start = offsets[row - 1] + column
                edits.append((start, start + len(raw), replacement))

        parser = Assets(convert_charrefs=True)
        parser.feed(text)
        for start, end, replacement in reversed(edits):
            text = text[:start] + replacement + text[end:]
        entry.write_text(text, encoding="utf-8")
OUTPUT = ROOT / "dist" / "firebase"


def copy_tree(source: Path, target: Path) -> None:
    if not source.is_dir():
        raise SystemExit(f"Missing required application directory: {source.relative_to(ROOT)}")
    shutil.copytree(source, target)



def validate_entrypoint_assets(output):
    """Check packaged entrypoint scripts/styles, not browser or API behavior.

    External assets and JavaScript imports are outside this check's scope.
    """
    from html.parser import HTMLParser
    from urllib.parse import unquote, urljoin, urlsplit

    class References(HTMLParser):
        def __init__(self):
            super().__init__()
            self.assets = []

        def handle_starttag(self, tag, attrs):
            values = dict(attrs)
            if tag == "script" and values.get("src"):
                self.assets.append((values["src"], ".js"))
            if tag == "link" and "stylesheet" in values.get("rel", "").lower().split():
                if values.get("href"):
                    self.assets.append((values["href"], ".css"))

    root = output.resolve()
    missing = []
    for route, filename in (("/", "index.html"), ("/operator", "operator/index.html"),
                            ("/discover", "discover/index.html")):
        parser = References()
        parser.feed((root / filename).read_text(encoding="utf-8"))
        for reference, extension in parser.assets:
            supplied = urlsplit(reference)
            if supplied.scheme or supplied.netloc:
                continue
            resolved = urlsplit(urljoin("https://hosting.invalid" + route, reference))
            asset = (root / unquote(resolved.path).lstrip("/")).resolve()
            if not asset.is_relative_to(root) or not asset.is_file() or asset.suffix != extension:
                missing.append(f"{route}: {reference}")
    if missing:
        raise ValueError("Hosting entrypoint assets are missing or invalid: " + "; ".join(missing))


def main() -> None:
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)

    web = ROOT / "apps" / "web"
    shutil.copy2(web / "index.html", OUTPUT / "index.html")
    copy_tree(web, OUTPUT / "assets")
    copy_tree(ROOT / "apps" / "operator", OUTPUT / "operator")
    copy_tree(ROOT / "apps" / "public", OUTPUT / "discover-assets")

    discover = OUTPUT / "discover"
    discover.mkdir()
    shutil.copy2(ROOT / "apps" / "public" / "consumer.html", discover / "index.html")

    architecture = ROOT / "docs" / "architecture"
    if architecture.is_dir():
        copy_tree(architecture, OUTPUT / "operator" / "docs")

    # The audience page loads this shared asset from the site root.
    shutil.copy2(ROOT / "apps/operator/global-nav.js", OUTPUT / "global-nav.js")
    version_entrypoint_assets(OUTPUT)
    validate_entrypoint_assets(OUTPUT)

    manifest = {
        "schema_version": "firebase-hosting-bundle-1",
        "source_version": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "entrypoints": ["/", "/operator", "/discover"],
        "dynamic_api": "/v1/** -> Cloud Run bs-cats-api in us-central1",
        "warning": "A static bundle is not proof that the dynamic API is deployed."
    }
    (OUTPUT / "build-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "output": str(OUTPUT),
        "files": sum(1 for item in OUTPUT.rglob("*") if item.is_file())
    }, sort_keys=True))


if __name__ == "__main__":
    main()
