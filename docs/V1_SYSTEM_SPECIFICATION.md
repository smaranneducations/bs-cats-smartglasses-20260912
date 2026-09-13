# Version 1 system specification

Status: release candidate specification. Date: 2026-09-13.

## Product conclusion

BS CATS is a reusable evidence-to-value engine for solo operators. A domain package defines concepts, relationships, source policy, comparable entities, useful questions, and commercial constraints. The engine builds governed knowledge, derives analysis, produces short-form media, distributes approved artifacts, measures response, and turns feedback into evaluated improvements.

Smart glasses are the first configured domain, not the product boundary. Version 1 prioritizes one complete, trustworthy workflow over premature multi-tenant SaaS.

## Core purpose and code of conduct

The operating purpose is to build an intelligence that can sustain its operations, improve decision quality, compound its data asset and maximize lawful revenue without entering an unmanaged loss cycle. Ethical conduct, legality, safety, truth, privacy, human dignity, source rights, media rights and applicable platform rules constrain every optimization. Profit never overrides those constraints.

“Alive” means scheduled bounded work, health monitoring, current evidence, expiring data, feedback intake, evaluation, measured economics and explicit pause or shutdown behavior. “Self-improving” means versioned proposals tested against evaluation cases and promoted through appropriate authority. It does not mean silent prompt mutation, permission escalation, self-approval, unlimited retries, deceptive persuasion, uncontrolled spending, or resistance to shutdown.

The financial owner provides finite seed capital and a low-work strategic human partner. The delegated operating executive owns routine preparation and execution, asks focused questions when human judgment can materially improve a decision, and prepares exact consent steps only when tools cannot lawfully complete them.

## Operating objectives

The system optimizes for useful audience decisions, traceable knowledge, low recurring human effort, contribution after costs, and reusable domain intelligence. It does not promise revenue. Views, agent count, generated files, and infrastructure size are diagnostic signals rather than success by themselves.

The first experiment has a cumulative USD 500 exposure ceiling, including the owner-reported USD 80 subscription. New paid work stops at USD 450 pending reconciliation so delayed charges retain a USD 50 reserve. At USD 500, spending stops. The operating executive presents evidence, actual unit economics and options; the financial owner may approve more seed money, but continuation is never assumed.

## Logical architecture

| Layer | Responsibility | Primary objects |
| --- | --- | --- |
| Governance | Mission, ethics, authority, cost, source, rights, approval and release policy | charters, policies, decisions, approvals |
| Domain package | Portable configuration for one subject and buyer problem | domain, markets, entity types, source classes |
| Ontology and semantics | Stable meaning, relationships, units, definitions and constraints | concepts, definitions, relations, shapes |
| Knowledge | Versioned entities, assertions, evidence and provenance | products, variants, sources, assertions, observations |
| Harness | Typed work, permissions, leases, retries, idempotency and gates | tasks, runs, receipts, exceptions |
| Agent capabilities | Bounded judgment roles operating through domain tools | profiles, prompts, evaluations, proposals |
| Analysis | Comparisons, explanations, trends and commercial assessments | analyses, reports, opportunity assessments |
| Creative system | Reusable scripts, scenes, visual primitives, assets and renders | briefs, storyboards, recipes, media assets, videos |
| Release and distribution | Exact approval and platform-specific metadata or posting | packages, approvals, publication receipts |
| Audience and commerce | Owned feed, engagement, offers and qualified intent | feed cards, events, offers, conversions |
| Learning and analytics | Separate factual quality from creative performance | metric snapshots, feedback, evaluation cases, decisions |

## Agent operating model

Agent names describe task-scoped capabilities, not independent employees or a permanent debating fleet. One generic runtime loads the smallest relevant profile and context.

