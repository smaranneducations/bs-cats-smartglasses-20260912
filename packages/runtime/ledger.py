from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import time
import uuid

from .context import canonical, fingerprint, reject_obvious_credentials


class AdmissionError(ValueError):
    pass


class StaleLeaseError(ValueError):
    pass


class RuntimeLedger:
    """One transaction boundary for task admission, leases, and reservations.

    Tables share the local object-store SQLite file but never alter its tables.
    This is not a Cloud Run persistence adapter or a provider billing cap.
    """

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS runtime_control (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    paused INTEGER NOT NULL DEFAULT 0,
                    changed_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runtime_budget (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    ceiling_cents INTEGER NOT NULL,
                    stop_cents INTEGER NOT NULL,
                    job_limit_cents INTEGER NOT NULL,
                    day_limit_cents INTEGER NOT NULL,
                    reconciled_at REAL,
                    unknown_costs INTEGER NOT NULL DEFAULT 1,
                    paid_armed INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS runtime_expenses (
                    expense_id TEXT PRIMARY KEY,
                    amount_cents INTEGER NOT NULL CHECK(amount_cents>=0),
                    category TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    provenance TEXT NOT NULL,
                    evidence_ref TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runtime_tasks (
                    task_id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    request_hash TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    context_hash TEXT NOT NULL,
                    context_json TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL,
                    timeout_seconds INTEGER NOT NULL,
                    lease_token TEXT,
                    lease_until REAL,
                    reservation_cents INTEGER NOT NULL DEFAULT 0,
                    admitted_day TEXT NOT NULL,
                    result_json TEXT,
                    failure_code TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runtime_audit (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    event_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    occurred_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS runtime_task_queue ON runtime_tasks(state, created_at);
            """)
            connection.execute("INSERT OR IGNORE INTO runtime_control VALUES (1, 0, ?)", (time.time(),))
            connection.execute("INSERT OR IGNORE INTO runtime_budget VALUES (1, 50000, 45000, 200, 500, NULL, 1, 0)")
            connection.execute(
                "INSERT OR IGNORE INTO runtime_expenses VALUES (?, ?, ?, ?, ?, ?)",
                ("owner-subscription-2026-09-12", 8000, "subscription", "2026-09-12",
                 "owner_reported", "charter:2026-09-12-subscription-payment"),
            )

    @contextmanager
    def connection(self):
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def audit(connection, task_id, event_type, actor_id, details):
        connection.execute("INSERT INTO runtime_audit(task_id,event_type,actor_id,details_json,occurred_at) VALUES (?,?,?,?,?)",
                           (task_id, event_type, actor_id, canonical(details), time.time()))

    @staticmethod
    def totals(connection):
        expenses = connection.execute("SELECT COALESCE(SUM(amount_cents),0) FROM runtime_expenses").fetchone()[0]
        reserved = connection.execute("SELECT COALESCE(SUM(reservation_cents),0) FROM runtime_tasks").fetchone()[0]
        return expenses, reserved

    def status(self):
        with self.connection() as connection:
            budget = dict(connection.execute("SELECT * FROM runtime_budget WHERE singleton=1").fetchone())
            expenses, reservations = self.totals(connection)
            counts = {row["state"]: row["n"] for row in connection.execute("SELECT state,COUNT(*) AS n FROM runtime_tasks GROUP BY state")}
            paused = bool(connection.execute("SELECT paused FROM runtime_control WHERE singleton=1").fetchone()[0])
        fresh = budget["reconciled_at"] is not None and 0 <= time.time() - budget["reconciled_at"] <= 86400
        return {"currency": "USD", "ceiling_cents": budget["ceiling_cents"],
                "stop_new_paid_work_cents": budget["stop_cents"],
                "recorded_expenses_cents": expenses, "outstanding_reservations_cents": reservations,
                "owner_reported_subscription_cents": 8000,
                "other_costs_unreconciled": bool(budget["unknown_costs"]),
                "accounting_fresh": fresh,
                "paid_execution_enabled": False,
                "paid_adapter_available": False,
                "spendable_headroom_cents": None if budget["unknown_costs"] or not fresh else max(0, budget["stop_cents"] - expenses - reservations),
                "paused": paused, "tasks_by_state": counts,
                "persistence": "local_sqlite", "provider_spend_cap": False}

    def submit(self, task, context, actor_id):
        request = task.model_dump(mode="json")
        reject_obvious_credentials(request)
        reject_obvious_credentials(context)
        if len(canonical(context)) > 65536:
            raise AdmissionError("Execution context exceeds the fixed size limit.")
        profile = context["profile"]
        if profile["external_cost_cents"] != 0:
            raise AdmissionError("Paid jobs remain disabled while external costs are unresolved.")
        request_hash = fingerprint({"actor_id": actor_id, "request": request})
        with self.connection() as connection:
            existing = connection.execute("SELECT task_id,request_hash,context_hash FROM runtime_tasks WHERE idempotency_key=?", (task.idempotency_key,)).fetchone()
            if existing:
                if existing["request_hash"] != request_hash or existing["context_hash"] != fingerprint(context):
                    raise AdmissionError("The idempotency key already represents different inputs or policy.")
                return existing["task_id"]
            if connection.execute("SELECT paused FROM runtime_control WHERE singleton=1").fetchone()[0]:
                raise AdmissionError("Runtime is paused.")
            task_id, now = "task_" + uuid.uuid4().hex, time.time()
            connection.execute("""INSERT INTO runtime_tasks
                (task_id,idempotency_key,request_hash,request_json,context_hash,context_json,actor_id,state,
                 max_attempts,timeout_seconds,admitted_day,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,'queued',?,?,?,?,?)""",
                (task_id, task.idempotency_key, request_hash, canonical(request), fingerprint(context), canonical(context), actor_id,
                 min(3, profile["maximum_attempts"]), min(60, profile["maximum_seconds"]),
                 datetime.now(timezone.utc).date().isoformat(), now, now))
            self.audit(connection, task_id, "submitted", actor_id, {"request_hash": request_hash, "context_hash": fingerprint(context), "reserved_cents": 0})
            return task_id

    def recover(self, connection):
        now = time.time()
        for row in connection.execute("SELECT task_id,attempts,max_attempts FROM runtime_tasks WHERE state='running' AND lease_until<?", (now,)).fetchall():
            state = "failed" if row["attempts"] >= row["max_attempts"] else "queued"
            connection.execute("UPDATE runtime_tasks SET state=?,lease_token=NULL,lease_until=NULL,failure_code='lease_expired',updated_at=? WHERE task_id=?", (state, now, row["task_id"]))
            self.audit(connection, row["task_id"], "lease_recovered", "system:runtime", {"next_state": state})

    def claim(self, actor_id, task_id=None):
        with self.connection() as connection:
            self.recover(connection)
            if connection.execute("SELECT paused FROM runtime_control WHERE singleton=1").fetchone()[0]:
                raise AdmissionError("Runtime is paused.")
            if connection.execute("SELECT COUNT(*) FROM runtime_tasks WHERE state='running'").fetchone()[0]:
                return None
            if task_id:
                row = connection.execute("SELECT * FROM runtime_tasks WHERE task_id=? AND state='queued'", (task_id,)).fetchone()
            else:
                row = connection.execute("SELECT * FROM runtime_tasks WHERE state='queued' ORDER BY created_at LIMIT 1").fetchone()
            if not row:
                return None
            token, now = uuid.uuid4().hex, time.time()
            connection.execute("UPDATE runtime_tasks SET state='running',attempts=attempts+1,lease_token=?,lease_until=?,updated_at=? WHERE task_id=?",
                               (token, now + row["timeout_seconds"] + 15, now, row["task_id"]))
            self.audit(connection, row["task_id"], "claimed", actor_id, {"attempt": row["attempts"] + 1})
            return {"task_id": row["task_id"], "lease_token": token, "timeout_seconds": row["timeout_seconds"],
                    "request": json.loads(row["request_json"]), "context": json.loads(row["context_json"])}

    def finish(self, task_id, token, actor_id, result=None, failure_code=None, retryable=False):
        if result is not None:
            reject_obvious_credentials(result)
            encoded = canonical(result)
            if len(encoded.encode()) > 262144:
                raise AdmissionError("Result exceeds the fixed 256 KiB limit.")
        else:
            encoded = None
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM runtime_tasks WHERE task_id=?", (task_id,)).fetchone()
            if not row or row["state"] != "running" or row["lease_token"] != token or row["lease_until"] < time.time():
                raise StaleLeaseError("A stale worker cannot complete this task.")
            paused = bool(connection.execute("SELECT paused FROM runtime_control WHERE singleton=1").fetchone()[0])
            state = "cancelled" if paused else "completed" if failure_code is None else "queued" if retryable and row["attempts"] < row["max_attempts"] else "failed"
            connection.execute("UPDATE runtime_tasks SET state=?,result_json=?,failure_code=?,lease_token=NULL,lease_until=NULL,updated_at=? WHERE task_id=?",
                               (state, encoded if state == "completed" else None, "paused" if paused else failure_code, time.time(), task_id))
            self.audit(connection, task_id, state, actor_id, {"failure_code": failure_code, "result_hash": fingerprint(result) if state == "completed" else None})
        return state

    def get(self, task_id):
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM runtime_tasks WHERE task_id=?", (task_id,)).fetchone()
            if row is None:
                raise KeyError(task_id)
            output = dict(row)
            output.pop("lease_token", None)
            for key in ("request_json", "context_json", "result_json"):
                value = output.pop(key)
                output[key.removesuffix("_json")] = json.loads(value) if value else None
            output["audit"] = [{**dict(item), "details": json.loads(item["details_json"])} for item in connection.execute(
                "SELECT event_type,actor_id,details_json,occurred_at FROM runtime_audit WHERE task_id=? ORDER BY event_id", (task_id,))]
            for item in output["audit"]:
                item.pop("details_json")
            return output

    def recent(self, limit=25):
        with self.connection() as connection:
            return [dict(row) for row in connection.execute("SELECT task_id,state,attempts,failure_code,created_at,updated_at FROM runtime_tasks ORDER BY created_at DESC LIMIT ?", (min(100, max(1, limit)),))]

    def set_paused(self, paused, actor_id):
        with self.connection() as connection:
            connection.execute("UPDATE runtime_control SET paused=?,changed_at=? WHERE singleton=1", (int(paused), time.time()))
            self.audit(connection, None, "paused" if paused else "resumed", actor_id, {})
