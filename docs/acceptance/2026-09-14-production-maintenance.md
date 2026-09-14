# Production maintenance acceptance: 2026-09-14

## Working entry points

- [Administrator workflow](https://bs-cats-smartglasses-20260912.web.app/operator)
- [Audience application](https://bs-cats-smartglasses-20260912.web.app/discover)
- [Service health](https://bs-cats-smartglasses-20260912.web.app/health)

## Verified in hosted Chrome

| Check | Observed result |
| --- | --- |
| Google authentication | Fresh application sign-out, reload and Google sign-in succeeded. |
| Protected administrator access | Signed-out reload requires login; anonymous session API returns 401. |
| Feedback creation | One genuine Codex acceptance observation was saved and survived a full reload. |
| Versioned editing | The same observation was edited, persisted as version 2, and remained present after fresh sign-in. |
| Product search and status | Search reduced six records to one; combined filters showed zero results; clearing restored six. |
| Ontology | Product concepts, definitions and the definition-change form were accessible without changing production facts. |
| Agent instructions | The roster and instruction-review form were accessible; authority boundaries were not changed. |
| Creative library | Twelve scene primitives were visible through the operator navigation. |
| Audience page | Honest empty-feed state and the image/evidence panel loaded. |

No product claims, factual approvals, agent permissions or publication approvals were changed for these checks. The single new feedback record identifies Codex as the source of the technical observation, not a human editorial decision.

## Automated checks

- Backend maintenance candidate: 228 Python tests and 41 JavaScript tests passed.
- Deployed public frontend: 215 Python tests and 45 JavaScript tests passed before PR #42 merged through normal CI.
- HTTPS staging checks: healthy Firestore service, unauthenticated writes denied, foreign origins denied, missing action headers denied and cross-site requests denied.
- Production Firebase routing: health returns 200 and an anonymous administrator session request returns 401.
- Credential scan passed on the staged source changes. No account passwords or provider tokens are included in this report.

These suites overlap; their counts must not be added as unique tests. Browser acceptance is separate from unit-test coverage.

## Deployment and recovery

| Component | Receipt |
| --- | --- |
| Hosting source | `216e36cc088b518017bb0eba689da0373d5fac79` (PR #42) |
| Hosting version | `98d39ce36cbb26cf` |
| Hosting release | `1789322163242000` |
| API serving revision | `bs-cats-api-check-60b0e90`, 100% service traffic |
| API immutable image | `sha256:7f83b4bed69f13554ab90852425354c686b0a9f12150894e58e392c55a9e6be0` |
| Prior API revision | `bs-cats-api-00005-2dz`, verified ready and retained for rollback |
| Prior Hosting version | `3a106e29600cfdb2` |

The API maintenance source and detailed diagnostic record remain in the existing restricted change record. They have not been silently represented as merged public source. No branch-protection bypass or advisory publication was performed.

The existing service account, authentication, administrator allowlist, database rules, one CPU, 512 MiB memory and maximum two instances were retained. The temporary maintenance traffic tag was removed. The package reused existing image dependencies without starting a paid Cloud Build job. Provider charges remain unreconciled; this is not a claim of zero cloud cost.

## Acceptance boundary

This completes the reported login, loading, filtering and feedback-persistence repairs. It does **not** certify the entire business vision or close overall acceptance issue #36.

There are no rights-cleared, approved published videos in the public feed. Playback, social publishing and audience interaction on a published video have therefore not passed hosted acceptance. The public comparison link still targets the protected intelligence route and is not an accepted ordinary-visitor workflow. Those gaps must remain explicit rather than being hidden by fake content, weakened authentication or invented approvals.
