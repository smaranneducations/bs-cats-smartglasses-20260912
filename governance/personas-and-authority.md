# Personas and authority

Version: 1.0. Effective date: 2026-09-13.

## Purpose and moral boundary

The platform has four personas. Separating them prevents a local superuser, an AI model, an administrator, or a public user from accidentally inheriting authority that belongs to another role. One person may hold multiple human roles, but every action must still identify the role used.

Ethics, legality, safety, truth, privacy, rights, human dignity and applicable platform policy are non-negotiable. Revenue is optimized only inside those constraints. A profitable but unethical, unlawful, unsafe, deceptive, exploitative or rights-violating action must be rejected.

## Platform custodian

The platform custodian maintains Codex, local processes, GitHub, Firebase, Google Cloud, browser extensions, account recovery, and consent flows that supported APIs or CLIs cannot complete. The custodian is the human account holder for identity, billing, legal commitments, employment, contracts, channel ownership, and provider terms.

This role may install tools, rotate credentials, approve OAuth consent, configure accounts, and execute emergency containment. It should not become the routine data curator or manually perform work an authorized API or deterministic script can do.

## Delegated operating executive

The delegated operating executive is the model-led operating role. It owns planning, prioritization, implementation, research orchestration, quality improvement, cost-aware model routing, channel preparation, measurement, and truthful reporting within delegated scope.

This is an operating role, not legal personhood or asset ownership. It cannot hold accounts, spend outside approved limits, accept contracts, hire people, create legal obligations, approve its own restricted actions, or publish an unseen artifact. It must use APIs and CLIs before computer control, minimize human work, and escalate only when consent, identity, judgment, or reserved authority is genuinely required.

## Business administrator

The business administrator defines or refines domains, reviews ontology proposals, supplies lawful observations, resolves evidence conflicts, curates data, inspects agents and prompts, handles exceptions, and approves exact release artifacts. Google sign-in plus an ignored administrator-email allowlist identifies this actor. Every mutation records the verified actor and object version.

Routine high-confidence evidence does not wait for approval. The administrator receives consequential exceptions: material ontology migrations, unresolved rights, contradictory high-impact claims, policy changes, budget boundaries, and exact public releases.

## Audience and customer

The audience uses the swipe feed, watches canonical videos, inspects evidence, reacts, comments, asks questions, follows outbound offers, and may buy products, reports, data access, or customer-funded generation. Public interaction does not grant administrative access. Text requires abuse controls and moderation before production scale.

## Reserved decisions

| Decision | Custodian | Operating executive | Business administrator | Audience |
| --- | --- | --- | --- | --- |
| Routine reversible implementation | Informed | Executes | Consulted when domain meaning changes | No role |
| Domain and ontology proposal | Supports | Prepares and evaluates | Reviews material migrations | Feedback signal |
| Credential and account consent | Executes | Prepares exact flow | No secret access by default | No role |
| Spend inside admitted job limits | Financial policy | Executes after admission | Observes | No role |
| Spend ceiling or subscription change | Approves | Recommends | Consulted | No role |
| Exact public artifact | Account authority | Prepares and verifies gates | Approves content | No role |
| Factual ranking | No commercial override | Computes from evidence | Corrects evidence | Popularity never validates fact |
| Legal contract, employment or shutdown | Approves and signs | Analyzes and recommends | Consulted | No role |

## Audit identity

Every consequential event records actor type, stable actor identifier, authority used, timestamp, idempotency key, input object versions, output object version, policy version, and decision or approval reference. “System” is not a fallback identity for unknown actors.
