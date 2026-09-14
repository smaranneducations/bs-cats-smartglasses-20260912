import json
import unittest
import httpx
from scripts.check_hosted_app import MAX_BYTES, run_checks


class HostedSmokeTests(unittest.TestCase):
    def check_report(self, overrides=None):
        overrides, calls = overrides or {}, []

        def handler(request):
            path = request.url.path
            calls.append(str(request.url))
            if path in overrides:
                value = overrides[path]
                if isinstance(value, Exception):
                    raise value
                return value
            if path in {"/operator", "/discover"}:
                return httpx.Response(200, headers={"content-type": "text/html"}, text='<html><script src="/app.js?v=1"></script><link rel="stylesheet" href="/app.css"></html>')
            if path == "/app.js":
                return httpx.Response(200, headers={"content-type": "text/javascript"}, text='"use strict";')
            if path == "/app.css":
                return httpx.Response(200, headers={"content-type": "text/css"}, text="body{color:black}")
            if path == "/health":
                return httpx.Response(200, json={"status": "healthy", "object_store": "firestore"})
            if path == "/v1/public/feed":
                return httpx.Response(200, json={"mode": "public", "cards": []})
            if path == "/v1/public/videos":
                return httpx.Response(200, json={"mode": "public", "videos": []})
            return httpx.Response(401, json={"detail": "Authentication required"})

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            return run_checks(client), calls

    def test_success_is_scoped_not_full_release_acceptance(self):
        report, calls = self.check_report()
        self.assertTrue(report["passed"])
        self.assertEqual(len(calls), 12)
        self.assertIn("media playback", report["not_assessed"])

    def test_html_fallback_is_not_a_working_script(self):
        report, _ = self.check_report({"/app.js": httpx.Response(200, headers={"content-type": "text/javascript"}, text="<!doctype html><html>Fallback</html>")})
        self.assertFalse(report["passed"])

    def test_open_administrator_endpoint_fails(self):
        report, _ = self.check_report({"/v1/session": httpx.Response(200, json={"private": "not-for-report"})})
        self.assertFalse(report["passed"])
        self.assertNotIn("not-for-report", json.dumps(report))

    def test_redirects_are_not_followed(self):
        report, calls = self.check_report({"/health": httpx.Response(302, headers={"location": "https://example.invalid"})})
        self.assertFalse(report["passed"])
        self.assertFalse(any("example.invalid" in url for url in calls))

    def test_exception_messages_are_not_logged(self):
        report, _ = self.check_report({"/health": httpx.ConnectError("private exception value")})
        self.assertFalse(report["passed"])
        self.assertNotIn("private exception value", json.dumps(report))

    def test_large_response_is_bounded(self):
        report, _ = self.check_report({"/health": httpx.Response(200, content=b"x" * (MAX_BYTES + 1))})
        self.assertFalse(report["passed"])

    def test_external_assets_not_fetched_or_claimed_as_checked(self):
        html = '<script src="/app.js?v=1"></script><script src="https://example.invalid/x.js"></script>'
        report, calls = self.check_report({"/operator": httpx.Response(200, headers={"content-type": "text/html"}, text=html)})
        self.assertTrue(report["passed"])
        self.assertEqual(report["external_asset_references_not_checked"], 1)
        self.assertFalse(any("example.invalid" in url for url in calls))

    def test_asset_fanout_is_bounded(self):
        html = ''.join(f'<script src="/asset-{i}.js"></script>' for i in range(33))
        report, calls = self.check_report({"/operator": httpx.Response(200, headers={"content-type": "text/html"}, text=html)})
        self.assertFalse(report["passed"])
        self.assertEqual(len(calls), 10)

    def test_unknown_origin_rejected(self):
        with httpx.Client(transport=httpx.MockTransport(lambda _: self.fail("Must not fetch"))) as client:
            with self.assertRaises(ValueError):
                run_checks(client, "http://127.0.0.1")

    def test_local_store_is_not_hosted_durability(self):
        report, _ = self.check_report({"/health": httpx.Response(200, json={"status": "healthy", "object_store": "local"})})
        self.assertFalse(report["passed"])


if __name__ == "__main__":
    unittest.main()
