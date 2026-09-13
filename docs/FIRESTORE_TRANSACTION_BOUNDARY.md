# Firestore transaction boundary

Date: 2026-09-13.

## Decision

Use native Firestore transactions for current governed object envelopes, version history and idempotency receipts. Keep the REST transport small, on the already-installed HTTP client, with the approved project and database fixed. Do not copy local provider secrets into a container or claim local SQLite leases are cloud persistence.

The adapter requires a domain transition/authorization validator. Storage compare-and-swap is not a replacement for object governance, authenticated actor identity, source approval or financial permission. The current application has not yet been switched from its local store to this journal. Wiring the shared domain transition boundary is a required integration step, not an optional permanent fallback.

## Atomic operation

Read the receipt, current object and at most ten pinned parents inside one transaction. Reject changed versions. Require the pure domain validator to explicitly authorize the proposed transition. Atomically write the current envelope, a create-only version record and a create-only receipt. A repeated key with the same actor and content returns the original result; different content conflicts.

An explicitly aborted transaction may retry up to three times. A timeout or server failure during commit is ambiguous: read the same receipt to resolve it, and do not replay if the receipt is still absent. Preserve the operation identity for reconciliation. Rollback attempts do not erase the original failure.

History remains subject to applicable deletion and retention rules. Create-only application history is not an exemption from lawful erasure or an instruction to preserve prohibited source content indefinitely.

## Authority, identity and money

The production token provider uses the attached Cloud Run service identity. A local CLI token path requires explicit opt-in, captures the existing gcloud access token in memory and does not read `.env`, copy credential files or print token values. No credentials are downloaded or installed by this change.

Transport admission is denied by default before identity retrieval. Every permitted Firestore operation must pass an admission collaborator, including document-read and document-write counts. The real reconciled budget adapter is not yet connected; this code does not arm paid operations, bootstrap cloud documents, alter IAM or deploy rules/indexes.

The browser billing report reached a signed-out Google account chooser. Project billing is enabled, but actual charges remain unavailable. Do not infer zero cost, freshness or free-tier headroom from successful CLI authentication or an empty warehouse. Continue independent implementation while reserving that scoped account-holder sign-in for the next human session.

## Indexing and tests

Index exemptions are authored for serialized snapshots and receipt results to avoid unnecessary indexing of large opaque payloads. They have not been deployed. Current lifecycle/type/version fields remain separate inspectable envelope fields.

The added contract tests use an in-memory transport to exercise atomic writes, stale versions, parent versions, duplicate/conflicting requests, bounded abort retries, uncertain commit handling, secret rejection and value encoding. They do not establish live Firestore permissions, actual billing, Firebase Auth, emulator behavior or full application integration.

## Primary interface references

- [Firestore transaction start](https://firebase.google.com/docs/firestore/reference/rest/v1/projects.databases.documents/beginTransaction)
- [Firestore transactional document reads](https://firebase.google.com/docs/firestore/reference/rest/v1/projects.databases.documents/batchGet)
- [Firestore atomic commit](https://firebase.google.com/docs/firestore/reference/rest/v1/projects.databases.documents/commit)
- [Cloud Run service identity](https://docs.cloud.google.com/run/docs/securing/service-identity)
