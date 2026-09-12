import json
import tempfile
import unittest
from pathlib import Path

from packages.contracts import LocalObjectStore, ObjectStatus, ReviewState
from scripts.research_intake import ingest_manifest


class ResearchIntakeTests(unittest.TestCase):
    def test_manifest_becomes_proposed_brief_with_audit_history(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            manifest_path = root / "manifest.json"
            store_path = root / "events.jsonl"
            manifest_path.write_text(
                json.dumps(
                    {
                        "research_id": "research_test",
                        "brief_object_id": "obj_test_brief",
                        "title": "Four smart-glasses categories",
                        "purpose": "Help buyers choose by use case.",
                        "summary": "The category contains products with different jobs.",
                        "sources": [
                            {
                                "source_id": "src_test",
                                "uri": "https://example.test/spec",
                                "title": "Example specification",
                                "publisher": "Example",
                                "evidence_tier": "primary_manufacturer",
                                "retrieved_at": "2026-09-13T09:00:00Z",
                                "digest": "The official page documents a display.",
                            }
                        ],
                        "claims": [
                            {
                                "claim_id": "claim_test",
                                "statement": "The product has a display.",
                                "kind": "fact",
                                "source_ids": ["src_test"],
                                "evidence_tier": "primary_manufacturer",
                                "verification_state": "verified",
                                "confidence": 0.95,
                            }
                        ],
                        "presentation": {
                            "hook": "The same label hides different products.",
                            "viewer_promise": "Choose the right category.",
                            "sections": [
                                {
                                    "heading": "Start with the job",
                                    "objective": "Separate categories.",
                                    "claim_ids": ["claim_test"],
                                    "talking_points": ["A display changes the use case."],
                                }
                            ],
                            "call_to_action": "Write down your primary use case.",
                        },
                    }
                ),
                encoding="utf-8",
            )

            result = ingest_manifest(manifest_path, store_path)
            self.assertEqual(result["status"], "proposed")

            store = LocalObjectStore(store_path)
            item = store.get("obj_test_brief")
            self.assertEqual(item.status, ObjectStatus.proposed)
            self.assertEqual(item.review.state, ReviewState.pending)
            self.assertEqual(len(store.history(item.object_id)), 2)
            self.assertEqual(store_path.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
