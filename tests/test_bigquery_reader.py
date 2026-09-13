from __future__ import annotations

import copy
import json
import unittest
from datetime import datetime, timedelta, timezone

from packages.knowledge.bigquery_reader import (
    AdmissionDenied, BigQuerySemanticReader, DryRunEstimate, IncompleteResult,
    MAXIMUM_BYTES, ProtocolMismatch, QueryTicket, Reservation, SemanticRead,
    TransportFailure, query_configuration,
)

NOW = datetime(2026, 9, 13, 4, 0, tzinfo=timezone.utc)


def ticket(operation="comparison", **overrides):
    values = dict(operation=operation, ids=("product_xreal_one_pro_us", "product_xreal_one_us"), recorded_from=NOW - timedelta(days=1), recorded_before=NOW, limit=250)
    values.update(overrides)
    return QueryTicket(SemanticRead(**values), "test-warehouse-read-20260913", NOW)


class FakeGate:
    def __init__(self):
        self.observations = []

    def reserve(self, request, estimate):
        return Reservation("fixture-reservation", request.fingerprint, request.read.maximum_bytes_billed, NOW + timedelta(minutes=5))

    def observe(self, reservation, usage):
        self.observations.append(usage)


class FakeTransport:
    def __init__(self):
        self.job = None
        self.calls = []
        self.raise_after_submission = False
        self.results = [{"jobComplete": True, "totalRows": "1", "schema": {"fields": [{"name": "record_json", "type": "STRING"}]}, "rows": [{"f": [{"v": json.dumps({"product_id": "product_xreal_one_us", "review_state": "pending"})}]}]}]

    def dry_run(self, request):
        self.calls.append("dry_run")
        return {"statistics": {"query": {"totalBytesProcessed": "0", "statementType": "SELECT"}}}

    def get_job(self, request):
        self.calls.append("get_job")
        if self.job is None:
            raise TransportFailure(404)
        return copy.deepcopy(self.job)

    def submit_query(self, request):
        self.calls.append("submit_query")
        self.job = request.resource()
        self.job["status"] = {"state": "RUNNING"}
        if self.raise_after_submission:
            raise TransportFailure(None, ambiguous=True)
        return copy.deepcopy(self.job)

    def get_results(self, request, page_token=None):
        self.calls.append("get_results")
        return copy.deepcopy(self.results.pop(0))

    def complete(self, request, *, billed="10485760"):
        self.job = request.resource()
        self.job.update({"status": {"state": "DONE"}, "statistics": {"query": {"totalBytesProcessed": "512", "totalBytesBilled": billed}}})


