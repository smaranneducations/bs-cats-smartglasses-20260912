#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import shutil


ROOT = Path(__file__).resolve().parents[1]
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
