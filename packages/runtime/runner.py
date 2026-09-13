from __future__ import annotations

import multiprocessing
import os
from pathlib import Path
import time

from .context import ROOT, canonical, execution_context, load_profile, reject_obvious_credentials
from .contracts import TaskRequest
from .ledger import RuntimeLedger


def local_ledger():
    path = Path(os.getenv("OBJECT_STORE_PATH", str(ROOT / ".local/object-events.jsonl"))).expanduser()
    if path.suffix == ".jsonl":
        path = path.with_suffix(".sqlite3")
    return RuntimeLedger(path)


def submit(task: TaskRequest, actor_id="agent:local-runtime"):
    profile = load_profile(task.profile_id)
    if task.profile_revision != profile["revision"] or len(task.inputs) > profile["maximum_objects"]:
        raise ValueError("Profile revision or object budget does not match.")
    context = execution_context(task, profile)
    return local_ledger().submit(task, context, actor_id)


def _child(send, request, context):
    try:
        from services.api.src.main import get_store
        from .tools import dispatch
        result = dispatch(get_store(), request, context)
        reject_obvious_credentials(result)
        if len(canonical(result).encode()) > 262144:
            send.send({"failure_code": "result_limit", "retryable": False})
        else:
            send.send({"result": result})
    except ValueError:
        send.send({"failure_code": "input_or_policy_rejected", "retryable": False})
    except Exception:
        # Never echo an exception that might contain an object payload or credential.
        send.send({"failure_code": "tool_failure", "retryable": True})
    finally:
        send.close()


def run_one(task_id=None, actor_id="agent:local-runtime"):
    ledger = local_ledger()
    claim = ledger.claim(actor_id, task_id)
    if claim is None:
        return {"state": "idle", "reason": "No eligible queued task, or another worker holds the lease."}
    context = multiprocessing.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    child = context.Process(target=_child, args=(send, claim["request"], claim["context"]), daemon=True)
    message = {"failure_code": "worker_timeout", "retryable": True}
    try:
        child.start()
        send.close()
        deadline = time.monotonic() + claim["timeout_seconds"]
        while time.monotonic() < deadline:
            if receive.poll(min(0.25, max(0, deadline - time.monotonic()))):
                try:
                    message = receive.recv()
                except EOFError:
                    message = {"failure_code": "worker_exit", "retryable": True}
                break
            if ledger.status()["paused"]:
                message = {"failure_code": "paused", "retryable": False}
                break
            if not child.is_alive():
                message = {"failure_code": "worker_exit", "retryable": True}
                break
    finally:
        if child.pid is not None:
            if child.is_alive():
                child.terminate()
            child.join(timeout=2)
            if child.is_alive():
                child.kill()
                child.join(timeout=2)
        receive.close()
        send.close()
    state = ledger.finish(claim["task_id"], claim["lease_token"], actor_id, **message)
    return {"task_id": claim["task_id"], "state": state,
            "failure_code": message.get("failure_code"), "external_provider_calls": 0}