class BigQueryReaderTests(unittest.TestCase):
    def setUp(self):
        self.transport = FakeTransport()
        self.gate = FakeGate()
        self.reader = BigQuerySemanticReader(self.transport, self.gate, clock=lambda: NOW)
        self.ticket = ticket()
        self.estimate = DryRunEstimate(self.ticket.fingerprint, 0, NOW, "SELECT")

    def test_compiles_every_operation_without_interpolating_ids(self):
        for operation in ("products", "assertions", "definitions", "comparison"):
            configuration = query_configuration(ticket(operation).read)
            self.assertNotIn("product_xreal_one_us", configuration["query"])
            self.assertIn("recorded_at >= @recorded_from", configuration["query"])
            self.assertIn("recorded_at < @recorded_before", configuration["query"])
            self.assertFalse(configuration["useLegacySql"])
            self.assertEqual(configuration["maximumBytesBilled"], str(MAXIMUM_BYTES))

    def test_comparison_pins_fact_version_and_definition_hash(self):
        sql = query_configuration(self.ticket.read)["query"]
        self.assertIn("a.object_version = p.object_version", sql)
        self.assertIn("d.definition_hash = a.definition_hash", sql)
        self.assertIn("assertion_review_state", sql)
        self.assertIn("definition_present", sql)
        self.assertNotIn("review_state = 'approved'", sql)

    def test_rejects_sql_injection_and_arbitrary_operations(self):
        for values in ({"ids": ("x'; DROP TABLE products; --",)}, {"operation": "raw_sql"}):
            with self.assertRaises(ValueError):
                ticket(**values)

    def test_rejects_missing_timezones_and_excessive_windows(self):
        for values in ({"recorded_before": NOW.replace(tzinfo=None)}, {"recorded_from": NOW - timedelta(days=367)}):
            with self.assertRaises(ValueError):
                ticket(**values)

    def test_rejects_unbounded_or_boolean_limits(self):
        for values in ({"limit": 501}, {"limit": True}, {"maximum_bytes_billed": MAXIMUM_BYTES + 1}):
            with self.assertRaises(ValueError):
                ticket(**values)

    def test_default_denial_precedes_identity_or_transport(self):
        reader = BigQuerySemanticReader(self.transport, clock=lambda: NOW)
        with self.assertRaises(AdmissionDenied):
            reader.submit(self.ticket, self.estimate)
        self.assertEqual(self.transport.calls, [])

    def test_dry_run_has_explicit_flag_and_does_not_submit(self):
        self.assertIs(self.ticket.resource(dry_run=True)["configuration"]["dryRun"], True)
        estimate = self.reader.estimate(self.ticket)
        self.assertEqual(estimate.bytes_processed, 0)
        self.assertEqual(self.transport.calls, ["dry_run"])
        self.assertEqual(self.gate.observations, [])

    def test_stale_and_over_limit_estimates_rejected_before_transport(self):
        for estimate in (DryRunEstimate(self.ticket.fingerprint, 0, NOW - timedelta(minutes=6), "SELECT"), DryRunEstimate(self.ticket.fingerprint, MAXIMUM_BYTES + 1, NOW, "SELECT")):
            with self.assertRaises(AdmissionDenied):
                self.reader.submit(self.ticket, estimate)
        self.assertEqual(self.transport.calls, [])

    def test_submission_uses_stable_job_and_returns_running(self):
        outcome = self.reader.submit(self.ticket, self.estimate)
        self.assertEqual(outcome["state"], "running")
        self.assertEqual(self.transport.calls, ["get_job", "submit_query"])
        self.assertEqual(outcome["job_id"], self.ticket.job_id)

    def test_ambiguous_submission_resumes_without_another_post(self):
        self.transport.raise_after_submission = True
        outcome = self.reader.submit(self.ticket, self.estimate)
        self.assertEqual(outcome["state"], "pending_reconciliation")
        self.transport.complete(self.ticket)
        result = self.reader.resume(self.ticket, self.gate.reserve(self.ticket, self.estimate))
        self.assertEqual(result["state"], "succeeded")
        self.assertEqual(self.transport.calls.count("submit_query"), 1)
        self.assertEqual(result["rows"][0]["review_state"], "pending")

    def test_missing_job_recovery_never_recreates_it(self):
        result = self.reader.resume(self.ticket, self.gate.reserve(self.ticket, self.estimate))
        self.assertEqual(result["state"], "missing_job_requires_reconciliation")
        self.assertEqual(self.transport.calls, ["get_job"])

    def test_existing_job_with_different_inputs_is_rejected(self):
        self.transport.complete(self.ticket)
        self.transport.job["configuration"]["query"]["query"] = "SELECT 'different'"
        with self.assertRaises(ProtocolMismatch):
            self.reader.submit(self.ticket, self.estimate)
        self.assertNotIn("submit_query", self.transport.calls)

    def test_missing_billed_bytes_remain_unknown(self):
        self.transport.complete(self.ticket, billed=None)
        result = self.reader.submit(self.ticket, self.estimate)
        self.assertIsNone(result["bytes_billed"])
        self.assertIsNone(self.gate.observations[0]["currency_cost"])
        self.assertFalse(result["warehouse_presence_is_fact_verification"])

    def test_truncation_is_not_presented_as_complete_data(self):
        self.transport.complete(self.ticket)
        self.transport.results[0]["totalRows"] = "251"
        with self.assertRaises(IncompleteResult):
            self.reader.submit(self.ticket, self.estimate)

    def test_row_count_mismatch_is_rejected(self):
        self.transport.complete(self.ticket)
        self.transport.results[0]["totalRows"] = "2"
        with self.assertRaises(IncompleteResult):
            self.reader.submit(self.ticket, self.estimate)

    def test_failed_job_reports_usage_without_fetching_or_retrying(self):
        self.transport.complete(self.ticket)
        self.transport.job["status"]["errorResult"] = {"reason": "resourcesExceeded"}
        result = self.reader.submit(self.ticket, self.estimate)
        self.assertEqual(result["state"], "failed")
        self.assertTrue(self.gate.observations[0]["failed"])
        self.assertNotIn("get_results", self.transport.calls)
        self.assertNotIn("submit_query", self.transport.calls)


if __name__ == "__main__":
    unittest.main()
