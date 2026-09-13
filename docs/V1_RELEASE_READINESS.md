# Version 1 release readiness

Snapshot date: 2026-09-13. Intended tag: `v1.0.0-rc.1` until production gates pass.

## Release decision

The repository is suitable for a versioned release-candidate freeze after its automated checks pass. It is not suitable for a “fully deployed and revenue-producing” claim.

## Observed cloud state

| Resource | Observed state |
| --- | --- |
| GCP and Firebase project | Active: `bs-cats-smartglasses-20260912` |
| Billing link | Enabled; actual charges not reconciled |
| Firebase Authentication | Project configured; Google provider was enabled by the account holder; hosted login not exercised |
| Firestore | Native database exists in `us-central1`; application cutover incomplete |
| Cloud Storage | Project asset bucket exists in `US-CENTRAL1`; approved canonical media not staged |
| BigQuery | Dataset and 14 planned tables exist; recorded project row count is zero |
| Firebase Hosting | Hosting site exists; no version 1 deployment receipt recorded |
| Cloud Run | No service observed in `us-central1` |
| GitHub | Remote is configured; current GitHub CLI credential is invalid and prevents push or release creation |

## Implemented release-candidate capabilities

- Versioned governed objects, schemas, transitions, evidence and actor metadata
- Local operator, audience, intelligence, comparison, feedback, media-review and release surfaces
- Domain configuration and semantic definitions for the smart-glasses pilot
- Bounded task runtime, model advice and cost ledger interfaces
- Research, Gmail alert, YouTube market, commerce and learning workflow code with explicit gates
- Rights-aware media catalog and local kinetic renderer with original background music support
- Canonical 30 to 90 second content contracts and exact-hash distribution packages
- YouTube and LinkedIn publishing adapters plus manual kits for unsupported channels
- Owned interaction and metrics projection contracts
- Firebase rules, BigQuery schema, container definition and deterministic Hosting bundle builder
- Requirements traceability and release-readiness automation

## Production blockers

| Blocker | Why it matters | Required closure evidence |
| --- | --- | --- |
| Disclosed credentials are not all rotated | Publicly disclosed long-lived secrets cannot be trusted | Provider rotation receipts and local status-only validation |
| Actual provider charges are unknown | Unattended paid work cannot enforce the cumulative budget | Current billing export or scoped charge reconciliation |
| API still uses local object persistence | Cloud Run filesystem is ephemeral and multi-instance unsafe | Firestore-backed application store integration tests and workload identity |
| No deployed Cloud Run service | Firebase cannot route dynamic APIs to an absent backend | Deployment receipt, URL, revision, IAM, min/max instances and health check |
| No approved canonical video package | Exact-artifact publication approval is mandatory | Approval object binding video and metadata hashes |
| Media rights remain unresolved for current renders | A render can work technically and still be unlawful to publish | Asset-level rights decisions and release gate pass |
| No owned-app production deployment | Audience flow and retained media are not publicly available | Firebase Hosting release receipt and browser acceptance evidence |
| No channel publication receipt | Adapters are not proof of provider success or eligibility | One idempotently reconciled provider receipt |
| No returned production metrics | Revenue and learning loop are not closed | Owned event plus authorized platform snapshot bound to release version |
| Repository license is undecided | Public visibility alone does not grant reuse rights | Human-approved license selection and committed license text |

## Freeze criteria

The release-candidate tag requires a clean release audit, requirements audit, full local test run, browser smoke check, secret scan, deterministic Hosting bundle, and a commit containing the generated status reports. GitHub push and release require renewed GitHub CLI authorization.

Production version 1 additionally requires every blocker above to be closed. A tag must never convert an unresolved blocker into an accepted limitation by wording alone.
