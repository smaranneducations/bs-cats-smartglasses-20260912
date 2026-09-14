# Issue #36: media contract and readiness reconciliation

## Problem statement
The image catalog can describe real product photographs, but the governed media
contract rejects that representation. Several readiness entries describe an old
deployment and misclassify private decision context as public implementation.

## Root cause
Catalog metadata and typed media objects evolved separately. A dated registry
was being treated as current runtime evidence instead of a scoped historical ledger.

## Change
Admit product/editorial photographs without relabeling them as illustrations.
Reject generated or non-image assets claiming photography; preserve rights and
exact-artifact publication gates. Move private decision references into an explicit
context field and reconcile only the requirements listed in the registry's review scope.

## Known evidence, not a whole-app acceptance claim

- Hosting: PR #49, merged `ef70b13`, version `bcff951d58688e3d`, released 2026-09-14.
- Public source baseline: 242 Python and 66 JavaScript tests passed for that release.
- Hosted baseline: 23 read-only route/asset/access checks passed.
- Chrome: Google sign-in and administrator feedback create/edit/search/reload exercised.
- Persistence: the exercised feedback retained its versioned record after reload.
- Media: one attributed, commercially reusable real photograph was cataloged locally;
  same-byte reuse and wrong-product rejection were exercised. It is not cloud media.
- This contract change is source work, not a backend deployment or a media publication.

## Acceptance for this bounded patch

Run the complete Python and JavaScript suites, the registry audit, and staged
publication/secret scans. Photography regression tests cover valid representations,
legacy compatibility, generated/non-image rejection, unchanged rights defaults,
and embedded recipe schema. Regenerate the browser fixture from canonical schemas.
Record actual results in the linked PR; a passing registry audit checks structure
and evidence paths, not the truth or completion of every product capability.

## Still required before friends-and-family UAT

- Deployed private preview delivery and a rights-cleared 9:16, 30-90 second render.
- Exact-artifact human publication approval, then owned-site playback and interactions.
- End-to-end durable warehouse projection and bounded agent execution.
- Restore-tested backups, reconciled cost admission and required account consent.
- Broader administrator, audience, session and mobile workflow acceptance.

These are incomplete gates, not implicitly approved exceptions. No paid generation,
new infrastructure, permission expansion or content publication is part of this patch.

## Migration and rollback
No data rewrite is required; existing representation values are unchanged. Deploy
readers that accept the new values before writing photographs into shared cloud
objects. To roll back, first stop new photograph writes and retain existing records;
do not relabel real photographs as illustrations to satisfy an older reader.

## Change management
Issue #36 is the authorized intake. Use a bounded branch/PR with CI and retain
commit-specific deployment evidence. Private diagnostic and source records stay
outside GitHub. Material feedback updates the requirements ledger and relevant
canonical documentation, not an unreviewed global permission change.
