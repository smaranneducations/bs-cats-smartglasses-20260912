# MCP boundary

This directory defines the intended Model Context Protocol boundary for governed domain tools. It is not an active MCP server in version 1.

The production tools already exist as typed Python functions and authenticated HTTP routes. An MCP adapter may expose only those existing capabilities after the cloud API, actor mapping, rate limits, and audit sink are proven. The adapter must not create a second business-logic path or grant storage access.

## Candidate tools

| Tool | Existing authority | Required MCP behavior |
| --- | --- | --- |
| `search_objects` | Object API and local store | Bounded filters, paginated result, actor scope |
| `get_object` | Object API | Exact version and lineage returned |
| `get_concept` | Semantic API | Stable concept identifier and current definition |
| `compare_products` | Semantic API | Same-category and market rules enforced |
| `propose_feedback` | Feedback API | Proposal only; no policy self-promotion |
| `inspect_release` | Release API | Read-only gates and exact hashes |

## Admission gate

An MCP service remains disabled until the cloud API uses durable persistence, authenticated identities map to typed actors, schemas have deterministic limits, all operations enter the same audit journal, prompt content cannot alter authority or budgets, and focused protocol and security tests pass.

MCP is an interface adapter, not an agent, ontology, database, or authorization system.
