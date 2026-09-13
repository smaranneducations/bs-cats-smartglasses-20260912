# Configuration registry

Tracked configuration is non-secret, reviewable policy. Credentials, administrator email allowlists, OAuth tokens, provider receipts, private data and local state remain ignored or move to a production secret manager.

| Area | Authority |
| --- | --- |
| Active domain | `active-domain.json` and `domains/` |
| Architecture and personas | `project-architecture.json` |
| Agents and model routing | `agent-roster.json`, `model-routing.json`, `runtime-profiles.json` |
| Ontology standards | `ontology-standards-profile.json` |
| Revenue and budget | `revenue-portfolio.json`, `experiment-budget.json` |
| Creative and media | `creative-direction.json`, `media-generation-policy.json` |
| Workflows | `workflows/` |
| Release | `release-policy.json`, `v1-delivery-plan.json` |
| Traceability | `requirements-traceability.json` |
| External capabilities | `external-capabilities.json` |

A nonempty field does not prove provider authorization or runtime operation. Configuration cannot approve its own promotion.
