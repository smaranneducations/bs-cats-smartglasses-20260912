# Technical maintenance and commercial release are separate gates

Effective 2026-09-13, following the account holder's direction to repair hosted login and resolve the security/deployment conflict. This clarifies technical maintenance authority; it does not weaken the charter's ethical, legal, privacy, security or spending constraints.

## Technical maintenance

The delegated operator may repair existing, authorized hosting and application services without asking the account holder to approve routine code changes again. Each change needs a GitHub issue or private security advisory, a reviewed pull request, exact source identity, proportionate passing checks, scoped deployment, retained rollback identity, and a truthful deployment/acceptance receipt. Existing access controls and budgets remain binding. No new account, billing arrangement, increased spend limit, public data exposure or destructive migration is implied.

Normal changes merge through the repository's required checks. Private security fixes use GitHub's supported advisory workflow, not an ordinary merge inside a temporary fork. GitHub does not run Actions in those forks: run the equivalent applicable checks locally on the exact private candidate and record the evidence privately. Keep the advisory and diagnostic details private. A reviewed, immutable private candidate may be deployed to repair the affected service before coordinated source disclosure; record its commit and rollback privately, then reconcile the public history through the supported advisory merge. Do not disable branch protections, manufacture CI approvals, or publish secrets to resolve a tooling mismatch.

Deploy only the necessary surface. A Hosting-only repair must not alter Cloud Run identity, Firestore rules, administrator allowlists or data. A backend repair must retain existing identity, region, resource limits and durable data, with an explicit revision rollback. Validate public assets and failure states, reject unauthenticated protected requests, and perform actual Google sign-in plus an attributable administrator workflow before claiming that hosted administration works. A response code or a passing unit test alone is insufficient.

## Commercial and editorial release

An exact video's approval, rights clearance, platform publication receipt, returned analytics and commercial readiness remain independent requirements. They gate publishing and business-readiness claims, not repair of the login page needed to review that video. No future unseen artifact is approved by technical deployment authority. The broad version-one readiness report must remain incomplete while its actual acceptance criteria are unmet.

## Evidence and limitations

Record source SHA, build identity, destination, previous and new release/revision, tests actually run, observed browser outcomes, known gaps and known/unknown costs. A successful GitHub workflow that packages or tags source is not a cloud deployment. Avoid creating duplicate infrastructure simply to obtain staging labels; use reversible snapshots and the existing service's supported preview/revision mechanisms where appropriate.

## Guardrail-preserving source reconciliation

If GitHub's advisory merge explicitly requires bypassing branch protection, do not select that bypass. For a client-side correction whose exact source is already served publicly by the deployed application, reconcile that same code and its non-sensitive regression tests through an ordinary parent-repository PR with all required CI and review controls. Keep the advisory description, diagnostic evidence and any undeployed private server changes private. This narrow path supersedes the advisory-merge preference above where that preference would require weakening protection; it does not authorize disclosure of secrets or unremediated security details.
