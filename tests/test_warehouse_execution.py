import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from packages.contracts.warehouse_execution import WarehousePricePolicy, WarehouseQueryRequest
from packages.knowledge.bigquery_reader import AdmissionDenied, DryRunEstimate, QueryTicket, SemanticRead
from packages.knowledge.warehouse_execution import SharedWarehouseSpendGate, WarehouseExecutionService
from packages.runtime.ledger import RuntimeLedger

NOW = datetime(2026, 9, 13, 6, 0, tzinfo=timezone.utc)
IDS = ("product_xreal_one_us", "product_xreal_one_pro_us")


def price(**changes):
    values = dict(public_reference_uri="https://cloud.google.com/bigquery/pricing",
                  public_reference_usd_per_tib="6.25", public_reference_observed_at=NOW,
                  account_currency="USD", account_on_demand_verified=True,
                  verified_upper_bound_usd_per_tib="6.25", verification_evidence_ref="fixture:verified-account-pricing",
                  verified_at=NOW - timedelta(minutes=1), valid_until=NOW + timedelta(hours=1))
    values.update(changes)
    return WarehousePricePolicy(**values)


def ticket(key="warehouse:test-query-001"):
    return QueryTicket(SemanticRead("comparison", IDS, NOW - timedelta(days=1), NOW, 250, 64 * 1024 * 1024), key, NOW)


def estimate(query):
    return DryRunEstimate(query.fingerprint, 1024, NOW, "SELECT")


class Store:
    def get(self, object_id):
        return SimpleNamespace(object_type="product", version=1)


class WarehouseExecutionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.ledger = RuntimeLedger(Path(self.directory.name) / "runtime.sqlite3")
        with self.ledger.connection() as connection:
            connection.execute("UPDATE runtime_budget SET unknown_costs=0,paid_armed=1,reconciled_at=? WHERE singleton=1", (NOW.timestamp(),))
        self.gate = SharedWarehouseSpendGate(self.ledger, price(), "research-agent", {key: 1 for key in IDS}, clock=lambda: NOW)

    def tearDown(self):
        self.directory.cleanup()

    def budget(self, **values):
        with self.ledger.connection() as connection:
            connection.execute("UPDATE runtime_budget SET " + ",".join(key + "=?" for key in values) + " WHERE singleton=1", tuple(values.values()))

    def test_reservation_is_visible_in_existing_shared_total(self):
        query = ticket()
        self.gate.reserve(query, estimate(query))
        self.assertEqual(self.ledger.status()["outstanding_reservations_cents"], 1)

    def test_same_ticket_reuses_one_reservation(self):
        query = ticket()
        first = self.gate.reserve(query, estimate(query))
        self.assertEqual(first, self.gate.reserve(query, estimate(query)))
        self.assertEqual(self.ledger.status()["outstanding_reservations_cents"], 1)

    def test_unknown_costs_deny_admission(self):
        self.budget(unknown_costs=1)
        with self.assertRaises(AdmissionDenied):
            self.gate.preflight(64 * 1024 * 1024)

    def test_stale_accounting_denies_at_exact_boundary(self):
        self.budget(reconciled_at=(NOW - timedelta(hours=6)).timestamp())
        with self.assertRaises(AdmissionDenied):
            self.gate.preflight(64 * 1024 * 1024)

    def test_unarmed_ledger_denies(self):
        self.budget(paid_armed=0)
        with self.assertRaises(AdmissionDenied):
            self.gate.preflight(64 * 1024 * 1024)

    def test_pause_denies_new_or_repeated_submission(self):
        query = ticket()
        self.gate.reserve(query, estimate(query))
        self.ledger.set_paused(True, "test-human")
        with self.assertRaises(AdmissionDenied):
            self.gate.reserve(query, estimate(query))

    def test_unknown_account_price_denies(self):
        self.gate.price = price(account_on_demand_verified=False)
        with self.assertRaises(AdmissionDenied):
            self.gate.preflight(64 * 1024 * 1024)

    def test_exact_price_expiry_denies(self):
        self.gate.price = price(valid_until=NOW)
        with self.assertRaises(AdmissionDenied):
            self.gate.preflight(64 * 1024 * 1024)

    def test_changed_estimate_fingerprint_denies(self):
        query = ticket()
        wrong = DryRunEstimate("0" * 64, 100, NOW, "SELECT")
        with self.assertRaises(AdmissionDenied):
            self.gate.reserve(query, wrong)

    def test_maximum_bytes_not_dry_run_bytes_determine_reservation(self):
        query = ticket()
        self.gate.reserve(query, DryRunEstimate(query.fingerprint, 0, NOW, "SELECT"))
        self.assertEqual(self.ledger.status()["outstanding_reservations_cents"], 1)

    def test_daily_limit_is_atomic_across_two_connections(self):
        self.budget(day_limit_cents=1)
        def reserve(key):
            query = ticket(key)
            try:
                self.gate.reserve(query, estimate(query))
                return True
            except AdmissionDenied:
                return False
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(reserve, ("warehouse:parallel-one", "warehouse:parallel-two")))
        self.assertEqual(sum(results), 1)
        self.assertEqual(self.ledger.status()["outstanding_reservations_cents"], 1)

    def test_experiment_stop_includes_existing_expenses(self):
        with self.ledger.connection() as connection:
            connection.execute("INSERT INTO runtime_expenses VALUES ('fixture-other',37000,'fixture','2026-09-12','test','fixture:cost')")
        with self.assertRaises(AdmissionDenied):
            self.gate.preflight(64 * 1024 * 1024)

    def test_usage_observation_keeps_reservation_and_does_not_settle_cost(self):
        query = ticket()
        reservation = self.gate.reserve(query, estimate(query))
        self.gate.observe(reservation, {"bytes_billed": 1024, "currency_cost": None})
        self.assertEqual(self.ledger.status()["outstanding_reservations_cents"], 1)
        with self.ledger.connection() as connection:
            row = connection.execute("SELECT result_json FROM runtime_tasks WHERE task_id=?", (reservation.reservation_id,)).fetchone()
        self.assertIsNone(json.loads(row[0])["settled_charge_cents"])

    def test_generic_worker_does_not_claim_or_release_external_reservation(self):
        query = ticket()
        self.gate.reserve(query, estimate(query))
        self.assertIsNone(self.ledger.claim("test-worker"))
        self.assertEqual(self.ledger.status()["outstanding_reservations_cents"], 1)

    def test_expiry_does_not_release_reserved_money(self):
        query = ticket()
        self.gate.reserve(query, estimate(query))
        self.gate.clock = lambda: NOW + timedelta(minutes=5)
        fresh = DryRunEstimate(query.fingerprint, 1024, NOW + timedelta(minutes=5), "SELECT")
        with self.assertRaises(AdmissionDenied):
            self.gate.reserve(query, fresh)
        self.assertEqual(self.ledger.status()["outstanding_reservations_cents"], 1)

    def test_live_style_unreconciled_request_never_constructs_transport(self):
        self.budget(unknown_costs=1)
        calls = []
        def transport():
            calls.append(True)
            raise AssertionError("Transport must not be constructed")
        service = WarehouseExecutionService(self.ledger, Store(), price(), transport, enabled=True, clock=lambda: NOW)
        request = WarehouseQueryRequest(operation="comparison", ids=list(IDS), recorded_from=NOW-timedelta(days=1), recorded_before=NOW, idempotency_key="api-denied-query-1")
        with self.assertRaises(AdmissionDenied):
            service.execute(request, "research-agent")
        self.assertEqual(calls, [])

    def test_arbitrary_sql_and_billing_overrides_are_rejected(self):
        values = dict(operation="comparison", ids=list(IDS), recorded_from=NOW-timedelta(days=1), recorded_before=NOW, idempotency_key="api-query-contract-1")
        with self.assertRaises(ValueError):
            WarehouseQueryRequest(**values, sql="SELECT * FROM anything")
        with self.assertRaises(ValueError):
            WarehouseQueryRequest(**values, paid_armed=True)

    def test_resume_without_admission_does_not_construct_transport(self):
        service = WarehouseExecutionService(self.ledger, Store(), price(), lambda: self.fail("No transport permitted"), enabled=True, clock=lambda: NOW)
        with self.assertRaises(AdmissionDenied):
            service.resume("wq_" + "0" * 32, "research-agent")
