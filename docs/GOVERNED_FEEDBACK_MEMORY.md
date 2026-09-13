# Governed feedback memory

Date: 2026-09-13.

Feedback now has a runtime path: existing feedback objects become version-pinned decision proposals, eligible reviewed decisions become scoped execution context, and workers reject a context whose approved decisions changed after admission. The local preparation command does not grant human approval or promote policy.

The proposal lives in validated decision metadata, with a content hash and feedback-version references, rather than a second conversation database. Existing object review and audit remain authoritative. Generic object metadata is not automatically trusted: the retrieval layer validates its typed proposal and fingerprint, current source versions, lifecycle and review state.

Creative overrides have a narrow typed allowlist. They cannot grant publication rights, change prices or budgets, enable provider calls, weaken media-rights requirements or transform a human hypothesis into a verified assertion. Ontology changes and factual-correction proposals require their own migration/evidence paths and never auto-promote through creative memory.

Runtime context keeps at most twelve scoped reviewed decisions and 16 KiB of memory. Conflicting approved settings fail closed. Unreviewed proposals are counted, not silently applied. Task execution rechecks approved advice and rule versions before using them. This is deterministic decision retrieval and guarded context assembly, not a claim of autonomous reasoning or a connected model provider.

The saved creative profile revision records the earlier 60-120 second preference, which is superseded by the current 30-90 second 9:16 canonical contract. Vivid authorized imagery, kinetic text, background music and no mechanical narration remain current. Renderer enforcement remains a separate required integration.

The impact endpoint follows object parents and explicit input-version maps to identify downstream objects requiring revalidation. It reports derived artifacts without lineage separately. It does not falsely claim every derived file is tracked, that approvals have already been withdrawn, or that affected content has already been regenerated.

Commands and API:

```sh
.venv/bin/python scripts/prepare_learning.py
```

- `GET /v1/intelligence/learning`: proposal status and evaluation intent, without raw conversation text.
- `GET /v1/intelligence/impact/{object_id}`: bounded downstream impact queue.
- Existing object-review UI: human review of the exact decision record.

The source-policy adviser has a separately disclosed field-mapping defect: its implementation does not use the existing policy/review contract consistently. It is not treated as a proven worker. The completed catalogue audit is unaffected. This issue remains explicitly unresolved pending the required correction decision; no false source clearance or paid collection is enabled.
