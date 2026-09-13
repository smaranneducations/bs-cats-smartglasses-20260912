# Deployment runbook

Status: prepared but blocked for production activation.

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

The container build requires repository-root context because the service consumes shared packages, browser applications, assets, configuration, and architecture documentation.

## Intended deployment

Deploy one Cloud Run API in `us-central1` with minimum instances zero, a bounded maximum instance count, no unauthenticated administrator mutations, workload identity, explicit environment configuration, and no publisher credentials. Record the image digest, revision, service account, IAM policy, URL, min/max instances, and health response.

Build the Firebase Hosting bundle with `scripts/build_firebase_hosting.py`. Deploy Hosting, Firestore rules and Storage rules only after the API service name and region match `firebase.json`. Record the Firebase release identifier and perform browser acceptance for operator sign-in, public feed, evidence view, feedback, and exact release review.

## Rollback

Cloud Run rolls back by routing traffic to the last known-good immutable revision. Firebase Hosting rolls back through its release history. Schema and ontology changes use their explicit compatibility plan; never restore an old application over incompatible data without migration evidence.

## Current decision

Do not execute production deployment from this snapshot. The release-readiness report documents unresolved persistence, credential, cost, media-rights, and approval gates. Completing build files does not satisfy those gates.
