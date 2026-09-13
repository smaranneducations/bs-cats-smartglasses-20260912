#!/usr/bin/env python3
"""Import bounded Firestore admin feedback without promoting policy or publishing."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.cloud.admin_feedback import FirestoreAdminFeedbackReader
from packages.cloud.firestore_transport import FirestoreTransport, ShortLivedGoogleToken
from packages.contracts import LocalObjectStore


def admission(operation, units):
    if operation != "document_read" or units > 20:
        raise RuntimeError("Only a bounded admin-feedback read is admitted.")
    if os.getenv("FIRESTORE_FEEDBACK_READ_ENABLED") != "1" or os.getenv("CLOUD_COSTS_RECONCILED") != "1":
        raise RuntimeError("Cloud feedback reading remains disarmed until accounting and the explicit read switch are current.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=20, choices=range(1, 21), metavar="1-20")
    parser.add_argument("--store", type=Path, default=ROOT / ".local" / "object-events.jsonl")
    args = parser.parse_args()
    transport = FirestoreTransport(token_source=ShortLivedGoogleToken(allow_local_cli=True), admission=admission)
    result = FirestoreAdminFeedbackReader(transport).import_into(LocalObjectStore(args.store), args.limit)
    print(f"Imported {len(result['imported'])} new feedback item(s); retained {len(result['retained'])} existing item(s).")
    print("No feedback content, credentials, policy promotion, spending or publication was printed or authorized.")


if __name__ == "__main__":
    main()
