#!/usr/bin/env python3
"""Render a governed private image/music draft without paid provider calls."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.media.planning import prepare_recipe
from packages.media.renderer import render
from services.api.src.main import get_store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("storyboard_id")
    parser.add_argument("--quality", choices=["preview","review"], default="preview")
    args = parser.parse_args()
    store = get_store()
    recipe = prepare_recipe(store, args.storyboard_id)
    print(json.dumps({"recipe_id":recipe.object_id,"state":"admitted_for_private_preview"}), flush=True)
    print(json.dumps(render(store, recipe, quality=args.quality), indent=2), flush=True)


if __name__ == "__main__":
    main()
