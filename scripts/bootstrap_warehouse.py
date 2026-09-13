#!/usr/bin/env python3
"""Create missing empty knowledge tables with the installed bq CLI, not query jobs."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from packages.knowledge.schema import CLUSTERS, DATASET, TABLES, schema

PROJECT = "bs-cats-smartglasses-20260912"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply-empty-tables", action="store_true")
    args = parser.parse_args()
    if not args.apply_empty_tables:
        print(json.dumps({"project": PROJECT, "dataset": DATASET, "tables": list(TABLES),
                          "operation": "create missing empty tables only", "will_load_rows": False}))
        return
    with tempfile.TemporaryDirectory(prefix="smartglasses-schema-") as temporary:
        for table in TABLES:
            target = PROJECT + ":" + DATASET + "." + table
            existing = subprocess.run(["bq", "--format=prettyjson", "show", target],
                                      capture_output=True, text=True, timeout=45)
            if existing.returncode == 0:
                actual = json.loads(existing.stdout)
                wanted = {(field["name"], field["type"], field["mode"]) for field in schema(table)}
                present = {(field["name"], field["type"], field.get("mode", "NULLABLE"))
                           for field in actual.get("schema", {}).get("fields", [])}
                if not wanted.issubset(present) or actual.get("timePartitioning", {}).get("field") != "recorded_at" or not actual.get("requirePartitionFilter"):
                    raise RuntimeError(f"{table}: existing schema differs; no destructive migration was attempted.")
                print(json.dumps({"table": table, "state": "existing_compatible"}), flush=True)
                continue
            # Only an explicit not-found result authorizes creation.
            if "not found" not in (existing.stdout + existing.stderr).lower():
                raise RuntimeError(f"{table}: metadata lookup failed; creation was not attempted.")
            path = Path(temporary) / (table + ".json")
            path.write_text(json.dumps(schema(table)), encoding="utf-8")
            command = ["bq", "--project_id=" + PROJECT, "mk", "--table",
                       "--schema=" + str(path), "--time_partitioning_type=DAY",
                       "--time_partitioning_field=recorded_at", "--require_partition_filter=true",
                       "--clustering_fields=" + ",".join(CLUSTERS[table]), target]
            result = subprocess.run(command, capture_output=True, text=True, timeout=60)
            if result.returncode:
                raise RuntimeError(f"{table}: empty-table creation failed; no data was loaded.")
            print(json.dumps({"table": table, "state": "empty_table_created"}), flush=True)
    print(json.dumps({"project": PROJECT, "dataset": DATASET, "rows_loaded": 0, "query_jobs_run": 0}))


if __name__ == "__main__":
    main()
