from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.build_firebase_hosting import validate_entrypoint_assets


class HostingBundleTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for name in ("index.html", "operator/index.html", "discover/index.html"):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("<!doctype html><title>Fixture</title>", encoding="utf-8")

    def operator(self, body):
        (self.root / "operator/index.html").write_text(body, encoding="utf-8")

    def test_existing_local_assets_pass(self):
        self.operator('<link rel="stylesheet" href="/operator/app.css?v=1"><script src="/operator/app.js"></script>')
        (self.root / "operator/app.css").write_text("body{}", encoding="utf-8")
        (self.root / "operator/app.js").write_text("void 0;", encoding="utf-8")
        validate_entrypoint_assets(self.root)

    def test_missing_stylesheet_fails_before_deployment(self):
        self.operator('<link rel="stylesheet" href="/operator/missing.css">')
        with self.assertRaisesRegex(ValueError, "missing.css"):
            validate_entrypoint_assets(self.root)

    def test_html_fallback_does_not_satisfy_missing_script(self):
        self.operator('<script src="/operator/missing.js"></script>')
        with self.assertRaisesRegex(ValueError, "missing.js"):
            validate_entrypoint_assets(self.root)

    def test_html_file_is_not_a_script_asset(self):
        self.operator('<script src="/operator/index.html"></script>')
        with self.assertRaises(ValueError):
            validate_entrypoint_assets(self.root)

    def test_relative_url_uses_browser_route_resolution(self):
        self.operator('<script src="app.js"></script>')
        (self.root / "app.js").write_text("void 0;", encoding="utf-8")
        validate_entrypoint_assets(self.root)

    def test_encoded_parent_path_cannot_leave_bundle(self):
        self.operator('<script src="/%2e%2e/outside.js"></script>')
        with self.assertRaises(ValueError):
            validate_entrypoint_assets(self.root)

    def test_external_assets_are_not_fetched_or_claimed_as_checked(self):
        self.operator('<script src="https://example.invalid/remote.js"></script>')
        validate_entrypoint_assets(self.root)


if __name__ == "__main__":
    unittest.main()
