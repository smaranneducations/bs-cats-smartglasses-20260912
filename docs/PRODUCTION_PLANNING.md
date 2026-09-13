# Local production planning: additive implementation handoff

Date: 2026-09-13.

## Scope of this slice

The source-linked content briefs now have an additive scene-planning layer.
The existing one-off MP4 renderer is unchanged. A separate shared-scene
renderer now produces private local MP4 drafts and source-review packets.
This is not a publishing integration or completed exact-artifact approval
workflow inside the app.

- Scene primitives are reused across product, feature, comparison, category,
  use-case, value, compatibility, question, myth and market stories.
- Change and commercial stories still require their separate evidence gates.
- The animated browser preview is silent, runs locally and uses original
  abstract CSS artwork, not purported product photographs.
- Scene duration totals must remain between 30 and 90 seconds. Comparison
  scenes match recorded fields; the planner does not invent a winner.
- Plans retain the brief revision and claim references. Changing an input
  makes the derived plan stale; rebuild it before approval.
- Very long brief titles are bounded while the full title is retained in
  metadata.

The current preview is a storyboard for editorial and layout review. It is
not an MP4, a product image licence, hands-on evidence or publishing consent.
Factual and layout approval remain outstanding.

## Source refresh planning

Sources and rights now shows due dates, permission expiry and blockers.
Preparing the queue captures versioned planning objects without making
network requests. Planning jobs stay outside the human factual-review inbox.

The collector remains disconnected and every saved job explicitly has
execution disabled. Source approval, automation permission, commercial
reuse, a supported access method, permission documentation and a future
permission-review expiry are separate prerequisites. Media reuse has its
own gate and is not granted by permission to retrieve data.

The policy form creates a reviewable proposal. It never grants permission,
marks a source freshly observed or activates a collector.

## Optional local record preparation

The following business operation creates three private reference previews
from the existing XREAL One Pro, XREAL One and XREAL Air 2 Pro records:

```sh
.venv/bin/python scripts/prepare_workspace_stories.py
```

It prepares a landscape comparison, a portrait product story and a landscape
feature story, together with blocked source-refresh plans. Existing objects
with the same deterministic identity are retained rather than overwritten.
It does not fetch sources, load credentials, call paid generation APIs,
approve facts, export videos or publish content.

Open the Content studio to view or compose previews. Review source-policy
proposals in Sources & rights, and inspect version history on each object.

## Validation and limits

On 2026-09-13 the human approved validation. All 62 tests passed, including
13 new planning/export tests. The comparison browser preview reached 90/90
seconds; scene navigation, source blockers, policy-form opening and exclusion
of routine jobs from the review inbox were exercised without granting rights.

The phone-width comparison page fit a 390-pixel viewport. An intermediate
795-pixel window had a 917-pixel document width, so responsive QA is not
complete. This known UI defect remains unresolved. One test fixture also
emits a non-failing enum-serialization warning.

Three private MP4 exports were produced by scripts/render_storyboard_video.py.
Media probes confirmed 90 seconds, H.264, 24 fps and 2,160 frames each.
Comparison and portrait poster layouts were inspected. Full frame-by-frame
review and production integration checks have not been completed.

The preview uses a small set of existing manufacturer-sourced records, not
a comprehensive or freshly collected catalogue. Permission decisions,
external access and paid-work admission remain unresolved. Existing cloud
costs remain unknown; no new paid API execution is introduced here.

## Next bounded slice

Register local draft exports as inspectable video artifacts and connect their
hashes and source revisions to exact-artifact review in the app. Fix the
intermediate-width layout issue before marking responsive QA complete.
Do not arm a source collector before its source-specific rights and access
are established. Keep final artifact approval distinct from record review.

The detailed private checkpoint and artifact locations are recorded in
.local/governance/VALIDATION_EXPORT_HANDOFF_2026-09-13.md.
