#!/usr/bin/env python3
"""Create a bounded local warehouse batch; never load it into the cloud."""
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.knowledge.projection import digest, project_store
from packages.knowledge.schema import SCHEMA_VERSION, schema
from services.api.src.main import get_store


def main():
    rows = project_store(get_store())
    root = ROOT / ".local" / "warehouse-batches"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    folder = Path(tempfile.mkdtemp(prefix="knowledge-", dir=root))
    folder.chmod(0o700)
    counts = {}
    for table, values in rows.items():
        with (folder / (table + ".jsonl")).open("w", encoding="utf-8") as stream:
            for row in values:
                stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
        (folder / (table + ".schema.json")).write_text(json.dumps(schema(table), indent=2), encoding="utf-8")
        counts[table] = len(values)
    manifest = {"schema_version": SCHEMA_VERSION, "row_counts": counts,
                "batch_sha256": digest(rows), "cloud_loaded": False,
                "evidence_warning": "Existing source references are not captured page fragments or independent tests.",
                "sensitive_data": "Raw feedback, conversations, credentials, configuration and media excluded.",
                "rights_state": "Private research projection; commercial/source approval is not inferred."}
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"folder": str(folder), **manifest}, indent=2))


if __name__ == "__main__":
    main()
