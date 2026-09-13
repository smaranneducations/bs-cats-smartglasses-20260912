"""Warehouse jobs use the existing runtime database and reservation total.

No accounting is armed here. Provider observations never erase an outstanding
reservation or get represented as a settled invoice.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING

from packages.contracts.warehouse_execution import (
    WarehousePricePolicy, WarehouseQueryRequest, WarehouseRuntimeTask,
)
from packages.knowledge.bigquery_reader import (
    AdmissionDenied, BigQuerySemanticReader, QueryTicket, Reservation, stamp,
)


def now_utc():
    return datetime.now(timezone.utc)


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def row_dict(cursor):
    row = cursor.fetchone()
    return None if row is None else dict(zip((item[0] for item in cursor.description), row))


def reservation_document(reservation):
    return {
        "reservation_id": reservation.reservation_id,
        "fingerprint": reservation.fingerprint,
        "maximum_bytes_billed": reservation.maximum_bytes_billed,
        "expires_at": stamp(reservation.expires_at),
    }


def read_reservation(value):
    return Reservation(value["reservation_id"], value["fingerprint"],
                       value["maximum_bytes_billed"], datetime.fromisoformat(value["expires_at"].replace("Z", "+00:00")))


class SharedWarehouseSpendGate:
    """Reserve in runtime_tasks, which RuntimeLedger.totals already sums.

    External states are deliberately not queued or leased to deterministic
    workers. Expiry stops new admission; it does not imply a free provider job.
    """

    def __init__(self, ledger, price: WarehousePricePolicy, actor_id, input_versions, *, clock=now_utc):
        self.ledger, self.price, self.actor_id = ledger, price, actor_id
        self.input_versions, self.clock = dict(input_versions), clock

    def _guard(self, connection, maximum_bytes_billed, *, additional=True):
        now = self.clock()
        budget = row_dict(connection.execute("SELECT * FROM runtime_budget WHERE singleton=1"))
        control = row_dict(connection.execute("SELECT paused FROM runtime_control WHERE singleton=1"))
        if not budget or not control:
            raise AdmissionDenied("Shared budget or pause control is missing")
        if control["paused"]:
            raise AdmissionDenied("The shared runtime is paused")
        if budget["unknown_costs"]:
            raise AdmissionDenied("Other project costs have not been reconciled")
        reconciled = budget["reconciled_at"]
        if reconciled is None or not 0 <= now.timestamp() - reconciled < 6 * 3600:
            raise AdmissionDenied("Shared accounting is stale or unavailable")
        if budget["paid_armed"] != 1:
            raise AdmissionDenied("Paid execution has not been armed in the shared ledger")
        price = self.price
        if (price.public_reference_observed_at is None or price.public_reference_observed_at > now
                or price.account_currency != "USD" or not price.account_on_demand_verified
                or price.verified_upper_bound_usd_per_tib is None
                or not price.verification_evidence_ref or price.verified_at is None or price.valid_until is None
                or not price.verified_at <= now < price.valid_until
                or not timedelta(0) < price.valid_until - price.verified_at <= timedelta(hours=24)):
            raise AdmissionDenied("Applicable, current account pricing has not been verified")
        if not 10 * 1024 * 1024 <= maximum_bytes_billed <= 64 * 1024 * 1024:
            raise AdmissionDenied("Query bytes are outside the bounded reader envelope")
        rate = max(price.public_reference_usd_per_tib, price.verified_upper_bound_usd_per_tib)
        cents = max(1, int((Decimal(maximum_bytes_billed) * rate * 100 / Decimal(2 ** 40)).to_integral_value(rounding=ROUND_CEILING)))
        if cents > min(budget["job_limit_cents"], 200):
            raise AdmissionDenied("Query exceeds the per-job reservation limit")
        spent, reserved = self.ledger.totals(connection)
        increment = cents if additional else 0
        if spent + reserved + increment > min(budget["ceiling_cents"], budget["stop_cents"], 45000):
            raise AdmissionDenied("The experiment admission ceiling would be exceeded")
        day = now.date().isoformat()
        day_reserved = connection.execute("SELECT COALESCE(SUM(reservation_cents),0) FROM runtime_tasks WHERE admitted_day=?", (day,)).fetchone()[0]
        day_expenses = connection.execute("SELECT COALESCE(SUM(amount_cents),0) FROM runtime_expenses WHERE substr(occurred_at,1,10)=?", (day,)).fetchone()[0]
        if day_reserved + day_expenses + increment > min(budget["day_limit_cents"], 500):
            raise AdmissionDenied("The shared daily reservation limit would be exceeded")
        expires_at = min(now + timedelta(minutes=5), price.valid_until,
                         datetime.fromtimestamp(reconciled, timezone.utc) + timedelta(hours=6))
        return cents, expires_at

    def preflight(self, maximum_bytes_billed):
        with self.ledger.connection() as connection:
            self._guard(connection, maximum_bytes_billed)

    def reserve(self, ticket, estimate):
        now = self.clock()
        if (estimate.fingerprint != ticket.fingerprint or estimate.statement_type != "SELECT"
                or not 0 <= (now - estimate.observed_at).total_seconds() < 300
                or not 0 <= estimate.bytes_processed <= ticket.read.maximum_bytes_billed):
            raise AdmissionDenied("Dry-run evidence does not admit this exact query")
        if set(self.input_versions) != set(ticket.read.ids) or any(type(version) is not int or version < 1 for version in self.input_versions.values()):
            raise AdmissionDenied("Exact current product versions are required")
        task_id = "task_" + hashlib.sha256(ticket.idempotency_key.encode()).hexdigest()[:32]
        with self.ledger.connection() as connection:
            prior = row_dict(connection.execute("SELECT request_hash, result_json, state FROM runtime_tasks WHERE task_id=?", (task_id,)))
            cents, expires_at = self._guard(connection, ticket.read.maximum_bytes_billed, additional=prior is None)
            if prior is not None:
                if prior["request_hash"] != ticket.fingerprint or prior["state"] not in ("warehouse_reserved", "warehouse_observed"):
                    raise AdmissionDenied("Reservation identity does not match this query")
                reservation = read_reservation(json.loads(prior["result_json"])["reservation"])
                if not now < reservation.expires_at:
                    raise AdmissionDenied("Expired admission can only be resumed, not resubmitted")
                return reservation
            reservation = Reservation(task_id, ticket.fingerprint, ticket.read.maximum_bytes_billed, expires_at)
            task = WarehouseRuntimeTask(
                inputs=[{"object_id": key, "version": version} for key, version in sorted(self.input_versions.items())],
                idempotency_key=ticket.idempotency_key, query_fingerprint=ticket.fingerprint,
                maximum_bytes_billed=ticket.read.maximum_bytes_billed,
            )
            context = {"input_versions": self.input_versions, "pricing": self.price.model_dump(mode="json")}
            result = {"reservation": reservation_document(reservation), "reserved_cents": cents,
                      "settled_charge_cents": None, "provider_observation": None}
            connection.execute(
                """INSERT INTO runtime_tasks
                (task_id,idempotency_key,request_hash,request_json,context_hash,context_json,actor_id,state,
                 attempts,max_attempts,timeout_seconds,lease_token,lease_until,reservation_cents,admitted_day,
                 result_json,failure_code,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,'warehouse_reserved',1,1,300,NULL,NULL,?,?,?,NULL,?,?)""",
                (task_id, ticket.idempotency_key, ticket.fingerprint, encode(task.model_dump(mode="json")),
                 fingerprint(context), encode(context), self.actor_id, cents, now.date().isoformat(),
                 encode(result), now.timestamp(), now.timestamp()),
            )
            self.ledger.audit(connection, task_id, "warehouse_cost_reserved", self.actor_id,
                              {"query_fingerprint": ticket.fingerprint, "reserved_cents": cents,
                               "maximum_bytes_billed": ticket.read.maximum_bytes_billed})
            return reservation

    def observe(self, reservation, usage):
        observation = encode(usage)
        if len(observation.encode()) > 65536:
            raise AdmissionDenied("Provider observation exceeds the audit envelope")
        with self.ledger.connection() as connection:
            prior = row_dict(connection.execute("SELECT request_hash, result_json FROM runtime_tasks WHERE task_id=?", (reservation.reservation_id,)))
            if prior is None or prior["request_hash"] != reservation.fingerprint:
                raise AdmissionDenied("Provider observation has no matching reservation")
            result = json.loads(prior["result_json"])
            if result["reservation"] != reservation_document(reservation):
                raise AdmissionDenied("Provider observation changed the admitted reservation")
            result["provider_observation"] = json.loads(observation)
            result["settled_charge_cents"] = None
            connection.execute("UPDATE runtime_tasks SET state='warehouse_observed',result_json=?,updated_at=? WHERE task_id=?",
                               (encode(result), self.clock().timestamp(), reservation.reservation_id))
            self.ledger.audit(connection, reservation.reservation_id, "warehouse_usage_observed", self.actor_id,
                              {"query_fingerprint": reservation.fingerprint, "reservation_retained": True})


class WarehouseExecutionService:
    def __init__(self, ledger, store, price, transport_factory, *, enabled=False, clock=now_utc):
        self.ledger, self.store, self.price = ledger, store, price
        self.transport_factory, self.enabled, self.clock = transport_factory, enabled, clock
        with ledger.connection() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS warehouse_requests (
                query_id TEXT PRIMARY KEY, actor_id TEXT NOT NULL, request_hash TEXT NOT NULL,
                request_json TEXT NOT NULL, input_versions_json TEXT NOT NULL, issued_at TEXT NOT NULL,
                provider_key TEXT NOT NULL UNIQUE, created_at REAL NOT NULL)""")

    def status(self):
        reason = None
        gate = SharedWarehouseSpendGate(self.ledger, self.price, "status-reader", {}, clock=self.clock)
        try:
            gate.preflight(64 * 1024 * 1024)
        except AdmissionDenied as error:
            reason = str(error)
        return {"schema_version": "warehouse-execution-status-1", "adapter_configured": self.enabled,
                "new_paid_queries_admissible": self.enabled and reason is None,
                "admission_reason": reason or (None if self.enabled else "Warehouse transport is not enabled"),
                "query_operations": ["products", "assertions", "comparison"],
                "maximum_bytes_billed": 64 * 1024 * 1024,
                "shared_runtime_ledger": True, "default_semantic_backend": "local_versioned_store",
                "automatic_local_fallback": False, "reservations_are_settled_charges": False,
                "table_population_verified": False, "publication_permission": False,
                "account_pricing_verified": self.price.account_on_demand_verified,
                "ledger": self.ledger.status()}

    def _load(self, query_id, actor_id):
        with self.ledger.connection() as connection:
            row = row_dict(connection.execute("SELECT * FROM warehouse_requests WHERE query_id=? AND actor_id=?", (query_id, actor_id)))
        if row is None:
            raise AdmissionDenied("No query ticket is available for this actor")
        request = WarehouseQueryRequest.model_validate_json(row["request_json"])
        ticket = QueryTicket(request.to_read(), row["provider_key"], datetime.fromisoformat(row["issued_at"].replace("Z", "+00:00")))
        return row, request, ticket

    def execute(self, request: WarehouseQueryRequest, actor_id: str):
        if not self.enabled:
            raise AdmissionDenied("Warehouse transport is not enabled")
        input_versions = {}
        for object_id in request.ids:
            record = self.store.get(object_id)
            if record.object_type != "product":
                raise AdmissionDenied("Warehouse queries require governed product inputs")
            input_versions[object_id] = record.version
        gate = SharedWarehouseSpendGate(self.ledger, self.price, actor_id, input_versions, clock=self.clock)
        gate.preflight(request.maximum_bytes_billed)
        key = fingerprint({"actor": actor_id, "key": request.idempotency_key})
        query_id = "wq_" + key[:32]
        request_value = request.model_dump(mode="json")
        request_hash = fingerprint(request_value)
        now = self.clock()
        with self.ledger.connection() as connection:
            prior = row_dict(connection.execute("SELECT request_hash,input_versions_json FROM warehouse_requests WHERE query_id=?", (query_id,)))
            if prior is not None:
                if prior["request_hash"] != request_hash or json.loads(prior["input_versions_json"]) != input_versions:
                    raise AdmissionDenied("This idempotency key is already bound to other inputs")
            else:
                connection.execute("INSERT INTO warehouse_requests VALUES (?,?,?,?,?,?,?,?)",
                                   (query_id, actor_id, request_hash, encode(request_value), encode(input_versions),
                                    stamp(now), "warehouse:" + key, now.timestamp()))
                self.ledger.audit(connection, None, "warehouse_ticket_created", actor_id, {"query_id": query_id, "input_versions": input_versions})
        _, _, ticket = self._load(query_id, actor_id)
        reader = BigQuerySemanticReader(self.transport_factory(), gate, clock=self.clock)
        estimate = reader.estimate(ticket)
        result = reader.submit(ticket, estimate)
        return {"query_id": query_id, "backend": "bigquery", "input_versions": input_versions,
                "result": result, "publication_permission": False, "local_fallback_used": False}

    def resume(self, query_id, actor_id):
        if not self.enabled:
            raise AdmissionDenied("Warehouse transport is not enabled")
        row, _, ticket = self._load(query_id, actor_id)
        task_id = "task_" + hashlib.sha256(ticket.idempotency_key.encode()).hexdigest()[:32]
        with self.ledger.connection() as connection:
            saved = row_dict(connection.execute("SELECT result_json FROM runtime_tasks WHERE task_id=? AND actor_id=?", (task_id, actor_id)))
        if saved is None:
            raise AdmissionDenied("No paid admission exists to resume; no new job was submitted")
        reservation = read_reservation(json.loads(saved["result_json"])["reservation"])
        versions = json.loads(row["input_versions_json"])
        gate = SharedWarehouseSpendGate(self.ledger, self.price, actor_id, versions, clock=self.clock)
        reader = BigQuerySemanticReader(self.transport_factory(), gate, clock=self.clock)
        return {"query_id": query_id, "backend": "bigquery", "input_versions": versions,
                "result": reader.resume(ticket, reservation), "publication_permission": False,
                "local_fallback_used": False, "operation": "observe_existing_job_only"}
