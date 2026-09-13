# Safe replication

## Minimal path

1. Clone or download the complete repository from GitHub.
2. Open the checkout in Codex, Cursor or another capable coding agent.
3. Use `README.md` and `AGENTS.md` as the governing entry points.
4. Tell the agent the new domain and ask it to preserve the existing contracts, tests, architecture and change-management process.
5. Create fresh accounts, cloud projects, OAuth applications, administrator allowlists and local credentials.
6. Validate locally, promote the same immutable commit through preprod and UAT, then deploy production only after machine and human gates pass.

## Never copy

- `.env`, `.local`, data exports, user records, logs or runtime artifacts;
- API keys, passwords, tokens, cookies, private keys or service-account files;
- original project IDs, administrator identities or publishing accounts as defaults;
- private security reports, exploit details or internal access paths;
- content or media whose license does not permit the replica's intended use.

## Required replacements

| Boundary | Replica responsibility |
|---|---|
| GitHub | New repository, protected main, private vulnerability reporting and Actions environments |
| Firebase | New project, Hosting site, Authentication configuration and Firestore rules |
| Google Cloud | New billing attachment, workload identity, service account, BigQuery dataset and bounded budgets |
| Administrators | New allowlist populated outside public source control |
| Providers | New OAuth applications and scoped publishing permissions |
| Domain | New source policy, ontology proposal, audience problem and data-fit decision |
| Media | New rights receipts, attribution and owned artifact storage |
| Economics | New cost ledger, ceiling, unit economics and revenue hypotheses |

## Agent acceptance criteria

The agent must distinguish copied architecture from newly verified runtime state. A nonempty configuration value is not proof of access. Created cloud resources are not proof of a working application. A working application is not proof of lawful media, publication approval, demand or revenue.

Before public GitHub changes, run:

```bash
python scripts/secret_scan.py --mode staged
python scripts/repository_publication_guard.py --mode staged
```

Before production, use the repository promotion workflow and preserve the deployment, identity, data, cost and rollback receipts.
