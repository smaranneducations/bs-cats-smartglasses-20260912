# Scoped local agent access

The local development API has separate authenticated principals. Do not omit an
agent credential and thereby use the local human-operator convenience role.

## Launcher and credential custody

Run `.venv/bin/python scripts/serve_scoped_workspace.py` from the workspace. It
starts the existing application on `127.0.0.1:8766`, preserves the human local UI,
and creates a distinct `API_AGENT_TOKEN` for the existing agent-editor role.
It refuses to replace an already configured agent token implicitly.

The generated credential is kept in a user-owned mode-0700 directory beneath
`/private/tmp/smartglasses-local-access-<uid>/session-*/agent.json`. The file is
mode 0600. This location is outside the OneDrive workspace. The launcher prints
only its path and expiry, never the token. No cloud or publishing credentials
are read or copied. This does not make claims about every possible system backup.

After eight hours the launcher removes this agent token from the API environment
and deletes the temporary credential. Human local UI access remains available.
Normal server shutdown also retires the credential. Abrupt process termination
can leave the private temporary file, but the stopped server no longer accepts
its token; the client also checks its recorded expiry.

## Client contract

`packages/runtime/local_api.py` provides `LocalAgentClient(credential_file)`.
It validates custody, project, endpoint and expiry, then checks `/v1/session` for
an authenticated agent editor. It refuses a human or anonymous fallback.

- `get(path)` performs a bounded authenticated local read.
- `capture(values, key)` assigns the authenticated agent identity and requires an idempotency key.
- `curate(object_id, patch, expected_version, key)` uses version-checked curation.

Mutation requests carry the required `X-Workspace-Action` header. The client does
not expose a review or publishing operation, follow redirects, use proxy settings,
print tokens or automatically retry uncertain writes. HTTP errors do not trigger
a fallback to a more privileged identity or a direct database mutation.

On the running service, a scoped agent request to a human-review endpoint returned
HTTP 403. An agent then successfully curated and captured internal commerce
objects, attributed as `research-agent`, with their reviews left pending. Seven
focused client tests passed; this is not a production identity/security audit.

## Production boundary

The explicit local-operator mode is a trusted-desktop convenience, not production
Firebase authentication or tenant isolation. Do not deploy it as public access.
The expiring local token is not a replacement for the eventual cloud identity
and account-holder consent flows. Production activation remains a separate
acceptance requirement.
