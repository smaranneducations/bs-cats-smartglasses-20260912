#!/usr/bin/env python3
"""Plan or execute bounded source discovery for unresolved knowledge fields."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.env_config import parse_env
from packages.intelligence.source_enrichment import EnrichmentError, SourceEnrichmentRouter, validate_task


ROOT = Path(__file__).resolve().parents[1]


def load_tasks(path: Path) -> list[dict]:
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, list) else [value]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_file", type=Path)
    parser.add_argument("--config", type=Path, default=ROOT / "config/workflows/source-enrichment.json")
    parser.add_argument("--env", type=Path, default=ROOT / ".env")
    parser.add_argument("--execute-free", action="store_true", help="Execute only no-charge adapters such as RSS and GDELT.")
    parser.add_argument("--allow-paid", action="store_true", help="Admit configured metered providers within workflow caps.")
    args = parser.parse_args()
    if args.execute_free and args.allow_paid:
        parser.error("Choose either --execute-free or --allow-paid.")
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        environment = {key: entry.value for key, entry in parse_env(args.env).effective.items()} if args.env.exists() else {}
        tasks = [validate_task(task) for task in load_tasks(args.task_file)]
        router = SourceEnrichmentRouter(config, environment, ROOT)
        if not args.execute_free and not args.allow_paid:
            print(json.dumps({"mode": "plan_only", "tasks": [
                {"task_id": task["task_id"], "providers": router.plan(task, allow_paid=False)} for task in tasks
            ]}, indent=2, ensure_ascii=True))
            return 0
        print(json.dumps(router.execute(tasks, allow_paid=args.allow_paid), indent=2, ensure_ascii=True))
        return 0
    except (OSError, ValueError, EnrichmentError) as exc:
        print(json.dumps({"state": "failed", "error": str(exc)}, ensure_ascii=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
