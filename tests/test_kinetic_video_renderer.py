from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "scripts" / "render_kinetic_video.py"
SPEC = importlib.util.spec_from_file_location("render_kinetic_video", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
renderer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = renderer
SPEC.loader.exec_module(renderer)


class KineticVideoRendererTests(unittest.TestCase):
    def test_spec_enforces_short_form_duration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            spec_path = Path(directory) / "spec.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "video_id": "valid_kinetic_demo",
                        "bpm": 120,
                        "beats": [
                            {
                                "image": "background.png",
                                "headline": ["ONE CLEAR IDEA"],
                                "duration": 6,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "60-120 seconds"):
                renderer.load_spec(spec_path)

    def test_frame_uses_original_background_and_kinetic_copy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("RGB", (1600, 900), "#36556a").save(root / "background.png")
            beat = renderer.parse_beat(
                {
                    "image": "background.png",
                    "eyebrow": "FIELD GUIDE",
                    "headline": ["PICK", "THE JOB"],
                    "deck": "Then pick the glasses",
                    "accent": "#ff5c35",
                    "duration": 6,
                    "layout": "left",
                    "number": "01",
                    "highlight_line": 1,
                },
                0,
            )
            assets = renderer.prepare_assets([beat], root)
            frame = renderer.render_frame(
                [beat],
                assets,
                {"left": renderer.shade_overlay("left"), "right": renderer.shade_overlay("right")},
                0,
                2.0,
            )
            self.assertEqual(frame.size, (1280, 720))
            self.assertNotEqual(frame.getpixel((80, 300)), frame.getpixel((1100, 300)))


if __name__ == "__main__":
    unittest.main()
