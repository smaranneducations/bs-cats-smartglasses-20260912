#!/usr/bin/env python3
"""Prepare or dry-run semantic warehouse reads. No paid execution CLI exists."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.knowledge.bigquery_reader import (
    BigQuerySemanticReader, BigQueryTransport, DATASET, ExistingGcloudIdentity,
    LOCATION, OPERATIONS, PROJECT, QueryTicket, SemanticRead, WarehouseError,
    query_configuration, stamp,
)


def instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    stamp(parsed)
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("plan", "dry-run"))
    parser.add_argument("--operation", choices=sorted(OPERATIONS), default="comparison")
    parser.add_argument("--id", dest="ids", action="append", required=True)
    parser.add_argument("--recorded-from", type=instant, default=instant("2026-09-12T00:00:00Z"))
    parser.add_argument("--recorded-before", type=instant)
    parser.add_argument("--limit", type=int, default=250)
    parser.add_argument("--key", default="warehouse-readiness-20260913")
    parser.add_argument("--use-existing-gcloud-login", action="store_true")
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    try:
        read = SemanticRead(args.operation, tuple(args.ids), args.recorded_from, args.recorded_before or now, args.limit)
        ticket = QueryTicket(read, args.key, now)
        report = {"project": PROJECT, "dataset": DATASET, "location": LOCATION, "operation": args.operation, "fingerprint": ticket.fingerprint, "job_id": ticket.job_id, "observed_at": stamp(now), "billed_query_submitted": False, "data_uploaded": False, "rows_fetched": 0, "paid_execution_available_from_cli": False}
        if args.mode == "plan":
            report.update({"state": "compiled_locally", "query_configuration": query_configuration(read)})
            print(json.dumps(report, indent=2))
            return 0
        if not args.use_existing_gcloud_login:
            raise ValueError("dry-run requires --use-existing-gcloud-login; no login or consent is initiated")
        reader = BigQuerySemanticReader(BigQueryTransport(ExistingGcloudIdentity(explicitly_enabled=True)))
        estimate = reader.estimate(ticket)
        report.update({"state": "provider_dry_run_validated", "estimated_bytes_processed": estimate.bytes_processed, "statement_type": estimate.statement_type, "maximum_bytes_billed_if_later_admitted": read.maximum_bytes_billed, "dry_run_is_working_data_integration": False})
        directory = ROOT / ".local" / "warehouse-probes"
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, filename = tempfile.mkstemp(prefix=f"{args.operation}-", suffix=".json", dir=directory)
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(report, output, indent=2)
            output.write("\n")
        print(json.dumps({**report, "report_path": filename}, indent=2))
        return 0
    except (ValueError, WarehouseError) as error:
        print(json.dumps({"state": "not_completed", "error": str(error), "billed_query_submitted": False}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
