# Exact-artifact review packet

The packet combines separate evidence gates for an existing governed video. It
does not grant publication, account, commercial or financial authority. It also
does not substitute for a working publisher or cloud/spending admission.

The authenticated endpoint is
`/v1/media/artifacts/{artifact_id}/release-review`. The existing private video
player displays its results. `scripts/prepare_release_review.py` captures the
result through the authenticated agent API as `release_review_packet`, with exact
input versions and the normal pending human-review state.

## What it checks

- Video, manifest and original soundtrack bytes, within confined render paths and bounded read sizes.
- Exact metadata using sorted compact JSON, and manifest/recipe/output identity.
- The existing renderer admission validator, current input versions and changes detected during inspection.
- Fresh ffprobe results for duration, video/audio codecs and dimensions; a separate final-delivery resolution check.
- Source reference coverage, factual review, applicable source policies and documented media-rights evidence.
- The recorded human review of the artifact, kept separate from technical checks.

The probe has a deadline, only file/pipe protocols, and a minimal environment
without provider credentials. It does not assess whether music is enjoyable or
the visual communication is effective. The thumbnail, target-channel eligibility,
upload implementation, account-holder consent and spending admission are outside
this packet's scope.

Source-policy permission windows are half-open: a policy at its expiry or refresh
boundary is no longer treated as current. This implementation does not modify or
repair the separately disclosed commerce-freshness or source-policy-worker bugs.

## Interpretation and integration boundary

A passing file hash proves identity, not factual truth or legal permission.
Source automation permission, factual reuse and image/music rights are distinct.
A public source page does not provide commercial or media rights by itself.

An approved review on a packet with unresolved prerequisites is not a valid
release. A future publisher must recompute the exact-artifact checks and apply
its separate publishing, account and financial gates. The packet always records
`permission_granted=false` and `recheck_required_before_use=true`.

The inspection detects version changes across bounded reads, but is not an atomic
cross-object snapshot. This limit must be resolved or accounted for at the actual
publication boundary. Do not claim deployment or safe publication merely because
an assessment or its isolated tests pass.

Unit tests use fixture bytes and a fake media probe/admission dependency. Live
artifact inspection, actual decoder output and API capture are recorded separately
in the execution checkpoint. Neither is a substitute for human viewing/listening
review or full-platform acceptance.
