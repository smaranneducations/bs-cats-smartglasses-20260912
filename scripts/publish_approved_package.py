#!/usr/bin/env python3
"""Execute only a human-approved exact-hash publication request."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.contracts import LocalObjectStore
from packages.publishing import execute_approved_publication


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request_id")
    parser.add_argument("--destination", action="append", dest="destinations")
    parser.add_argument("--store", type=Path, default=ROOT / ".local" / "object-events.jsonl")
    args = parser.parse_args()
    results = execute_approved_publication(LocalObjectStore(args.store), args.request_id, args.destinations)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
