# Service topology

Version 1 uses the unified API as the only deployable application service. The generic task runtime, render pipeline, and publishing pipeline currently run as governed capabilities in the local application and scripts.

| Service | State | Decision |
| --- | --- | --- |
| `api` | Local implementation; deployed health endpoint reports Firestore on 2026-09-13 | One application service; authenticated workflow acceptance remains separate |
| `agent-runtime` | Inactive shell | Do not deploy until durable queue and workload identity exist |
| `render-worker` | Inactive shell | Do not deploy until resource isolation or measured load justifies it |
| `publisher-worker` | Inactive shell | Do not deploy until exact approval and credential isolation are proven |

Keeping inactive shells does not make them production services. They exist only to preserve the intended isolation boundaries and must not be included in a release deployment.

Default `docker compose up` starts only the API and preserves its existing named data volume. The three shells are opt-in under the `scaffolds` profile and receive no `.env` file. Their health responses do not establish working agents, rendering, or publication. They are retained for compatibility with existing CI and references, not as a commitment to three additional services.

Current work and acceptance criteria: [execution handoff](../docs/CURRENT_EXECUTION.md). Historical deployment-gated descriptions are not current Hosting or Cloud Run deployment evidence.
