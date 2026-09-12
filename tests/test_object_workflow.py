import tempfile
import unittest
from pathlib import Path

from packages.contracts import (
    ActorType,
    CurationPatch,
    DuplicateObjectError,
    LocalObjectStore,
    ObjectStatus,
    ReviewDecision,
    ReviewState,
    SourceReference,
    UniversalObject,
)


class ObjectWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.store_path = Path(self.temporary_directory.name) / "events.jsonl"
        self.store = LocalObjectStore(self.store_path)

    def test_capture_curate_and_human_approve(self):
        item = UniversalObject(
            object_id="obj_test_glasses",
            object_type="market_observation",
            title="A captured smart-glasses signal",
            purpose="Preserve evidence before interpretation.",
            sources=[SourceReference(uri="https://example.test/source")],
            payload={"raw_note": "A source-backed observation."},
        )
        captured = self.store.capture(item, actor_id="founder")
        self.assertEqual(captured.status, ObjectStatus.captured)
        self.assertEqual(captured.version, 1)

        curated = self.store.curate(
            captured.object_id,
            CurationPatch(
                confidence=0.72,
                tags=["market", "smart-glasses"],
                payload={"summary": "A concise, reviewable interpretation."},
            ),
            actor_id="curation-agent",
            actor_type=ActorType.agent,
        )
        self.assertEqual(curated.status, ObjectStatus.proposed)
        self.assertEqual(curated.review.state, ReviewState.pending)
        self.assertEqual(curated.version, 2)
        self.assertIn("raw_note", curated.payload)
        self.assertIn("summary", curated.payload)

        approved = self.store.review(
            captured.object_id,
            ReviewDecision.approved,
            reviewer_id="founder",
            notes="Evidence and interpretation are aligned.",
        )
        self.assertEqual(approved.status, ObjectStatus.active)
        self.assertEqual(approved.review.state, ReviewState.approved)
        self.assertEqual(approved.version, 3)
        self.assertEqual(
            [record.event.sequence for record in self.store.history(captured.object_id)],
            [1, 2, 3],
        )

    def test_duplicate_capture_is_rejected(self):
        item = UniversalObject(
            object_id="obj_duplicate",
            object_type="claim",
            title="One object",
            purpose="Prove stable identifiers are enforced.",
        )
        self.store.capture(item, actor_id="founder")
        with self.assertRaises(DuplicateObjectError):
            self.store.capture(item, actor_id="founder")


if __name__ == "__main__":
    unittest.main()
