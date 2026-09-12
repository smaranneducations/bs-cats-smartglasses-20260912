import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "env_config.py"
SPEC = importlib.util.spec_from_file_location("env_config", SCRIPT)
env_config = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = env_config
SPEC.loader.exec_module(env_config)


class EnvConfigTests(unittest.TestCase):
    def test_parser_does_not_execute_shell_syntax(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "executed"
            env_path = Path(directory) / ".env"
            env_path.write_text(f"SAFE=$(touch {marker})\n", encoding="utf-8")
            parsed = env_config.parse_env(env_path)
            self.assertEqual(parsed.effective["SAFE"].value, f"$(touch {marker})")
            self.assertFalse(marker.exists())

    def test_normalize_preserves_effective_values_and_removes_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env_path = root / ".env"
            template = root / ".env.template"
            env_path.write_text("A=old\nSECRET='words with spaces'\nA=new\nEXTRA=value\n", encoding="utf-8")
            template.write_text("# Header\nA=\nSECRET=\n", encoding="utf-8")
            removed, _ = env_config.normalize(env_path, template)
            parsed = env_config.parse_env(env_path)
            self.assertEqual(removed, 1)
            self.assertFalse(parsed.duplicate_counts)
            self.assertEqual(parsed.effective["A"].value, "new")
            self.assertEqual(parsed.effective["SECRET"].value, "words with spaces")
            self.assertEqual(parsed.effective["EXTRA"].value, "value")
            self.assertEqual(os.stat(env_path).st_mode & 0o777, 0o600)

    def test_safe_get_allowlist_excludes_secrets(self):
        self.assertIn("GCP_PROJECT_ID", env_config.SAFE_OUTPUT_KEYS)
        self.assertNotIn("OPENAI_API_KEY", env_config.SAFE_OUTPUT_KEYS)
        self.assertNotIn("YOUTUBE_REFRESH_TOKEN", env_config.SAFE_OUTPUT_KEYS)

    def test_placeholder_detection(self):
        self.assertFalse(env_config.is_configured(""))
        self.assertFalse(env_config.is_configured("/path/to/key.json"))
        self.assertTrue(env_config.is_configured("bs-cats-smartglasses-20260912"))


if __name__ == "__main__":
    unittest.main()
