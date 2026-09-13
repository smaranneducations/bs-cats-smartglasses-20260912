> Current operating state and implementation queue: [CURRENT_EXECUTION.md](CURRENT_EXECUTION.md). Keep one deployable API; inactive service shells are opt-in. Preserve stable paths and data rather than performing cosmetic repository moves.

# Project structure and ownership

## Dependency direction

Governance and contracts define boundaries. Domain configuration depends on those boundaries. Knowledge, runtime, agents, media, publishing, analytics, applications, and services consume them. Provider adapters sit at the edge. Browser code and agents do not bypass contracts to write databases directly.

| Path | Responsibility | Production status |
| --- | --- | --- |
| `AGENTS.md` | Master operating instructions | Active |
| `governance/` | Version-controlled authority and personas | Active |
| `config/` | Non-secret policy, domain and workflow configuration | Active; individual integrations vary |
| `packages/contracts/` | Typed object and workflow schemas | Active |
| `packages/domain_engine/` | Domain portability and schema interpretation | Active local |
| `packages/knowledge/` | Object store, semantic layer and warehouse adapters | Local active; cloud reads bounded; cutover incomplete |
| `packages/governance/` | Identity, policy and review decisions | Active local |
| `packages/runtime/` | Tasks, runner, tools, cost ledger and local API client | Active local |
| `packages/agents/` | Task-scoped profiles and implementations | Active local with provider-specific gaps |
| `packages/intelligence/` | Research, learning, commerce and trend workflows | Mixed implemented and gated |
| `packages/media/` | Catalog, planning and rendering | Active local; rights and cloud rendering gated |
| `packages/publishing/` | Immutable packages and channel adapters | Implemented; no public publication receipt |
| `packages/analytics/` | Owned-event metric projection | Active local; provider collectors planned |
| `packages/mcp-tools/` | MCP boundary specification | Not an active server |
| `apps/operator/` | Authenticated business administration | Active local; hosted authentication unproven |
| `apps/public/` | Audience swipe and canonical-video experience | Active private preview |
| `apps/web/` | Intelligence and review surfaces | Active local |
| `services/api/` | Unified application and local static server | Active local; cloud persistence gated |
| `services/agent-runtime/` | Future isolated worker shell | Inactive placeholder; not deployed |
| `services/render-worker/` | Future isolated renderer shell | Inactive placeholder; not deployed |
| `services/publisher-worker/` | Future isolated publisher shell | Inactive placeholder; not deployed |
| `sql/bigquery/` | Warehouse schema and constraints | Deployed schema; zero project-loaded rows |
| `infra/` | Infrastructure definitions | Bootstrap only; not sole deployment authority |
| `scripts/` | Deterministic operations and audits | Active by individual script status |
| `tests/` | Focused contract and behavior checks | Active; results must be dated |
| `.github/` | Intake, ownership, review and CI | Added for version 1 freeze |

## Scaling rule

One Cloud Run API with scale-to-zero is the preferred first production shape. Split a worker only when at least one condition is measured: incompatible dependency isolation, materially different permissions, timeout or resource profile, independent scaling pressure, or publication credential isolation. “One agent per service” is not a valid reason.

## Documentation rule

Architecture and policy documents state target behavior. Release-readiness and execution checkpoints state observed behavior. A document, schema, resource, test double, or nonempty configuration field is never presented as proof that a production integration works.
