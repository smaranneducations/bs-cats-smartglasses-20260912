import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "secret_scan.py"
SPEC = importlib.util.spec_from_file_location("secret_scan", SCRIPT)
secret_scan = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = secret_scan
SPEC.loader.exec_module(secret_scan)


class SecretScanTests(unittest.TestCase):
    def test_detects_likely_key_without_returning_value(self):
        fake_key = "sk-" + "A" * 32
        findings = secret_scan.scan_text("settings.txt", f"token: {fake_key}")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule, "openai-key")
        self.assertNotIn(fake_key, repr(findings))

    def test_empty_public_template_assignment_is_allowed(self):
        findings = secret_scan.scan_text(".env.template", "OPENAI_API_KEY=\nYOUTUBE_REFRESH_TOKEN=\n")
        self.assertEqual(findings, [])

    def test_populated_config_secret_is_flagged(self):
        findings = secret_scan.scan_text("settings.yaml", "client_secret: definitely-not-a-placeholder")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule, "assigned-secret")


if __name__ == "__main__":
    unittest.main()
