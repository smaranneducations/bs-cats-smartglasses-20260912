import tempfile
import unittest
from pathlib import Path

from packages.contracts.content import VideoScene
from scripts.render_local_video import (
    caption_chunks,
    render_scene_frame,
    srt_timestamp,
)


class LocalVideoRendererTests(unittest.TestCase):
    def test_caption_chunks_and_timestamp(self):
        chunks = caption_chunks("one two three four five", max_words=2)
        self.assertEqual(chunks, ["one two", "three four", "five"])
        self.assertEqual(srt_timestamp(61.234), "00:01:01,234")

    def test_original_scene_frame_is_rendered(self):
        scene = VideoScene(
            scene_id="category_test",
            duration_seconds=10,
            narration="Test narration.",
            visual_direction="Original test diagram.",
            on_screen_text=["ONE CLEAR JOB", "NO PRODUCT FOOTAGE"],
            claim_ids=["claim_test"],
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "frame.png"
            render_scene_frame(scene, 0, 1, output)
            self.assertTrue(output.exists())
            self.assertGreater(output.stat().st_size, 10_000)


if __name__ == "__main__":
    unittest.main()
