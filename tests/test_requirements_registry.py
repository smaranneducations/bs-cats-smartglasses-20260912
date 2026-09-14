"""Public implementation evidence must be portable, not private decision prose."""
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RequirementsRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads((ROOT / "config/requirements-traceability.json").read_text())

    def test_unique_requirement_ids_and_known_statuses(self):
        entries = self.registry["requirements"]
        self.assertEqual(len(entries), len({item["id"] for item in entries}))
        for item in entries:
            self.assertIn(item["status"], self.registry["status_definitions"])

    def test_implementation_evidence_is_public_and_available(self):
        for item in self.registry["requirements"]:
            self.assertTrue(item["implementation_evidence"])
            for path in item["implementation_evidence"]:
                with self.subTest(requirement=item["id"], path=path):
                    self.assertNotIn(".local", Path(path).parts)
                    resolved = (ROOT / path).resolve()
                    self.assertTrue(resolved.is_relative_to(ROOT))
                    self.assertTrue(resolved.is_file())

    def test_reconciled_entries_keep_gaps_and_next_actions(self):
        entries = {item["id"]: item for item in self.registry["requirements"]}
        for identifier in self.registry["review_scope"]["requirement_ids"]:
            self.assertTrue(entries[identifier]["runtime_evidence"])
            self.assertTrue(entries[identifier]["remaining_gap"])
            self.assertTrue(entries[identifier]["next_action"])
