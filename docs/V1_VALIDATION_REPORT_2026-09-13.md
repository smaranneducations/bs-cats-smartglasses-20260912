# V1 release-candidate validation report

Observed 2026-09-13. Candidate: `1.0.0-rc.1`.

## Verified repository evidence

| Check | Result | Evidence |
|---|---|---|
| Automated contract and behavior suite | Pass | 187 tests passed with `python -m unittest discover -s tests -v` |
| Python compilation | Pass | `packages`, `services` and `scripts` compiled without an error |
| Worktree credential scan | Pass | No likely credentials found among repository candidates |
| Firebase Hosting bundle construction | Pass | 42 files generated under ignored `dist/firebase` |
| Requirements registry | Pass | 35 requirements parsed; registry has no structural failures |
| Repository release audit | Pass | Required release files and safety controls are present |
| Local audience route smoke check | Pass | Preview loaded governed cards without browser console errors |
| Local intelligence route smoke check | Pass | Products, concepts, runs and system state loaded without browser console errors |
| Local operator route smoke check | Pass | Eight-stage workflow and agent roster loaded without browser console errors |

The test suite emits one non-failing Pydantic serializer warning in a disconnected-collector test because the fixture supplies the string `active` where an enum is expected. No test failed, but the fixture should be normalized in a later GitHub change request.

## Requirements disposition

- Implemented: 7.
- Partial: 24.
- Blocked: 2.
- Missing: 2.

These counts make this a repository and local-workflow release candidate, not a completed commercial production system. The detailed mapping is generated in `docs/REQUIREMENTS_AUDIT.md` from `config/requirements-traceability.json`.

## Production denial

Production release remains denied until all of the following have verifiable receipts:

- previously disclosed credentials are rotated and production credentials are scoped;
- provider charges and outstanding commitments are reconciled against the USD 500 cumulative ceiling;
- application writes use durable Firestore persistence rather than local process state;
- the API is deployed to Cloud Run and its identity, limits and health are verified;
- the Firebase Hosting deployment is verified against that API;
- at least one exact final artifact has approved claims, rights-cleared media and approved metadata;
- public publishing returns a provider receipt without ambiguous retry;
- production metrics return to the governed measurement layer;
- the human account holder selects a repository license or deliberately keeps all rights reserved.

## Release interpretation

The candidate can be frozen in GitHub for governed review. It must not be tagged or described as production-ready, revenue-generating, autonomously self-modifying or fully deployed. Ethics, legality, safety, privacy, rights and truth remain mandatory gates above financial sustainability and revenue.
