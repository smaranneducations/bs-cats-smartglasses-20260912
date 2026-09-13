from pathlib import PurePosixPath
import unittest

from scripts.repository_publication_guard import content_reasons, path_reasons


class RepositoryPublicationGuardTests(unittest.TestCase):
    def test_safe_public_examples_are_allowed(self):
        self.assertEqual(path_reasons(PurePosixPath("config/admin-auth.env.example")), [])
        self.assertEqual(content_reasons('ADMIN_EMAIL="admin@example.com"'), [])

    def test_private_runtime_and_environment_paths_are_blocked(self):
        self.assertIn("local or private runtime path", path_reasons(PurePosixPath(".local/events.json")))
        self.assertIn("environment file", path_reasons(PurePosixPath(".env.production")))

    def test_credential_containers_and_reports_are_blocked(self):
        self.assertIn("credential or runtime state filename", path_reasons(PurePosixPath("token.json")))
        self.assertIn(
            "private vulnerability or exploit report filename",
            path_reasons(PurePosixPath("vulnerability-report-auth.md")),
        )

    def test_private_key_and_restricted_markers_are_blocked(self):
        private_key_marker = "-----BEGIN " + "PRIVATE KEY-----"
        restricted_marker = '"privacy_classification": "' + 'restricted"'
        self.assertIn("private key material", content_reasons(private_key_marker))
        self.assertIn(
            "restricted or personal data classification",
            content_reasons(restricted_marker),
        )


if __name__ == "__main__":
    unittest.main()