| Capability | Output | Hard boundary |
| --- | --- | --- |
| Domain scout | Data-fit assessment | Cannot switch live domain alone |
| Ontology architect | Additive or migration proposal | Cannot silently rewrite current meaning |
| Researcher | Source and assertion proposals | No arbitrary scraping or invented facts |
| Rights and source reviewer | Permission classification and exceptions | Unknown rights block publication use |
| Data-quality analyst | Validation results and conflict proposals | Popularity does not change truth |
| Analyst | Comparison or explanation | Must preserve unknowns and regions |
| Marketing strategist | Hook, segment and channel hypothesis | No fabricated urgency, identity or demand |
| Storyteller and scriptwriter | One-question short-form script | Maximum 90 seconds |
| Media librarian | Reused asset or generation request | Generate only after lawful retrieval fails and under USD 0.10 |
| Director and editor | Versioned render recipe and artifact | No unbound assets or claims |
| Release manager | Approval packet or blocked reasons | Cannot self-approve public release |
| Distributor | Provider receipt or manual kit | Credentials scoped per adapter |
| Performance analyst | Version-bound metric snapshot | Engagement cannot validate facts |
| Learning curator | Proposed rule, ontology or experiment change | No automatic permission or policy escalation |

## Harness contract

Every task contains task type, charter version, domain, actor, permissions, input versions, evidence set, acceptance criteria, risk, cost reservation, timeout, lease, retry policy, idempotency key, and output schema. Important writes use compare-and-swap versioning and an immutable receipt. An ambiguous external commit is reconciled by the same operation identity instead of blind retry.

Gates remain independent: ethics and legality, source admissibility, data validation, factual review, media rights, render quality, exact artifact approval, spend admission, and provider authorization. Passing one gate never implies another.

## Primary workflow

1. Define one narrow domain and online buyer problem.
2. Research source availability, lawful reuse, catalogue complexity, demand path, and attainable revenue path.
3. Create or update the concept scheme, definitions, constraints, source policies, and compatibility plan.
4. Capture versioned entities, variants, assertions, sources, observations, and evidence.
5. Validate deterministic rules and send only consequential conflicts or migration decisions to the administrator.
6. Produce one bounded analysis answering one audience question.
7. Compose one canonical 9:16 video of 30 to 90 seconds with at most two products and one primary question or attribute.
8. Search the rights-aware media catalog before requesting generation. Bind every visual, music track, font, claim, and primitive version to the recipe.
9. Render a low-cost preview and create an exact review package containing hashes, title, description, tags, disclosures, evidence, rights, and destination plan.
10. After explicit approval of that exact package, retain the canonical artifact in owned storage, stage it in the audience application, publish through eligible YouTube and LinkedIn APIs, and create manual kits for unsupported Instagram, TikTok, and X actions.
11. Collect owned metrics and authorized provider metrics against the exact package and primitive versions.
12. Convert feedback and outcomes into classified, versioned proposals and evaluation cases. Promote only after applicable checks and authority.

## Revenue portfolio

Version 1 treats revenue ideas as hypotheses with evidence gates. Candidate channels are advertising share from eligible owned channels, disclosed affiliate or referral relationships, sponsorships that do not control facts, paid reports and decision tools, governed dataset or API access, customer-funded video generation, platform licensing, education or supervised training, and possible asset or channel sale.

Customer-funded generation targets a provisional 30 percent gross platform margin only after token, rendering, storage, moderation, support, refunds, payment fees, tax, fraud, and quality-retry costs are measured. “Customer pays tokens” does not mean the platform has zero cost.

The owned application retains canonical media so one social platform suspension does not erase the asset. Platform copies and links remain distribution channels, not the sole archive.

## Deployment topology

The intended first production topology is one scale-to-zero Cloud Run API, Firebase Hosting, Firebase Authentication, Firestore for transactional workflow state, Cloud Storage for approved media and evidence artifacts, BigQuery for analytic projections, Cloud Scheduler or app heartbeats for bounded recurring work, and provider-specific publisher adapters. Separate worker services are admitted only after workload or isolation evidence justifies them.

Version 1 does not require Kubernetes, a graph database, one service per agent, or a permanent model council. Those would increase cost and operating burden without proving user value.

## Acceptance boundary

The repository snapshot is ready to freeze when deterministic tests, requirements audit, release audit, secret scan, build packaging, and documentation checks pass. Production activation additionally requires rotated credentials, durable persistence cutover, authenticated cloud administration, reconciled costs, an approved canonical package, one successful owned-app deployment, one supported channel receipt, metric return, rollback evidence, and a repository license decision.
