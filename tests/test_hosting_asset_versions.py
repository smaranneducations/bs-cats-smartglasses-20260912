import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.build_firebase_hosting import version_entrypoint_assets


class HostingAssetVersionsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for name in ("index.html", "operator/index.html", "discover/index.html"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("<!doctype html><html><head></head><body></body></html>", encoding="utf-8")
        (self.root / "app.js").write_text("window.fixture = true;", encoding="utf-8")
        (self.root / "style.css").write_text("body { color: black; }", encoding="utf-8")

    def entry(self, text):
        (self.root / "index.html").write_text(text, encoding="utf-8")

    def result(self):
        return (self.root / "index.html").read_text(encoding="utf-8")

    def test_versions_script_and_stylesheet_preserving_query_and_fragment(self):
        self.entry('<link rel="stylesheet" href="/style.css"><script src="/app.js?mode=quiet&amp;v=old#top"></script>')
        version_entrypoint_assets(self.root)
        self.assertRegex(self.result(), r'/style.css\?v=[a-f0-9]{16}')
        digest = hashlib.sha256((self.root / "app.js").read_bytes()).hexdigest()[:16]
        self.assertIn(f'/app.js?mode=quiet&amp;v={digest}#top', self.result())

    def test_unchanged_assets_are_idempotent(self):
        self.entry('<script src="/app.js"></script>')
        version_entrypoint_assets(self.root)
        first = self.result()
        version_entrypoint_assets(self.root)
        self.assertEqual(self.result(), first)

    def test_changed_asset_changes_its_reference(self):
        self.entry('<script src="/app.js"></script>')
        version_entrypoint_assets(self.root)
        first = self.result()
        (self.root / "app.js").write_text("window.fixture = false;", encoding="utf-8")
        version_entrypoint_assets(self.root)
        self.assertNotEqual(self.result(), first)

    def test_external_assets_and_inline_script_content_are_untouched(self):
        text = '<script>const sample = `<link rel="stylesheet" href="/missing.css">`;</script><script src="https://example.invalid/sdk.js"></script>'
        self.entry(text)
        version_entrypoint_assets(self.root)
        self.assertEqual(self.result(), text)

    def test_relative_urls_use_the_actual_browser_route(self):
        entry = self.root / "operator/index.html"
        entry.write_text('<script src="app.js"></script>', encoding="utf-8")
        version_entrypoint_assets(self.root)
        self.assertRegex(entry.read_text(encoding="utf-8"), r'app.js\?v=[a-f0-9]{16}')

    def test_missing_local_assets_fail_closed(self):
        self.entry('<script src="/missing.js"></script>')
        with self.assertRaisesRegex(ValueError, "missing or out-of-bundle"):
            version_entrypoint_assets(self.root)

    def test_encoded_path_escape_is_rejected(self):
        self.entry('<script src="/%2e%2e/escape.js"></script>')
        with self.assertRaisesRegex(ValueError, "missing or out-of-bundle"):
            version_entrypoint_assets(self.root)


if __name__ == "__main__":
    unittest.main()
