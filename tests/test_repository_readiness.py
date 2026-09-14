from pathlib import Path
import tempfile
import unittest
from scripts.release_readiness import assess_repository


class RepositoryReadinessTests(unittest.TestCase):
    def test_repository_check_cannot_certify_production(self):
        report = assess_repository()
        self.assertFalse(report["production_readiness_assessed"])
        self.assertFalse(report["production_ready"])
        self.assertEqual(report["production_status"], "not_assessed_by_this_check")
        self.assertNotIn("cloud_run_deployment", report["production_blockers"])
        self.assertNotIn("firebase_hosting_deployment", report["production_blockers"])

    def test_missing_repository_fails_without_crashing_on_ignore_file(self):
        with tempfile.TemporaryDirectory() as directory:
            report = assess_repository(Path(directory))
        self.assertFalse(report["repository_candidate_ready"])
        self.assertIn("README.md", report["missing_files"])
        self.assertFalse(report["safety_checks"]["env_ignored"])


if __name__ == "__main__":
    unittest.main()
