#!/usr/bin/env python3
"""Local operator entry point. It never reads .env or calls paid providers."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.runtime.contracts import TaskRequest
from packages.runtime.runner import local_ledger, run_one, submit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    commands.add_parser("list")
    commands.add_parser("pause")
    commands.add_parser("resume")
    create = commands.add_parser("submit")
    create.add_argument("request_file", type=Path)
    run = commands.add_parser("run-one")
    run.add_argument("--task-id")
    show = commands.add_parser("show")
    show.add_argument("task_id")
    args = parser.parse_args()
    if args.command == "submit":
        if args.request_file.stat().st_size > 65536:
            raise ValueError("Task file exceeds 64 KiB.")
        task = TaskRequest.model_validate_json(args.request_file.read_text())
        result = {"task_id": submit(task)}
    elif args.command == "run-one":
        result = run_one(args.task_id)
    elif args.command == "show":
        result = local_ledger().get(args.task_id)
    elif args.command == "list":
        result = local_ledger().recent()
    elif args.command in {"pause", "resume"}:
        local_ledger().set_paused(args.command == "pause", "operator:local-cli")
        result = {"paused": args.command == "pause"}
    else:
        result = local_ledger().status()
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError):
        print("Runtime action could not complete. Check input, policy, and local access; no private payload was printed.", file=sys.stderr)
        raise SystemExit(1)
