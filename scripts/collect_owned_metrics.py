#!/usr/bin/env python3
"""Create warehouse-shaped owned-app metric and primitive snapshots."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.analytics import OwnedMetricsCollector
from packages.contracts import LocalObjectStore


def main():
    store = LocalObjectStore(ROOT / ".local" / "object-events.jsonl")
    print(json.dumps(OwnedMetricsCollector(ROOT, store).collect(), indent=2))


if __name__ == "__main__":
    main()
