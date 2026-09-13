# Skills tools MCP and API registry

## Purpose

Capabilities are organized by authority and reuse, not by creating one service for every agent. Deterministic tools perform parsing, validation, persistence, rendering, metrics, and quota arithmetic. Agents perform bounded judgment through those tools. APIs expose application boundaries. MCP is a future adapter over the same governed tools.

| Capability type | Location | State |
| --- | --- | --- |
| Agent profiles | `config/agent-roster.json` and `packages/agents/` | Active local |
| Domain tools | `packages/runtime/tools.py` and `packages/knowledge/semantic.py` | Active local |
| Object and workflow contracts | `packages/contracts/` | Active |
| Application APIs | `services/api/src/` | Active local |
| Provider APIs | `packages/intelligence/` and `packages/publishing/` | Mixed, gated per provider |
| Browser skills | Codex installation and authorized computer-use layer | Used only when supported APIs or CLIs cannot complete account-holder actions |
| MCP adapter | `packages/mcp-tools/` | Specification only; not active |
| Recurring operations | App heartbeats and bounded scripts | Active only where a recorded automation exists |

## Provider boundaries

YouTube research and publishing, LinkedIn publishing, Gmail alert ingestion, Firebase authentication, Firestore, Cloud Storage, BigQuery and Cloud Run each retain separate credentials, scopes, quotas, receipts and failure recovery. No “general agent key” receives all provider authority.

## Capability admission

A new library, skill, MCP server, API, model, or worker requires a GitHub issue documenting the task it solves, license, data boundary, permissions, variable and fixed cost, maintenance burden, alternatives, evaluation, rollback, and why existing tools are insufficient.
