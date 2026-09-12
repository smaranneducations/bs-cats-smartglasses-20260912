# GitHub Pipeline Guide

The CI workflow is intentionally minimal for the first slice.

## Current CI job

- checks for required scaffold files
- compiles contract model (`packages/contracts/object.py`)

## Later expansion

- Cloud Build or GitHub Actions deploy stages for:
  - `services/api` -> Cloud Run
  - `services/agent-runtime` -> Cloud Run
  - `services/render-worker` -> Cloud Run
  - `services/publisher-worker` -> Cloud Run
  - Firebase Hosting deploy for `apps/web`
- Secret injection from Secret Manager / GitHub Actions OIDC

## Branch discipline

1. `main` receives only reviewed code
2. small, focused PRs for each service/stage
3. merge only after secrets and pipeline checks are aligned
