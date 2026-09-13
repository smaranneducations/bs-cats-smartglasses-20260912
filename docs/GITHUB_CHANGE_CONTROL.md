# GitHub change control

Status: mandatory after the version 1 snapshot.

## Operating rule

GitHub is the authoritative implementation intake, decision record, review surface, and release history. Ask-mode discussions can explore strategy or clarify an issue. They do not directly modify code or production state. A requested implementation begins when a GitHub issue exists with sufficient authority and acceptance criteria.

## Workflow

1. Create a change request or bug issue without credentials or private source data.
2. Triage scope, authority, affected requirements, evidence, risk, estimated cost, and whether human consent is required.
3. Record a bounded implementation decision and assign one branch named `codex/<issue>-<topic>`.
4. Update code, tests, documentation, requirements traceability, migrations, and rollback instructions together.
5. Open a pull request that links the issue and provides actual verification evidence.
6. Require CI and applicable human review. Exact content approval, financial authorization, and account consent remain separate even when code review passes.
7. Merge without rewriting history. Tag releases only from the default branch after the release-readiness report matches the intended release claim.
8. Record deployment and provider receipts separately from the merge. A merged deployment file is not proof of deployment.

## Required issue content

Every change request states the problem or opportunity, desired outcome, affected persona, evidence, acceptance criteria, cost ceiling, data and rights impact, security impact, migration or compatibility needs, rollback, and reserved human decisions.

## Repository protections

The target GitHub configuration requires pull requests for the default branch, at least one approving review for consequential changes, passing CI, no force pushes, no branch deletion, and secret scanning where the account plan supports it. CODEOWNERS provides routing, not approval of facts, spending, publication, or legal terms.

## Private information

Never put API keys, OAuth tokens, passwords, email contents, customer data, private `.local` objects, hidden reasoning, or unlicensed media in GitHub. Issues should use object identifiers, sanitized evidence summaries, and links to approved private systems.

## Emergency path

A credential leak or active security exploit may be contained immediately by disabling access or pausing deployment. The operator then opens a security issue or private advisory with the exact scope, evidence, actions, residual risk, and follow-up tests. Emergency handling does not authorize unrelated changes.

## Technical maintenance clarification

`docs/TECHNICAL_DEPLOYMENT_POLICY.md` separates approved infrastructure repair from editorial publication and commercial readiness. It also defines the private advisory candidate/check/receipt path where GitHub deliberately does not provide normal temporary-fork CI or individual-PR merging. Routine maintenance authority is not permission to weaken access controls or omit GitHub history.
