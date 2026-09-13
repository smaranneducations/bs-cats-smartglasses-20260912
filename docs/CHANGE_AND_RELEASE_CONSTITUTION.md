# Change and release constitution

Version 1.0.0. Effective after `v1.0.0-rc.1`.

## One system of record

GitHub is the system of record for every change to code, configuration, ontology, agent instructions, workflows, infrastructure, schemas, editorial policy and production operations. Chat is used to discuss and agree an outcome. It is not an alternative change channel.

The normal path is:

1. Record an issue or change request with outcome and acceptance criteria.
2. Implement on a `codex/` branch.
3. Open a pull request linked to the request.
4. Run automated safety, contract and credential checks.
5. Record material decisions, migration and rollback.
6. Merge into protected `main` only after required checks pass.
7. Create an immutable snapshot.
8. Promote the same commit through environments when deployment is required.

Ask or Plan mode supports discussion and agreement. Agent mode supports implementation. Neither mode can bypass this path.

## Snapshot policy

Daily snapshots run once each day and after changes to `main`. GitHub retains these build artifacts for five days, providing a short rollback window without accumulating indefinite storage.

On the first day of every month, GitHub creates an immutable monthly snapshot release from `main`. Monthly snapshots are retained indefinitely and are explicitly labeled as snapshots, not evidence of production deployment.

## Promotion policy

`Preprod` packages and validates a selected commit. `Uat` records human acceptance of that exact commit. `Production` deploys the same commit and is the only live environment. Promotion never rebuilds from changed source.

Every production version follows semantic versioning and records release notes, commit digest, test evidence, approvals, deployment receipt, migration status and rollback target. Content publication remains a separate exact-artifact approval even when application deployment is approved.

## Production admission

The GitHub production workflow must fail before cloud authentication or deployment unless `docs/V1_RELEASE_READINESS_REPORT.json` reports `production_ready: true`. Readiness requires scoped credentials, reconciled costs, durable persistence, working cloud infrastructure, approved rights-cleared media, unambiguous publishing receipts, returned metrics and the applicable repository-license decision.

## Emergency changes

Direct production or console changes are break-glass actions, not a parallel workflow. They require a linked issue, named human authority, reason, evidence, exact commands or settings changed, impact, rollback and immediate reconciliation through a pull request before ordinary work resumes. Ethical, legal, security, publication and spending constraints remain mandatory.
