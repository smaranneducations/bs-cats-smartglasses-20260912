# BS CATS Intelligence Platform

Version 1 release candidate for a governed, reusable system that turns a lawful domain dataset into useful knowledge, short-form media, audience learning, and testable revenue opportunities.

Smart glasses are the first working domain. The engine is domain-portable: domain definitions, ontology concepts, evidence rules, agent profiles, workflows, and channel adapters are configuration and governed objects rather than hard-coded business logic.

## Release truth

The repository contains a working local operator application, public swipe experience, governed object store, semantic comparison layer, evidence and feedback workflows, bounded agent runtime, image-led video renderer, distribution-package adapters, analytics contracts, Firebase rules, BigQuery schemas, and cloud deployment packaging.

It is not yet a production deployment. As of 2026-09-13, the Firebase project and its Firestore, Storage, Hosting site, and BigQuery foundation exist, but no Cloud Run application service is deployed, the warehouse contains no project-loaded rows, provider charges are not reconciled, previously disclosed credentials require rotation, and no exact media package has passed all public-release gates. See [release readiness](docs/V1_RELEASE_READINESS.md).

## Four personas

| Persona | Purpose | Authority boundary |
| --- | --- | --- |
| Platform custodian | Maintains the workstation, Codex, repository, cloud accounts, and browser-only consent flows | Human account holder; controls identity, legal, billing, and irreversible account actions |
| Delegated operating executive | Plans and executes permitted business and engineering work using the least costly capable tools | May not own accounts, accept liabilities, raise budgets, publish unapproved artifacts, or bypass consent |
| Business administrator | Curates ontology and data, resolves exceptions, reviews material changes, and approves exact release artifacts | Authenticated, allowlisted, attributable human role |
| Audience and customer | Discovers, swipes, watches, reacts, comments, follows evidence, and may buy disclosed offers | Public role with no administrative access |

The complete role model is in [governance/personas-and-authority.md](governance/personas-and-authority.md).

## System map

The platform follows this loop:

`domain definition -> ontology -> lawful research -> governed assertions -> analysis -> content plan -> media catalog -> render -> exact approval -> channel distribution -> owned metrics -> feedback -> evaluated improvement`

The ontology is the semantic contract, not merely a glossary. The harness binds every task to exact object versions, evidence, actor, permissions, cost limits, idempotency, acceptance criteria, and release gates. Read [the v1 system specification](docs/V1_SYSTEM_SPECIFICATION.md) and [the ontology architecture](docs/ONTOLOGY_ARCHITECTURE.md).

## Local use

```bash
python3 -m venv .venv
.venv/bin/pip install -r services/api/requirements.txt
.venv/bin/uvicorn services.api.src.main:app --host 127.0.0.1 --port 8766
```

Open:

- Operator: `http://127.0.0.1:8766/operator`
- Audience: `http://127.0.0.1:8766/discover?preview=1`
- Intelligence workspace: `http://127.0.0.1:8766/intelligence`
- Health: `http://127.0.0.1:8766/health`

Local secrets belong in `.env` or ignored local configuration. Never paste credentials into issues, pull requests, logs, prompts, or tracked files. See [SECURITY.md](SECURITY.md) and [docs/ENV_SETUP.md](docs/ENV_SETUP.md).

## Change control

After this snapshot, implementation requests enter through GitHub issues and land through pull requests. Discussion may happen elsewhere, but it is not an executable change request until the decision, evidence, acceptance criteria, cost boundary, and authority are recorded in GitHub. See [the GitHub operating process](docs/GITHUB_CHANGE_CONTROL.md).

## Repository guide

- `apps/`: operator, audience, and intelligence browser surfaces
- `packages/`: reusable contracts, ontology, runtime, agents, media, publishing, cloud, and analytics code
- `services/`: deployable API plus clearly labeled inactive worker shells
- `config/`: non-secret machine-readable business and runtime policy
- `governance/`: version-controlled operating directives and authority boundaries
- `docs/`: architecture, operations, evidence, release, and decision documentation
- `sql/`: BigQuery schemas and bounded warehouse definitions
- `scripts/`: deterministic operations, audits, build, and maintenance commands
- `tests/`: contract and behavior tests
- `.github/`: issue intake, pull-request policy, ownership, and CI

See [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) for ownership and dependency rules.

## Release commands

```bash
.venv/bin/python scripts/audit_requirements.py
.venv/bin/python scripts/release_readiness.py
.venv/bin/python scripts/build_firebase_hosting.py
```

The release audit reports readiness; it does not grant publication approval, reconcile billing, rotate secrets, or prove a cloud deployment.
