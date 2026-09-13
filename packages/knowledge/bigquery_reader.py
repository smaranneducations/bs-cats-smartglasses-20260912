"""Bounded BigQuery semantic reads. Paid execution is denied without a ledger gate.

The request is a domain operation, never agent-authored SQL. Submission and
reconciliation are separate so a lost response does not cause a fresh job.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


PROJECT = "bs-cats-smartglasses-20260912"
DATASET = "smart_glasses_core"
LOCATION = "US"
MAXIMUM_BYTES = 64 * 1024 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
OPERATIONS = frozenset({"products", "assertions", "definitions", "comparison"})
TABLES = frozenset({"catalog_products", "catalog_assertions", "semantic_definitions"})
UTC = timezone.utc


class WarehouseError(RuntimeError):
    pass


class AdmissionDenied(WarehouseError):
    pass


class ProtocolMismatch(WarehouseError):
    pass


class IncompleteResult(WarehouseError):
    pass


class TransportFailure(WarehouseError):
    def __init__(self, status: int | None, *, ambiguous: bool = False):
        self.status = status
        self.ambiguous = ambiguous
        super().__init__("warehouse transport unavailable" if status is None else f"warehouse HTTP {status}")


def utc_now() -> datetime:
    return datetime.now(UTC)


def stamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("an explicit timezone is required")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class SemanticRead:
    operation: str
    ids: tuple[str, ...]
    recorded_from: datetime
    recorded_before: datetime
    limit: int = 250
    maximum_bytes_billed: int = MAXIMUM_BYTES

    def __post_init__(self) -> None:
        if self.operation not in OPERATIONS:
            raise ValueError("unsupported semantic operation")
        if not isinstance(self.ids, tuple) or not 1 <= len(self.ids) <= 20:
            raise ValueError("supply one to twenty immutable identifiers")
        if len(set(self.ids)) != len(self.ids):
            raise ValueError("duplicate identifiers are not permitted")
        if any(not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", value) for value in self.ids):
            raise ValueError("invalid domain identifier")
        if self.operation == "comparison" and not 2 <= len(self.ids) <= 4:
            raise ValueError("comparisons require two to four product identifiers")
        stamp(self.recorded_from)
        stamp(self.recorded_before)
        if not timedelta(0) < self.recorded_before - self.recorded_from <= timedelta(days=366):
            raise ValueError("recorded-time window must be positive and at most 366 days")
        if type(self.limit) is not int or not 1 <= self.limit <= 500:
            raise ValueError("row limit must be between one and five hundred")
        if type(self.maximum_bytes_billed) is not int or not 10 * 1024 * 1024 <= self.maximum_bytes_billed <= MAXIMUM_BYTES:
            raise ValueError("query byte limit must be between 10 and 64 MiB")
        object.__setattr__(self, "ids", tuple(sorted(self.ids)))


def _table(name: str) -> str:
    if name not in TABLES:
        raise ValueError("table is outside the semantic read boundary")
    return f"`{PROJECT}.{DATASET}.{name}`"


def _latest(table: str, selector: str, partition: str, order: str) -> str:
    return (
        f"SELECT * FROM {_table(table)}\n"
        "WHERE recorded_at >= @recorded_from AND recorded_at < @recorded_before\n"
        f"AND {selector}\n"
        f"QUALIFY ROW_NUMBER() OVER (PARTITION BY {partition} ORDER BY {order}) = 1"
    )


def query_configuration(read: SemanticRead) -> dict[str, Any]:
    """Compile fixed templates, preserving review states and definition identity."""
    products = _latest("catalog_products", "product_id IN UNNEST(@ids)", "product_id", "object_version DESC, recorded_at DESC, row_id DESC")
    assertions = _latest("catalog_assertions", "subject_id IN UNNEST(@ids)", "subject_id, concept_id", "object_version DESC, recorded_at DESC, row_id DESC")
    if read.operation == "products":
        sql = f"WITH current_records AS ({products}) SELECT TO_JSON_STRING(t) AS record_json FROM current_records t ORDER BY product_id LIMIT @row_limit"
    elif read.operation == "assertions":
        sql = f"WITH current_records AS ({assertions}) SELECT TO_JSON_STRING(t) AS record_json FROM current_records t ORDER BY subject_id, concept_id LIMIT @row_limit"
    elif read.operation == "definitions":
        definitions = _latest("semantic_definitions", "definition_hash IN UNNEST(@ids)", "concept_id, definition_hash", "recorded_at DESC, row_id DESC")
        sql = f"WITH current_records AS ({definitions}) SELECT TO_JSON_STRING(t) AS record_json FROM current_records t ORDER BY concept_id, definition_hash LIMIT @row_limit"
    else:
        definitions = _latest("semantic_definitions", "TRUE", "concept_id, definition_hash", "recorded_at DESC, row_id DESC")
        sql = (
            f"WITH products AS ({products}), assertions AS ({assertions}), definitions AS ({definitions})\n"
            "SELECT TO_JSON_STRING(STRUCT(\n"
            "p.product_id, p.object_version, p.brand, p.model, p.category, p.market, p.variant,\n"
            "p.review_state AS product_review_state, p.status AS product_status,\n"
            "a.assertion_id, a.concept_id, a.definition_hash, a.value_number, a.value_text,\n"
            "a.value_boolean, a.value_state, a.unit, a.observed_at, a.valid_from, a.valid_to,\n"
            "a.evidence_kind, a.confidence, a.confidence_reason, a.conditions,\n"
            "a.review_state AS assertion_review_state, a.source_ids, a.evidence_ids,\n"
            "d.definition, d.constraints AS definition_constraints,\n"
            "d.definition_hash IS NOT NULL AS definition_present\n"
            ")) AS record_json\n"
            "FROM products p LEFT JOIN assertions a\n"
            "ON a.subject_id = p.product_id AND a.object_version = p.object_version\n"
            "LEFT JOIN definitions d ON d.concept_id = a.concept_id AND d.definition_hash = a.definition_hash\n"
            "ORDER BY p.product_id, a.concept_id LIMIT @row_limit"
        )
    parameters = [
        {"name": "ids", "parameterType": {"type": "ARRAY", "arrayType": {"type": "STRING"}}, "parameterValue": {"arrayValues": [{"value": value} for value in read.ids]}},
        {"name": "recorded_from", "parameterType": {"type": "TIMESTAMP"}, "parameterValue": {"value": stamp(read.recorded_from)}},
        {"name": "recorded_before", "parameterType": {"type": "TIMESTAMP"}, "parameterValue": {"value": stamp(read.recorded_before)}},
        {"name": "row_limit", "parameterType": {"type": "INT64"}, "parameterValue": {"value": str(read.limit + 1)}},
    ]
    return {
        "query": sql,
        "useLegacySql": False,
        "useQueryCache": True,
        "priority": "INTERACTIVE",
        "parameterMode": "NAMED",
        "queryParameters": parameters,
        "maximumBytesBilled": str(read.maximum_bytes_billed),
    }


@dataclass(frozen=True)
class QueryTicket:
    read: SemanticRead
    idempotency_key: str
    issued_at: datetime

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.:/-]{8,200}", self.idempotency_key):
            raise ValueError("a bounded task idempotency key is required")
        stamp(self.issued_at)

    @property
    def job_id(self) -> str:
        return "sg_read_" + hashlib.sha256(self.idempotency_key.encode()).hexdigest()

    @property
    def fingerprint(self) -> str:
        return digest({"project": PROJECT, "location": LOCATION, "query": query_configuration(self.read), "issued_at": stamp(self.issued_at)})

    def resource(self, *, dry_run: bool = False) -> dict[str, Any]:
        configuration: dict[str, Any] = {
            "query": query_configuration(self.read),
            "jobTimeoutMs": "30000",
            "labels": {"sg_plan_a": self.fingerprint[:32], "sg_plan_b": self.fingerprint[32:]},
        }
        if dry_run:
            configuration["dryRun"] = True
        return {"jobReference": {"projectId": PROJECT, "location": LOCATION, "jobId": self.job_id}, "configuration": configuration}


@dataclass(frozen=True)
class DryRunEstimate:
    fingerprint: str
    bytes_processed: int
    observed_at: datetime
    statement_type: str | None


@dataclass(frozen=True)
class Reservation:
    reservation_id: str
    fingerprint: str
    maximum_bytes_billed: int
    expires_at: datetime


class SpendGate(Protocol):
    """Production implementation must use the shared, reconciled experiment ledger.

    reserve is atomic/idempotent for the ticket. It prices the full byte ceiling,
    not just the dry-run estimate. observe must retain unknown charges and must
    not treat query bytes as a complete project bill.
    """

    def reserve(self, ticket: QueryTicket, estimate: DryRunEstimate) -> Reservation: ...

    def observe(self, reservation: Reservation, usage: dict[str, Any]) -> None: ...


class DenyPaidExecution:
    def reserve(self, ticket: QueryTicket, estimate: DryRunEstimate) -> Reservation:
        raise AdmissionDenied("reconciled shared-ledger admission is not connected; billed queries remain disabled")

    def observe(self, reservation: Reservation, usage: dict[str, Any]) -> None:
        raise AdmissionDenied("no admitted warehouse reservation is available")


class ExistingGcloudIdentity:
    """Use an existing local login without reading .env or exposing the token."""

    def __init__(self, *, explicitly_enabled: bool = False):
        self.enabled = explicitly_enabled

    def __call__(self) -> str:
        if not self.enabled:
            raise AdmissionDenied("existing local cloud identity was not enabled")
        try:
            result = subprocess.run(
                ["/opt/homebrew/bin/gcloud", "auth", "print-access-token", "--quiet"],
                capture_output=True, text=True, timeout=15, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            raise WarehouseError("existing local cloud identity is unavailable") from None
        token = result.stdout.strip()
        if result.returncode != 0 or not 20 <= len(token) <= 16384 or any(character.isspace() for character in token):
            raise WarehouseError("existing local cloud identity is unavailable")
        return token


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


class BigQueryTransport:
    """Fixed Google endpoint, bounded bodies, no automatic POST retries."""

    def __init__(self, identity: Callable[[], str]):
        self.identity = identity
        self.opener = build_opener(ProxyHandler({}), _NoRedirect())

    def _request(self, method: str, suffix: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        encoded = None if body is None else json.dumps(body, allow_nan=False).encode()
        if encoded is not None and len(encoded) > 128 * 1024:
            raise ValueError("warehouse request exceeds its body limit")
        request = Request(
            f"https://bigquery.googleapis.com/bigquery/v2/projects/{PROJECT}/{suffix}",
            data=encoded, method=method,
            headers={"Authorization": "Bearer " + self.identity(), "Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with self.opener.open(request, timeout=12) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as error:
            status = error.code
            error.close()
            raise TransportFailure(status, ambiguous=method == "POST" and status >= 500) from None
        except (URLError, TimeoutError, OSError):
            raise TransportFailure(None, ambiguous=method == "POST") from None
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ProtocolMismatch("warehouse response exceeds its byte limit")
        try:
            parsed = json.loads(raw)
        except (UnicodeDecodeError, ValueError):
            raise ProtocolMismatch("warehouse returned an invalid JSON response") from None
        if not isinstance(parsed, dict):
            raise ProtocolMismatch("warehouse response is not an object")
        return parsed

    def dry_run(self, ticket: QueryTicket) -> dict[str, Any]:
        return self._request("POST", "jobs", ticket.resource(dry_run=True))

    def get_job(self, ticket: QueryTicket) -> dict[str, Any]:
        return self._request("GET", f"jobs/{ticket.job_id}?" + urlencode({"location": LOCATION}))

    def submit_query(self, ticket: QueryTicket) -> dict[str, Any]:
        return self._request("POST", "jobs", ticket.resource())

    def get_results(self, ticket: QueryTicket, page_token: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"location": LOCATION, "maxResults": ticket.read.limit + 1, "timeoutMs": 0}
        if page_token:
            if not isinstance(page_token, str) or len(page_token) > 4096:
                raise ProtocolMismatch("invalid warehouse page token")
            params["pageToken"] = page_token
        return self._request("GET", f"queries/{ticket.job_id}?" + urlencode(params))


def _nonnegative_integer(value: Any, *, optional: bool = False) -> int | None:
    if optional and value is None:
        return None
    if isinstance(value, bool) or not re.fullmatch(r"\d+", str(value)):
        raise ProtocolMismatch("warehouse count is missing or invalid")
    return int(value)


class BigQuerySemanticReader:
    def __init__(self, transport: Any, gate: SpendGate | None = None, *, clock: Callable[[], datetime] = utc_now):
        self.transport = transport
        self.gate = gate if gate is not None else DenyPaidExecution()
        self.clock = clock

    def estimate(self, ticket: QueryTicket) -> DryRunEstimate:
        """A documented BigQuery dry run; this does not submit a billed query."""
        result = self.transport.dry_run(ticket)
        statistics = result.get("statistics", {})
        query = statistics.get("query", {})
        statement_type = query.get("statementType")
        if statement_type is not None and statement_type != "SELECT":
            raise ProtocolMismatch("dry run did not describe a read-only statement")
        for table in query.get("referencedTables", []):
            if table.get("projectId") != PROJECT or table.get("datasetId") != DATASET or table.get("tableId") not in TABLES:
                raise ProtocolMismatch("dry run referenced a resource outside the warehouse boundary")
        estimated = _nonnegative_integer(query.get("totalBytesProcessed", statistics.get("totalBytesProcessed")))
        assert estimated is not None
        return DryRunEstimate(ticket.fingerprint, estimated, self.clock(), statement_type)

    def submit(self, ticket: QueryTicket, estimate: DryRunEstimate) -> dict[str, Any]:
        """At most one new POST. Persist the ticket and reservation before resume."""
        now = self.clock()
        if not timedelta(minutes=-1) <= now - ticket.issued_at <= timedelta(hours=24):
            raise AdmissionDenied("query ticket is outside its submission window")
        if estimate.fingerprint != ticket.fingerprint or not timedelta(0) <= now - estimate.observed_at <= timedelta(minutes=5):
            raise AdmissionDenied("query estimate is stale or belongs to another request")
        if estimate.bytes_processed > ticket.read.maximum_bytes_billed:
            raise AdmissionDenied("dry-run estimate exceeds the enforced query byte ceiling")
        reservation = self.gate.reserve(ticket, estimate)
        self._reservation(ticket, reservation, require_fresh=True)
        try:
            try:
                job = self.transport.get_job(ticket)
            except TransportFailure as error:
                if error.status != 404:
                    raise
                try:
                    job = self.transport.submit_query(ticket)
                except TransportFailure as duplicate:
                    if duplicate.status != 409:
                        raise
                    job = self.transport.get_job(ticket)
            return self._finish(ticket, reservation, job)
        except TransportFailure:
            return self._pending(ticket, reservation, "pending_reconciliation")

    def resume(self, ticket: QueryTicket, reservation: Reservation) -> dict[str, Any]:
        """Read the SAME provider job. Never creates, replaces or retries a job."""
        self._reservation(ticket, reservation, require_fresh=False)
        try:
            job = self.transport.get_job(ticket)
            return self._finish(ticket, reservation, job)
        except TransportFailure as error:
            return self._pending(ticket, reservation, "missing_job_requires_reconciliation" if error.status == 404 else "pending_reconciliation")

    def _reservation(self, ticket: QueryTicket, reservation: Reservation, *, require_fresh: bool) -> None:
        if not isinstance(reservation, Reservation) or not reservation.reservation_id or reservation.fingerprint != ticket.fingerprint:
            raise AdmissionDenied("shared-ledger reservation does not match the exact query")
        if reservation.maximum_bytes_billed != ticket.read.maximum_bytes_billed:
            raise AdmissionDenied("reservation does not cover the exact byte ceiling")
        stamp(reservation.expires_at)
        if require_fresh and not self.clock() < reservation.expires_at <= self.clock() + timedelta(minutes=15):
            raise AdmissionDenied("shared-ledger reservation is expired or exceeds the admission window")

    def _pending(self, ticket: QueryTicket, reservation: Reservation, state: str) -> dict[str, Any]:
        return {"state": state, "job_id": ticket.job_id, "fingerprint": ticket.fingerprint, "reservation_id": reservation.reservation_id, "rows": None, "bytes_billed": None, "must_resume_same_job": True}

    def _validate_job(self, ticket: QueryTicket, job: dict[str, Any]) -> None:
        reference = job.get("jobReference", {})
        if reference.get("projectId") != PROJECT or reference.get("jobId") != ticket.job_id or str(reference.get("location", "")).upper() != LOCATION:
            raise ProtocolMismatch("provider job identity does not match the ticket")
        expected = ticket.resource()["configuration"]
        configuration = job.get("configuration", {})
        labels = configuration.get("labels", {})
        if any(labels.get(key) != value for key, value in expected["labels"].items()):
            raise ProtocolMismatch("idempotency key was reused for different query inputs")
        query = configuration.get("query", {})
        for key in ("query", "useLegacySql", "parameterMode", "queryParameters"):
            if query.get(key) != expected["query"][key]:
                raise ProtocolMismatch("provider query differs from the admitted query")
        if str(query.get("maximumBytesBilled")) != expected["query"]["maximumBytesBilled"]:
            raise ProtocolMismatch("provider query byte ceiling differs from admission")

    def _finish(self, ticket: QueryTicket, reservation: Reservation, job: dict[str, Any]) -> dict[str, Any]:
        self._validate_job(ticket, job)
        status = job.get("status", {})
        if status.get("state") != "DONE":
            return self._pending(ticket, reservation, "running")
        statistics = job.get("statistics", {}).get("query", {})
        billed = _nonnegative_integer(statistics.get("totalBytesBilled"), optional=True)
        usage = {"job_id": ticket.job_id, "fingerprint": ticket.fingerprint, "provider_state": "DONE", "failed": bool(status.get("errorResult")), "bytes_billed": billed, "bytes_processed": _nonnegative_integer(statistics.get("totalBytesProcessed"), optional=True), "currency_cost": None, "all_project_costs_known": False}
        self.gate.observe(reservation, usage)
        if status.get("errorResult"):
            return {**self._pending(ticket, reservation, "failed"), "bytes_billed": billed, "must_resume_same_job": False}
        rows: list[dict[str, Any]] = []
        page_token: str | None = None
        for _ in range(2):
            result = self.transport.get_results(ticket, page_token)
            if result.get("jobComplete") is not True:
                return self._pending(ticket, reservation, "waiting_for_results")
            total = _nonnegative_integer(result.get("totalRows"))
            if total is not None and total > ticket.read.limit:
                raise IncompleteResult("warehouse result exceeds the declared semantic result limit")
            fields = result.get("schema", {}).get("fields", [])
            if fields and [(field.get("name"), field.get("type")) for field in fields] != [("record_json", "STRING")]:
                raise ProtocolMismatch("warehouse result schema does not match the compiled projection")
            for row in result.get("rows", []):
                cells = row.get("f", [])
                if len(cells) != 1 or not isinstance(cells[0].get("v"), str):
                    raise ProtocolMismatch("warehouse semantic row is malformed")
                try:
                    value = json.loads(cells[0]["v"])
                except ValueError:
                    raise ProtocolMismatch("warehouse semantic row is not JSON") from None
                if not isinstance(value, dict):
                    raise ProtocolMismatch("warehouse semantic row is not an object")
                rows.append(value)
                if len(rows) > ticket.read.limit:
                    raise IncompleteResult("warehouse returned too many semantic rows")
            page_token = result.get("pageToken")
            if not page_token:
                if len(rows) != total:
                    raise IncompleteResult("warehouse row count does not match its completed result")
                return {"state": "succeeded", "backend": "bigquery", "job_id": ticket.job_id, "fingerprint": ticket.fingerprint, "rows": rows, "bytes_billed": billed, "recorded_window": {"from": stamp(ticket.read.recorded_from), "before": stamp(ticket.read.recorded_before)}, "recorded_window_is_real_world_validity": False, "warehouse_presence_is_fact_verification": False}
        raise IncompleteResult("warehouse result exceeded its bounded page budget")
