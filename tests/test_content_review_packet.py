import tempfile
import unittest
from pathlib import Path

from packages.contracts import SourceReference, UniversalObject
from packages.contracts.content import VideoScene, VideoScript
from scripts.build_review_packet import render_review_packet, validate_script_against_brief


class ContentReviewPacketTests(unittest.TestCase):
    def setUp(self):
        self.brief = UniversalObject(
            object_id="obj_brief",
            object_type="content_brief",
            title="Brief <unsafe>",
            purpose="Test linked content.",
            sources=[
                SourceReference(
                    source_id="src_one",
                    uri="https://example.test/source",
                    title="Source <one>",
                )
            ],
            payload={
                "claims": [
                    {
                        "claim_id": "claim_one",
                        "statement": "A linked claim.",
                        "source_ids": ["src_one"],
                        "verification_state": "verified",
                        "freshness_check_required": True,
                    }
                ]
            },
        )
        self.script = VideoScript(
            script_id="script_one",
            brief_object_id=self.brief.object_id,
            working_title="A safe review",
            thumbnail_text="ONE RULE",
            target_duration_seconds=20,
            description="A review packet test.",
            disclosure="No affiliate links.",
            scenes=[
                VideoScene(
                    scene_id="scene_one",
                    duration_seconds=20,
                    narration="A linked narration.",
                    visual_direction="Draw a simple diagram.",
                    on_screen_text=["Choose by job"],
                    claim_ids=["claim_one"],
                )
            ],
        )

    def test_unknown_claim_is_rejected(self):
        broken = self.script.model_copy(deep=True)
        broken.scenes[0].claim_ids = ["claim_missing"]
        with self.assertRaises(ValueError):
            validate_script_against_brief(broken, self.brief)

    def test_review_packet_escapes_content_and_links_sources(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "review.html"
            render_review_packet(self.script, self.brief, output)
            document = output.read_text(encoding="utf-8")
            self.assertIn("https://example.test/source", document)
            self.assertIn("Source &lt;one&gt;", document)
            self.assertNotIn("Source <one>", document)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
