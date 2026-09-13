# Warehouse execution through the shared runtime

**Execution status, 2026-09-13 05:44 UTC: not ready for activation.** The focused
suite ran 18 tests: 10 passed and 8 errored because the new adapter attempts a
nested `BEGIN IMMEDIATE` while `RuntimeLedger.connection()` already has an active
transaction. Reservation success, concurrency and recovery are consequently not
proven. No correction has been applied pending the human correction decision.
The running server has not been restarted to load these routes, and paid
execution remains disabled. The public-reference timestamp in the initial price
file was prefilled rather than recorded from the tool clock; it is not valid
observation evidence and also needs correction. Account applicability remains
explicitly unverified. The design below is an implementation target, not a claim
that its failing paths work.

This is the bounded query execution adapter, not a claim that cloud tables are
populated or that the default semantic backend has switched to BigQuery.

## Interfaces

- `GET /v1/warehouse/status` reports the real admission state.
- `POST /v1/warehouse/queries` accepts a typed products, assertions or comparison
  request with governed product IDs, a recorded time window and an idempotency key.
- `POST /v1/warehouse/queries/{query_id}/resume` observes the same provider job. It
  does not create a replacement job or release a reservation because a timer ran out.

These routes use the existing authenticated actor and mutation middleware. They
offer no endpoint to arm spending, alter account pricing or approve publication.
The existing semantic routes still use the local store; there is no silent local
fallback when a warehouse query is unavailable.

## Shared cost boundary

The adapter calls the same `local_ledger()` factory as the runtime API. Reservations
are rows in `runtime_tasks`, which the existing `RuntimeLedger.totals` includes in
its outstanding total. Their explicit external states keep them out of the local
deterministic worker queue. There is no second spend ledger.

Reservation admission uses an immediate SQLite transaction, existing expenses,
all outstanding reservations, the shared pause flag and shared task/day/lifetime
limits. It additionally applies the charter's $2/job, $5/day and $450 stop limits.
Accounting must be reconciled within six hours, unknown costs must be resolved,
and the shared paid-execution arm must already be enabled. This adapter never
changes those financial controls.

The public price reference is not an applicable account price. The checked-in
configuration deliberately leaves account currency, billing model confirmation
and the current all-in USD upper bound unverified. No free-tier allowance or credit
is assumed. Non-USD account conversion is not automatically inferred.

For this fixed on-demand SELECT path, maximum bytes billed, not the dry-run
estimate, determine the rounded-up cent reservation. The current reader allows
at most 64 MiB. Google documents the on-demand pricing and maximum-bytes control
at [BigQuery pricing](https://cloud.google.com/bigquery/pricing) and the
[Job API](https://docs.cloud.google.com/bigquery/docs/reference/rest/v2/Job).
This does not cap unrelated services, storage, subscriptions or account charges.

Provider observations are audit evidence, not settled invoices. Reservations are
retained after observation, failure or expiry until authoritative accounting can
reconcile them. This deliberately favors preserving the experiment envelope over
claiming an uncertain job was free.

## Execution and identity

The query ticket binds the actor, request, exact product versions and provider
idempotency key. Fixed SQL, typed parameters, byte caps, bounded result pages and
same-job recovery are supplied by the existing BigQuery reader. The service
rejects an idempotency key reused with different inputs.

The current transport is the existing local gcloud identity, enabled only in a
local/development/test environment with `WAREHOUSE_QUERY_ADAPTER_ENABLED=1`.
There is no downloaded service-account key and no copy of OAuth credentials into
the project. This is not a production Cloud Run identity implementation.

## Verification scope

`tests/test_warehouse_execution.py` uses an isolated real SQLite ledger to exercise
shared totals, atomic concurrent admission, expiry, pause, unknown accounting,
price applicability and denial before transport construction. It does not prove
live billed queries, cloud deployment, source rights, data population or UI quality.
Actual executed results are recorded in the execution checkpoint separately.
