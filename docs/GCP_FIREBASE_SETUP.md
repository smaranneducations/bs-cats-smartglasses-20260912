# GCP + Firebase setup: local-first and cost-conscious

## Reuse the authorized project

Use existing configuration and authorized CLI sessions to obtain non-secret project IDs, app metadata and repository bindings. Do not ask for values already available or create duplicate projects. Existing Blaze/billing approval is not unlimited spending authority; a resource is not proof of a working integration.

Ask the financial owner only for necessary account-holder consent, unavailable access or a reserved financial decision. Prepare the precise local flow, not a request for passwords, JSON keys or tokens in chat.

## Identity and configuration

- Prefer local Application Default Credentials or short-lived identity and narrowly scoped cloud/CI workload identity.
- Do not download a service-account JSON key by default. Grant permissions by workload, data boundary and operation, not broad administration to bypass errors.
- Reuse supported GitHub CLI/keychain authentication for local repository operations. A long-lived personal access token is not a universal prerequisite.
- Retrieve Firebase web configuration as non-secret metadata where authorized. It does not secure the database; authenticated authorization and restrictive rules are separate gates.
- Keep Firebase/GCP IDs consistent and preserve existing region, bucket and dataset choices unless an explicit migration decision applies.
- Enable only APIs/resources required for the accepted slice. Do not create a service per agent or reprovision merely to assess another domain.

## Secret boundary

Keep secrets in approved device-local storage, never chat, public Git, frontend bundles or build contexts. Establish the actual OneDrive sync policy before keeping replacement credentials there. Ignore rules neither prevent synchronization nor purge history.

Do not assume moving third-party secrets to cloud Secret Manager or GitHub secrets satisfies a local-only charter. Workload identity does not automatically solve third-party publishing/model credentials. Document the integration boundary and obtain specific authorization if external secret storage is necessary.

Previously disclosed credentials need legitimate rotation/revocation planning. Identify shared-project dependencies first; do not revoke shared keys blindly. Record field/status only, never values.

## Resource and release gates

Use scale-to-zero and bounded workloads where supported. Before unattended paid work, require reconciled accounting and enforced task, daily and total admissions. Budget alerts alone are not spend caps. Existing storage, subscriptions and delayed charges count.

Firestore/Auth rules, IAM, product initialization, artifact storage, source permissions, publisher consent and actual deployment are separate gates. Complete the applicable controls before claiming a cloud milestone. Continue deterministic local work while an integration is blocked.

See `docs/ENV_SETUP.md` and `docs/PIPELINE.md`. This document does not provision resources or install cost controls.
