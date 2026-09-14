# Version 1 release readiness

Updated 2026-09-14. This supersedes the earlier undeployed-infrastructure snapshot, not the unresolved production gates.

## Decision

The hosted administrator and audience interfaces are deployed. Fresh Google sign-in, persisted feedback, product inspection and real Firestore comparisons have been exercised; see the [acceptance record](acceptance/2026-09-14-hosted-workflows.md).

The complete autonomous research-to-publication-to-revenue loop is **not accepted**. A reachable URL, a passing test suite, or a release tag does not establish that outcome.

## Evidence at the last checkpoint

| Area | Observed state |
| --- | --- |
| Firebase Hosting and Cloud Run | Deployed; production health reports a healthy Firestore object store. |
| Google authentication | Fresh sign-out, reload and Google sign-in passed in production Chrome. |
| Governed object store | Hosted feedback persisted through reload/sign-in; real version-history inspection and comparison passed after the missing index was deployed. |
| Browser workflows | Operator navigation, product evidence, ontology-based comparison and public disclosure/empty-state views exercised. |
| Private media | Draft metadata is available to authenticated administrators; hosted video bytes remain unavailable. Required storage access has not been granted. |
| Publishing | Three visible drafts remain without complete rights/factual/exact-artifact clearance; no production publishing success claimed. |
| Durable workers and audience engagement | Not accepted; object-store health does not prove these separate persistence paths. |
| Budget, backups and credentials | No current reconciliation, restore-drill acceptance or complete rotation receipt established by this checkpoint. |
| GitHub | Repairs and acceptance receipts pass through PRs; current evidence is linked from the acceptance record. |

BigQuery existence, agent definitions and adapter code are not proof of a populated warehouse or continuously running cloud workflows. Preserve explicit unknowns until those paths are exercised.

## Repeatable checks

```bash
python scripts/release_readiness.py
python scripts/check_hosted_app.py --output .local/acceptance/hosted-smoke.json
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/*.cjs
python scripts/secret_scan.py --mode tracked
```

Use the configured environment interpreter. The repository checker assesses file presence, JSON syntax and ignore declarations only. The hosted checker performs bounded anonymous requests to the project's allowlisted Hosting origin and its directly linked first-party assets; it rejects incorrect statuses, MIME types, HTML asset fallbacks and excessive responses. It never signs in, changes data, changes access, posts content or certifies the complete release.

Fresh browser acceptance, attributable writes, media playback, backups, financial controls and provider publication receipts remain separate checks. A private sanitized smoke receipt is evidence of its stated scope and timestamp, not permanent proof that every integration works.

## Unresolved admission gates

- Authorize the exact private-media access boundary, then verify private upload, playback, hash/size checks and anonymous denial.
- Validate the production media-probe dependency, rights/factual controls and approval binding for an exact artifact and metadata packet.
- Exercise durable orchestration, owned engagement and metric return without presenting in-memory/local paths as production persistence.
- Reconcile actual costs and reservations, validate applicable credential replacement and complete a scoped backup/restore drill.
- Establish lawful content and repository reuse rights and the permitted provider publishing/monetization relationships.

Issue 36 remains the overall acceptance tracker. Do not downgrade a failing requirement into a passed gate by renaming the milestone.
