# Service topology

Version 1 uses the unified API as the only deployable application service. The generic task runtime, render pipeline, and publishing pipeline currently run as governed capabilities in the local application and scripts.

| Service | State | Decision |
| --- | --- | --- |
| `api` | Active locally; deployment-gated | First Cloud Run candidate after durable persistence |
| `agent-runtime` | Inactive shell | Do not deploy until durable queue and workload identity exist |
| `render-worker` | Inactive shell | Do not deploy until resource isolation or measured load justifies it |
| `publisher-worker` | Inactive shell | Do not deploy until exact approval and credential isolation are proven |

Keeping inactive shells does not make them production services. They exist only to preserve the intended isolation boundaries and must not be included in a release deployment.
