# Documentation map

Start with [current execution](CURRENT_EXECUTION.md), not an old checkpoint. The [root README](../README.md) describes the product and economics; this index locates implementation evidence and instructions.

Latest [agent-run acceptance report](acceptance/2026-09-13.md): automated checks, Chrome audience/admin journeys, and the remaining human-UAT gates. Test results are tied to their source/deployment, not treated as universal proof of readiness.

## Purpose, authority, and operating rules

| Question | Canonical reference |
| --- | --- |
| What is the mission and what can an agent do? | [Master instructions](../AGENTS.md) |
| Which constraints cannot be traded for revenue? | [Ethical constitution](../governance/ETHICAL_OPERATING_CONSTITUTION.md) |
| Who operates the workstation, business, and application? | [Personas and authority](../governance/personas-and-authority.md), [workstation operations](../governance/CODEX_WORKSTATION_AND_AD_HOC_OPERATIONS.md) |
| What spending authority exists? | [Experiment budget](../config/experiment-budget.json), [scorecard](EXPERIMENT_SCORECARD.md) |
| How do requests become changes? | [GitHub change control](GITHUB_CHANGE_CONTROL.md), [change policy](../config/change-management-policy.json) |

## Implementation and architecture

| Question | Canonical reference |
| --- | --- |
| Where does code belong? | [Project structure](PROJECT_STRUCTURE.md), [service topology](../services/README.md) |
| What is the complete intended system? | [V1 specification](V1_SYSTEM_SPECIFICATION.md), [source blueprint](../Smart_Glasses_Intelligence_Platform_Blueprint.docx) |
| How do concepts, definitions, assertions, and context fit together? | [Ontology architecture](ONTOLOGY_ARCHITECTURE.md), [contextual storytelling policy](../config/contextual-storytelling-policy.json) |
| Which agent/tool capabilities actually exist? | [Capability registry](CAPABILITY_REGISTRY.md), [registered runtime profiles](../config/runtime-profiles.json) |
| What release controls apply? | [Release readiness](V1_RELEASE_READINESS.md), [release policy](../config/release-policy.json) |
| What was actually deployed? | [Hosting receipt](releases/2026-09-13-hosting-hotfix.json), [current execution](CURRENT_EXECUTION.md) |

## Historical material

[Local workspace](LOCAL_WORKSPACE.md), [overnight checkpoint](V1_EXECUTION_CHECKPOINT_2026-09-13.md), and the chronological [execution status](EXECUTION_STATUS.md) preserve earlier decisions and observations. Their old next steps, stop instructions, record counts, and deployment states are not the current queue. Private `.local/governance` documents are supporting history, not prerequisites for understanding a fresh public checkout.

Keep existing paths stable. Do not move or delete referenced documentation merely to make the folder tree look smaller. Consolidate conflicting instructions at their entry points; link detailed historical evidence rather than copying it into every agent prompt.
