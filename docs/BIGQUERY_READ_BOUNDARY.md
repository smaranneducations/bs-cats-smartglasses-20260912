# BigQuery semantic read boundary

This implementation is one connection in the documented warehouse architecture,
not a claim that the full application is already BigQuery-backed.

## Authoritative preparation

Read-only BigQuery table metadata on 2026-09-13 confirmed the deployed schemas for
`catalog_products`, `catalog_assertions` and `semantic_definitions`, their US
location, recorded-time partition filters and zero stored rows. No query or load
job was required for that metadata inspection.

`packages/knowledge/bigquery_reader.py` uses those existing tables. It supplies
four fixed semantic operations: product records, assertion records, exact-hash
definitions and product comparisons. Identifiers and time windows are named
parameters. Agents cannot supply SQL, choose another project, access an arbitrary
table or remove the 10-64 MiB maximum-bytes-billed boundary.

Comparisons join assertions to the exact product version and definitions to the
exact concept/hash pair. Missing definitions remain explicit. Pending, rejected
or withdrawn data is not disguised by filtering it out before selecting the
latest version. A recorded-time window is knowledge history, not proof of a
claim's real-world validity. Warehouse presence is not independent verification.

## Job and spending lifecycle

Query tickets bind the immutable request, issue time and task idempotency key.
The provider job ID is deterministic for that key. Existing jobs must match the
query parameters, fingerprint and byte ceiling before being reused. A lost
submission response returns a reconciliation state. `resume` only reads that
same job; it never creates or retries a query. Result pages, response bytes,
identifiers, time windows and rows are bounded. Partial results fail explicitly.

Paid execution defaults to denial before transport or identity access. A future
production binding must implement `SpendGate` against the existing shared
experiment ledger, not create a separate budget. Its atomic reservation must
cover the full query byte ceiling using reconciled, current pricing and existing
per-job, daily and cumulative controls. It must preserve the ticket and
reservation in the durable harness before submission and recover the same job.
The interface alone is not proof that this binding is installed.

Completed job observations preserve unknown billed bytes and unknown monetary
costs. Provider byte statistics neither reconcile the project's bill nor authorize
additional jobs. No CLI override enables paid execution. The local inspection
command can only compile a plan or request a provider dry run.

## Identity and activation

The REST transport accepts an injected short-lived identity provider, keeps the
Google endpoint fixed, refuses redirects, caps request/response bodies and does
not print provider error bodies. The optional local identity helper uses an
existing gcloud login and captures its token in memory. It does not initiate
login, read `.env`, persist a token or copy credentials into a cloud service.

The application has not switched semantic reads to this adapter. Activation
requires the real shared-ledger binding, populated/versioned warehouse data,
appropriate cloud identity and an integration check. Billed execution remains
disabled while billing is unreconciled. These are release requirements rather
than an approved reduced scope.

## Focused evidence

`tests/test_bigquery_reader.py` exercises compilation, scope and time bounds,
default-denied execution, estimate freshness, identity of recovered jobs,
ambiguous responses, missing jobs, truncation and unknown cost handling with a
fake transport. Such tests do not prove live query execution or integration.

`scripts/inspect_warehouse.py dry-run` writes a private machine-readable report to
`.local/warehouse-probes/` after successful provider validation. Reports explicitly
distinguish a dry run from data retrieval, upload or billed execution. Actual test
and provider outcomes belong in the execution checkpoint, not inferred here.

## Provider references

- [BigQuery query dry run](https://cloud.google.com/bigquery/docs/samples/bigquery-query-dry-run)
- [Job configuration and byte limits](https://docs.cloud.google.com/bigquery/docs/reference/rest/v2/Job)
- [Job insertion](https://docs.cloud.google.com/bigquery/docs/reference/rest/v2/jobs/insert)
- [Query result retrieval](https://docs.cloud.google.com/bigquery/docs/reference/rest/v2/jobs/getQueryResults)
- [Job history and identity](https://docs.cloud.google.com/bigquery/docs/reference/rest/v2/jobs/get)
- [Pricing and separate storage charges](https://cloud.google.com/bigquery/pricing)
