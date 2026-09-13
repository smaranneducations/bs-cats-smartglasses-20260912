# GitHub Pipeline Guide

## Current scope

The inspected CI definition installs project dependencies, runs the Python unit suite and tracked-file secret scan, and compiles the contract module. A workflow file is not evidence of a successful remote run. The 2026-09-13 static review identified a renderer portability risk from macOS-specific fonts; resolve the Linux dependency before relying on rendering checks in CI. No CI run or deployment was performed for this review.

## Delivery boundaries

- Preserve focused reviewed changes and the existing repository. A domain-fit experiment does not require another repository or cloud project.
- Keep source data, private governance, credentials, logs and private artifacts out of public Git and container contexts. Ignore rules do not remove already-tracked material.
- Run applicable tests and a secret scan before an authorized push/release. Never print credentials in build logs.
- Separate build, test, deployment, content publication and budget admission. A green build is not video approval or permission for paid scale-up.

## Deployment design

Prefer one API/agent runtime and an isolated renderer with scale-to-zero rather than four always-on services. Publishing capabilities must remain isolated even when orchestration shares a service. Firebase serves the web application once authorization, rules and deployment are implemented.

Prefer workload identity federation/OIDC for CI-to-cloud authorization with narrowly scoped runtime identities. Do not require downloaded service-account keys or personal access tokens by default. Reuse authorized local GitHub CLI/keychain access.

The local-only secret charter remains binding. Keyless cloud identity avoids some exported keys; it does not authorize copying third-party provider or publishing secrets to CI, cloud secret stores or builds. Resolve that specific boundary before enabling integrations needing it. Record missing consent as a scoped integration gate and continue local work.

Use the current private handoff when available. These are deployment requirements, not a claim that the existing runtime enforces them.
