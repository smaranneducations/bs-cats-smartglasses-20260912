# Bounded execution foundation

Implementation checkpoint: 2026-09-13. Newly authored; not executed or tested in this checkpoint.

## What is implemented in source

The existing API has read-only runtime status, task list, and task-detail routes. A local CLI submits typed tasks and runs one bounded deterministic worker. Tasks pin input object versions, profile revision, charter version, objective, acceptance criteria, context hash, and an idempotency key. Task state, audit events, leases, and the financial baseline use `runtime_` tables in the same local SQLite file as object events.

The initial profiles are catalogue coverage, source-policy queue preparation, and content-workflow readiness. They use explicit domain tools, not arbitrary SQL, shell commands, internet access, or provider APIs. A separate child process bounds execution time. The ledger admits one active worker, recovers expired leases, rejects stale completions, and caps retries. Pause prevents new admission and requests termination of running work at the next polling boundary.

Results are review proposals. They cannot approve sources, change facts, modify permissions, publish media, or promote their own policies. Recorded source links are not treated as verified evidence. The workflow planner retrieves the saved creative direction, including realistic image-led visuals and background music; this does not yet make the renderer consume that direction.

## Cost limits and actual coverage

The ledger seeds the single $80 owner-reported subscription payment using a stable identifier. It records the $500 cumulative ceiling, $450 paid-work stop line, and initial $2/job and $5/day limits. These limit fields are not evidence of a connected paid admission system. All current profiles have zero external variable API cost and paid execution is rejected; no provider adapter or billing reconciler is installed. Actual local electricity, subscriptions, existing cloud resources, and other outstanding charges are not claimed to be zero. Spendable headroom remains unknown while accounting is unreconciled.

No API tokens, raw conversations, or `.env` contents enter the runner. A best-effort secret-pattern rejection adds defense in depth but is not a complete secret scanner or a guarantee that arbitrary text is safe. Keep inputs limited to relevant non-secret task context.

## Operator commands

```sh
.venv/bin/python scripts/runtime.py status
.venv/bin/python scripts/runtime.py submit .local/tasks/example.json
.venv/bin/python scripts/runtime.py run-one
.venv/bin/python scripts/runtime.py list
.venv/bin/python scripts/runtime.py show TASK_ID
.venv/bin/python scripts/runtime.py pause
.venv/bin/python scripts/runtime.py resume
```

The task input JSON uses `profile_id`, `objective`, `inputs` containing exact `object_id` and `version`, `acceptance_criteria`, and `idempotency_key`. A workflow-planner task also supplies `workflow_family`. Optional risk is `low` or `medium`. Acceptance criteria are recorded for later evaluation, not automatically proven by task completion.

## Still required for v1

- Execution checks, error-path tests, and a real task run. No new checks were run for this authored batch.
- A transactional Firestore adapter before any Cloud Run deployment; local SQLite is not durable multi-instance cloud coordination.
- Explicitly evaluated model-based workers and priced provider adapters under reconciled financial admission.
- Runtime feedback proposals, guarded policy promotion, and correction propagation to derived outputs.
- The image/music renderer, exact-artifact human review, publisher, and analytics integrations.
- Authenticated UI controls for permitted task creation and pause, preserving human versus agent permissions.

The earlier standalone `services/agent-runtime/main.py` remains a placeholder. The chosen initial topology is the combined API and bounded runtime, not one deployed service per agent role. No cloud worker has been deployed by this checkpoint.
