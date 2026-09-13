# Foundation reality check and corrected priorities

Date: 2026-09-13. This is an implementation audit, not a completion claim.

## Findings grounded in the workspace

| Foundation | Current observed state |
| --- | --- |
| Operational data | The local app uses the SQLite object/event store at .local/object-events.sqlite3. Product evidence, briefs and planning records exist locally. |
| BigQuery | No BigQuery integration was found in the searched implementation files. This audit did not inspect cloud datasets; their existence or contents are not established. No verified warehouse ingestion or warehouse-backed app is demonstrated. |
| Agent runtime | services/agent-runtime/main.py describes itself as a scaffold. /agent/run returns status=placeholder and enabled=false. |
| Rendering service | services/render-worker/main.py returns pending. Local rendering scripts produce actual files, but that does not make the worker a connected production service. |
| Publishing service | services/publisher-worker/main.py returns placeholder and enabled=false. Nothing has been published by the current local flow. |
| Semantic foundation | Typed objects, fields, units, evidence/provenance rules and draft composition exist in packages/contracts. A complete warehouse-backed semantic query/tool layer has not been demonstrated. |
| Feedback learning | A governance protocol, feedback/decision objects and local forms exist. Automatic conversation-to-policy retrieval, evaluation, promotion and downstream enforcement are not established. |
| Tests | The last 62 passing tests cover implemented local components. They do not prove BigQuery ingestion, autonomous agents, a completed semantic layer or business results. |

## Human corrections and reusable dispositions

The preferred audience-facing video has realistic colourful imagery, kinetic
text and background music. Rejecting mechanical narration did not reject
background music. The plain silent exports are technical drafts, not an
accepted creative replacement.

The versioned specification is config/creative-direction.json. It explicitly
states that the current renderer does not yet consume or enforce it. The
preferred older reference contains wording and factual claims that require
current review; preserve its style, not every old assertion.

The architectural feedback identifies delivery drift: a presentation demo
cannot stand in for the intelligence platform. Do not describe file stubs,
configuration values, stored feedback or test counts as working services.

A named GitHub conversation-learning project has not been identified by a
repository link or name. No such plugin was found among the available tools.
Do not claim it is installed or install an unrelated tool on that assumption.
Raw conversation logs may contain credentials; retain sanitized decisions
and scoped preferences, not a wholesale transcript in GitHub, BigQuery or a
third-party memory service.

## Corrected delivery sequence

1. Reconcile the blueprint's required data path with the actual implementation
   and existing approved cloud resources. Report missing access, rights or
   cost accounting honestly; do not create duplicate projects.
2. Implement one bounded, traceable data-ingestion and query path into the
   required warehouse, with explicit schemas, evidence lineage, refresh
   state and query limits. Keep credentials outside analytical data.
3. Put the existing domain definitions behind semantic tools used consistently
   by agents and presentation components.
4. Implement a real, bounded agent task executor with role/tool permissions,
   budgets, retries, state transitions and attributable outputs.
5. Demonstrate one sanitized human feedback item becoming a scoped versioned
   preference, a retrieved execution input, an evaluation and an observable
   downstream change. A document alone does not satisfy this step.
6. Reconnect image-led, music-backed video production to that shared governed
   knowledge, then exact-artifact review. Publishing remains separately gated.

This sequence is a corrective priority, not completed work, automatic spending
authority or a promise of audience growth. Continue to favor existing tools,
bounded local work and minimal necessary human involvement. Source/legal
clearance, account-holder consent, actual spend reconciliation and final
publication approval must not be inferred from a broad instruction to proceed.
