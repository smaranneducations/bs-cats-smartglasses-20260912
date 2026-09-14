# Deployment and validation runbook

Updated 2026-09-14. Hosting and the Firestore-backed API are live; consult the [current acceptance record](acceptance/2026-09-14-hosted-workflows.md) rather than inferring readiness from this procedure.

## Separate technical repair from business release

Bounded technical repairs follow GitHub change control, tests and deployment evidence under the [technical deployment policy](TECHNICAL_DEPLOYMENT_POLICY.md). Unrelated revenue/media gates need not block an authorized login or database-index repair. This does not authorize new sensitive access, increased budgets, credential disclosure or publication of unseen content.

Full business release still needs rights/factual/exact-artifact approval, provider eligibility, durable workflows, verified recovery and current cost admission. A healthy API does not substitute for these controls.

## Prepare the change

- Use the intended GitHub repository and a scoped PR; preserve unrelated work and record the problem, root cause and fix steps.
- Keep tokens, local data and unapproved media outside Git, public Hosting and container contexts. Use workload identity and existing least-privilege access.
- Identify the last accepted immutable image/revision and Hosting release before deployment; record compatibility implications for schema changes.
- Run the tests and credential scan appropriate to the change. A private maintenance change stays in its authorized private review path until properly released.

```bash
python scripts/release_readiness.py
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/*.cjs
python scripts/secret_scan.py --mode tracked
python scripts/build_firebase_hosting.py
```

The repository checker is not a production test. Use the configured interpreter and established deployment tooling; do not install a new stack or start a paid build merely because an example command exists here.

## Deploy the bounded artifact

Deploy one existing Cloud Run API with minimum instances zero, maximum two, the existing attached service identity and explicit runtime configuration. Keep administrator mutations authenticated. Start a candidate with zero traffic, check its health and affected workflows, then promote only after its actual failure is resolved and acceptance passes. Preserve the previous revision for rollback and remove temporary candidate routes afterward.

Hosting uses the deterministic `dist/firebase` bundle. Deploy only the services changed by the PR; do not redeploy rules or broaden storage permissions as a side effect of a front-end repair.

```bash
firebase deploy --only hosting --project bs-cats-smartglasses-20260912 --non-interactive
```

For an approved index-only change:

```bash
firebase deploy --only firestore:indexes --project bs-cats-smartglasses-20260912 --non-interactive
```

Wait for required indexes to report READY before exercising dependent queries. `governed_object_versions` history filters `object_id` and sorts `version`; its declared composite index is required by the real store even when mocked tests pass.

Do not migrate existing data just to deploy code. Any separate migration must preview its bounded allowlist and preserve existing history, identity and versions; execution requires its own applicable authorization.

## Validate the deployed result

```bash
python scripts/check_hosted_app.py --output .local/acceptance/hosted-smoke.json
```

This makes no mutations and prints no response bodies, credentials or provider exception messages. It checks public/admin HTTP boundaries and directly linked CSS/JavaScript, including the old unstyled-page failure mode. External dependencies and authenticated workflows require their own browser tests.

Exercise fresh Google sign-in, data retrieval, an attributable test-record mutation and reload, comparison, private media and publication gates as applicable. Use only governed test records; do not approve facts, publish drafts or delete valuable data just to make an acceptance test green.

Record the exact source, image, revision, Hosting version, database-index state, test results, costs/unknowns and remaining gates in the appropriate public or private change record. Exclude sensitive diagnostics and credentials from public documentation.

## Recovery

Cloud Run recovery routes traffic to the last accepted compatible immutable revision. Hosting recovery uses its recorded release history. Keep the required history index when rolling application code back; schema/ontology changes need explicit compatibility handling.

Code rollback does not restore deleted or corrupt data. Backup availability and a tested restore are independent admission gates, not implied by Git tags or container revisions.
