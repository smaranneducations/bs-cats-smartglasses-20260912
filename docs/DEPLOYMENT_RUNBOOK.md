# Deployment runbook

Status: Firestore cutover implementation prepared; production activation still requires successful migration, deployment receipts and acceptance checks.

## Preconditions

- GitHub CLI is authenticated to the intended repository account.
- Previously disclosed credentials are rotated and status-only validation passes.
- Current cloud charges and reservations are reconciled against the cumulative experiment ledger.
- Firestore is the application persistence adapter; local filesystem state is not used for hosted mutations.
- Workload identity and least-privilege service accounts exist.
- Administrator allowlist is stored outside the repository and Google sign-in is tested.
- One canonical artifact and metadata package has passed factual, rights, render, exact approval and spend gates.

## Build

```bash
.venv/bin/python scripts/audit_requirements.py
.venv/bin/python scripts/release_readiness.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/secret_scan.py tracked
.venv/bin/python scripts/build_firebase_hosting.py
docker build -f services/api/Dockerfile -t bs-cats-api:VERSION .
```

Preview the allowlisted local history migration without cloud writes:

```bash
.venv/bin/python scripts/migrate_local_store_to_firestore.py
```

The production migration requires the explicit `--execute` flag, authenticated local CLI identity and a bounded operation budget. It rejects credentials, non-allowlisted object types, non-contiguous history and divergence from an existing production version. The application selects Firestore only when `OBJECT_STORE_BACKEND=firestore` and separately requires `FIRESTORE_OPERATIONS_ENABLED=1`.

The container build requires repository-root context because the service consumes shared packages, browser applications, assets, configuration, and architecture documentation.

## Intended deployment

Deploy one Cloud Run API in `us-central1` with minimum instances zero, a bounded maximum instance count, no unauthenticated administrator mutations, workload identity, explicit environment configuration, and no publisher credentials. Record the image digest, revision, service account, IAM policy, URL, min/max instances, and health response.

Build the Firebase Hosting bundle with `scripts/build_firebase_hosting.py`. Deploy Hosting, Firestore rules and Storage rules only after the API service name and region match `firebase.json`. Record the Firebase release identifier and perform browser acceptance for operator sign-in, public feed, evidence view, feedback, and exact release review.

## Rollback

Cloud Run rolls back by routing traffic to the last known-good immutable revision. Firebase Hosting rolls back through its release history. Schema and ontology changes use their explicit compatibility plan; never restore an old application over incompatible data without migration evidence.

## Current decision

Execute only the bounded issue #3 cutover requested by the financial owner: allowlisted application-data migration, one minimum-zero/maximum-two Cloud Run API, Firebase Hosting, authenticated acceptance checks and receipts. This does not authorize content publication, paid promotion, provider uploads or removal of unrelated release blockers.
