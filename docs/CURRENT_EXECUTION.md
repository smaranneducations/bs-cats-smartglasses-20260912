# Current execution and completion plan

Effective: 2026-09-13. Governing change: [issue #34](https://github.com/smaranneducations/bs-cats-smartglasses-20260912/issues/34).

Latest execution evidence: [agent-run acceptance checkpoint](acceptance/2026-09-13.md), tracked in [issue #36](https://github.com/smaranneducations/bs-cats-smartglasses-20260912/issues/36). Human UAT is not yet ready. The human requires automated checks and real hosted audience/admin journeys to pass before handover; failed, blocked, and untested cases must remain explicit.

This is the current handoff for implementation agents. It supersedes historical next-action and model-switch pauses in older checkpoints, not the ethical constitution, human financial authority, publication approval, or release safeguards. The human has resumed implementation and requests minimal routine involvement.

## Start here

1. Read `AGENTS.md`, this file, and the governing issue or PR. Retrieve only the relevant contracts and source files for the chosen slice.
2. Keep public work based on public `main`; keep private security work isolated. Preserve existing worktrees and uncommitted changes.
3. Complete the highest-priority unblocked outcome below. Attach actual evidence and a rollback path; a document or nonempty configuration field is not a working capability.
4. Update this handoff and the issue at the end of the slice. Do not restart domain selection, build another navigation shell, or add another planning document instead of completing the workflow.

## What is established

| Surface | Evidence and limit |
| --- | --- |
| Firebase Hosting | [Public site](https://bs-cats-smartglasses-20260912.web.app/discover) and [operator](https://bs-cats-smartglasses-20260912.web.app/operator) respond. This is deployment evidence, not full acceptance. |
| Operator presentation | Merged PR #33 was deployed on 2026-09-13. The stylesheet and four scripts return correct MIME types; a browser reload shows the designed page and administrator sign-in prompt. |
| API persistence selection | `/health` returned HTTP 200 with `object_store: firestore`, version `0.4.0`. This does not prove a complete authenticated write/read/restore workflow. |
| Deployment provenance | Public commit `da95e4233ce3340d42bc4148c64dccd8d1163cc3`; provider release and rollback reference are in the [receipt](releases/2026-09-13-hosting-hotfix.json). |
| Local runtime | `packages/runtime/ledger.py` and `runner.py` implement SQLite task admission, bounded leases, recovery, pause, and audit. Registered profiles are catalogue auditor, source-policy adviser, and workflow planner. |
| Cost enforcement scope | That runtime rejects paid profiles and reports no paid adapter. It is not a shared production billing cap and does not establish admission control for other standalone scripts. |
| Ontology and storage | The blueprint specifies semantic knowledge in BigQuery, workflow state in Firestore, artifacts in Cloud Storage, and domain tools between agents and storage. Created tables are not evidence of synchronized, queryable knowledge. |

No end-to-end successful production workflow, settled revenue, complete backup/restore protection, or general autonomous learning claim is made by this checkpoint.

## Review findings and decisions

| Finding | Decision |
| --- | --- |
| Local asset aliases differed from Hosting filenames. HTTP 200 could be an HTML fallback, not the requested script. | Validate entrypoint stylesheet/script references during Hosting packaging; include the shared navigation asset used by the audience page. Require live MIME and rendered-page evidence for a release. |
| Default Compose launched three placeholder services, each receiving the entire `.env`. | Keep one active API; make shells opt-in and remove their unnecessary credential injection. Preserve paths required by existing CI until a separately scoped removal is justified. |
| Historical handoffs contained conflicting domain decisions, deployment states, and stop instructions. | Use this single current queue. Preserve history with explicit archival notices rather than deleting decisions or repeatedly extending obsolete next steps. |
| The runtime has three bounded deterministic profiles, not a fleet of working specialist model agents. | Keep roster definitions separate from executable registrations. Wire one complete task contract before adding another agent role. |
| The readiness script uses fixed blocker labels. | Treat its output as a repository checklist, not live deployment truth. Replace fixed claims with evidence-backed acceptance in the release workstream; do not manually flip production-ready to true. |
| Data preservation must cover more than source-controlled code or a legacy JSONL file. | Protect current SQLite databases, Firestore, BigQuery, and media together. Prove restoration; GitHub snapshots are not data backups. |

## Ordered completion work

| Priority | Outcome | Required implementation and acceptance |
| --- | --- | --- |
| 1 | Administrator can complete one durable workflow | Finish protected identity work through its authorized review path. Prove approved administrator login, rejection of unauthorized users, actor attribution, version conflict handling, and create/edit/reload against Firestore. Do not publish sensitive diagnostic details in public issues. |
| 2 | Valuable data can be recovered | Inventory authoritative stores and media, not secret values. Use consistent SQLite backup/export rather than copying an open database or assuming JSONL is current. Add scoped cloud exports, independent recovery permissions, checksums, retention, and an isolated restore exercise with RPO/RTO and costs recorded. Do not lock retention or delete originals without the applicable authority. |
| 3 | Governed research reaches semantic knowledge | Connect source-policy admission, bounded fetching, evidence, deduplication, field-level unknowns, validation, ontology proposals, and durable publication to the semantic store. Demonstrate idempotent retries and one correction propagating to dependent analysis. Keep dataset catalog metadata distinct from domain concepts. |
| 4 | Automated research is affordable and lawful | Make every adapter use the same durable spend admission and rights policies before network activity. Include reservations, uncertain charges, price freshness, lifetime/day/job limits, caching, and retry accounting. Do not arm paid execution while accounting or admission coverage is unresolved. |
| 5 | Agent work is useful, inspectable, and bounded | Wire research, mapping, validation, and object-custodian tasks through shared contracts and relevant context. Expose profile/prompt/version/tools to the operator; version changes and retain evaluations without allowing agents to expand their own authority. |
| 6 | One excellent story becomes an owned artifact | Evidence -> audience question -> differentiator -> script -> claim coverage -> licensed catalog imagery -> typed creative primitives -> playable 30-90 second master with kinetic text and background music. Store the master independently of social platforms; unknown facts do not block unrelated valid claims. |
| 7 | Approval distributes exactly the same artifact | Review the exact master and channel metadata. Record an immutable approval fingerprint, idempotent YouTube/LinkedIn results and owned-site availability. Produce manual text/link kits for unsupported channels; resolve ambiguous upload results instead of blindly retrying. |
| 8 | Feedback improves quality and contribution | Join comments, performance, corrections, and costs to content and recipe versions. Keep factual learning separate from popularity. Propose bounded improvements and measure accepted-output cost, human minutes, qualified/returning audience, inquiries, and collected contribution. |
| 9 | Release evidence and recovery are repeatable | Drive immutable preprod/UAT/prod snapshot promotion, receipts, rollback, and daily/monthly recovery retention through GitHub. Separate technical acceptance from permission to publish an unseen video or claims of commercial success. |

These are open acceptance outcomes, not an acceptable permanent technical backlog. Fix routine causes in the active slice; an external boundary should not stop independent authorized work.

## Charter carried into each task

- Ethics, legality, safety, security, privacy, credible claims, and lawful media/data use outrank revenue. The agent is a delegated operator, not the legal account holder.
- Budget: $500 cumulative, including the $80 owner-reported subscription. Other charges are not assumed zero. Stop new paid work at $450 exposure; initial variable limits are $2/job and $5/day within reconciled authority.
- Research incomplete products progressively. Unknown, false, not applicable, and unverified are different states. Escalate only decision-critical conflicts or permissions, not every empty cell.
- One domain configuration, one shared runtime, one API, and reusable primitives first. Do not create multi-tenant SaaS, extra deployed workers, a dedicated graph database, or bespoke per-product screens to avoid fixing the core.
- Retrieval-first image catalog, rights and lineage metadata, and illustrative labels. The authorized image-generation ceiling is $0.10/image, subordinate to all other budget gates.
- One 30-90 second master for owned-site and channel reuse, energetic visuals and music by default, no mechanical narration. A later premium service is a hypothesis, not current spending authority.
- Admin ontology, datasets, concepts, definitions, agents, feedback, creative primitives, and publication belong in the same operator navigation. Public audiences see useful media and evidence, not administration controls.
- Ask for human input only when required for consent, missing access, an unresolved consequential trade-off, credible evidence unavailable through permitted means, or an exact final publishing decision. Existing authorization is not requested repeatedly.

## Model handoff

Use a routine implementation model for one bounded, well-specified slice. Reserve stronger reasoning for identity boundaries, data migrations, budget admission, source rights, release safety, and unresolved architecture. This is a routing recommendation, not a claim that a script switches this conversation's model.

Each task handoff contains: outcome; governing issue; exact files/contracts; current evidence; allowed writes and tools; acceptance checks; resource limits; rollback; remaining human-only action if any. Do not pass credentials, the full conversation, or hidden reasoning as context.

## Completed in this change versus still pending

The emergency Hosting asset-path deployment is completed and observed. The packaging guard, shared public navigation asset, cache revalidation policy, default-service cleanup, video configuration correction, and consolidated instructions are source changes for issue #34 and require the normal PR path. They are not included in the earlier deployment receipt.

The larger application remains in completion work. User acceptance testing should begin with the protected operator workflow, not with approval of hundreds of individual records.
