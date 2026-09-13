# Application API

The FastAPI service is the version 1 application boundary for operator, audience, intelligence, semantic, media, release, warehouse, and runtime routes. It also serves the local browser applications.

## Security boundary

- Local mutable actions require the workspace-action header and a derived local actor.
- Hosted administrator actions require a valid Firebase ID token whose verified email is in the ignored administrator allowlist.
- Public event intake is bounded and is not administrative authority.
- Publisher credentials are not required by the general API process.
- The OpenAPI explorer is intentionally disabled.

## Deployment boundary

The container is buildable from the repository root with `services/api/Dockerfile`. Do not deploy it as a production service while `OBJECT_STORE_PATH` points to ephemeral container storage. Durable Firestore cutover, workload identity, reconciled cost admission, rotated secrets, and production origin rules are release gates.

The image excludes `.env`, `.local`, local data, test artifacts, and provider credentials through `.dockerignore`.
