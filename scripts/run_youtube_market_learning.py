#!/usr/bin/env python3
"""Run the bounded monthly YouTube market-learning snapshot."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.intelligence.youtube_market import YouTubeMarketError, YouTubeMarketPipeline


def main():
    try:
        receipt = YouTubeMarketPipeline(ROOT, ROOT / "config" / "workflows" / "youtube-market-learning.json").run()
        print(json.dumps(receipt, indent=2))
    except (YouTubeMarketError, OSError, ValueError) as error:
        print(json.dumps({"state": "not_completed", "error": str(error), "automatic_retry": False}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
