# Environment Setup Guide

The setup tool is designed to keep `.env` ignored by Git, excluded from the root container context and restricted to the local owner account. These controls do not prove credentials were never committed or synchronized. Establish the actual OneDrive sync policy before treating this workspace as device-only storage. Never paste secrets into chat.

## 1) Preserve existing configuration

Reuse an existing `.env`; do not overwrite it with a template. For a genuinely new setup, create configuration from `.env.template` only if the target does not exist, with restrictive permissions in a confirmed device-local location. Use local CLI/browser consent; report field names and status, not values.

## 2) Fill required values first (minimum working set)

### Cloud integration configuration

Deterministic local foundation work does not need every cloud/publishing credential. Configure only the next integration. Nonempty values do not prove validity, scope or connectivity.

1. `GCP_PROJECT_ID`
2. `GCP_REGION`
3. `FIREBASE_PROJECT_ID`
4. `FIREBASE_WEB_API_KEY`
5. `FIREBASE_AUTH_DOMAIN`
6. `FIREBASE_STORAGE_BUCKET`
7. `FIREBASE_MESSAGING_SENDER_ID`
8. `FIREBASE_APP_ID`
9. `FIRESTORE_DATABASE_ID`
10. `BIGQUERY_DATASET_SMART_GLASSES`
11. `BIGQUERY_PROJECT_ID`
12. `STORAGE_DEFAULT_BUCKET`
13. `GITHUB_OWNER`
14. `GITHUB_REPO`
15. GitHub CLI keychain authentication or `GITHUB_TOKEN`
16. `APP_SECRET_KEY`
17. `JWT_SECRET`

Application-model credentials are an integration gate, not a prerequisite for deterministic local foundation work. Prefer local Google ADC or workload identity over a downloaded service-account key.

### Required for first channel publish

1. `YOUTUBE_API_CLIENT_ID`
2. `YOUTUBE_API_CLIENT_SECRET`
3. `YOUTUBE_REFRESH_TOKEN`
4. `YOUTUBE_CHANNEL_ID`

### Required for LinkedIn later

1. `LINKEDIN_CLIENT_ID`
2. `LINKEDIN_CLIENT_SECRET`
3. `LINKEDIN_ACCESS_TOKEN`

## 3) Run bootstrap helper

```bash
bash scripts/bootstrap.sh
```

It creates missing folders and canonicalizes the existing `.env` without executing it. Duplicate assignments are resolved using the last effective value and the result is written atomically with mode `0600`.

## 4) Validate input (without sending secrets anywhere)

```bash
bash scripts/check-env.sh
```

To inspect the later YouTube configuration boundary without revealing values:

```bash
bash scripts/check-env.sh youtube
```

## 4.1 Optional project provisioning (cost-safe)

For an authorized provisioning slice only, reuse the selected project and current financial envelope before this helper. Do not repeat project creation or request approval already provided. This command can modify cloud resources:

```bash
bash scripts/provision-gcp-firebase.sh
```

The script reads allow-listed non-secret values through `scripts/env_config.py`; it never sources `.env`. It enables core APIs and creates or reuses:
- storage bucket (if missing)
- BigQuery dataset (if missing)

Firebase Auth, Firebase Storage product initialization, rules, IAM, budgets and application deployment remain separate gates. Use the [Firebase setup guide](./GCP_FIREBASE_SETUP.md).

## 5) Minimal-human-effort credential collection

Discover non-secret metadata through authorized CLI access, reuse secure sessions and prepare local consent flows for missing permissions. Do not block deterministic local work on unrelated keys or collect credentials for speculative integrations.

When human action is unavoidable, provide the exact local consent page or field and its required permission. The human enters secrets locally, never through chat or a model prompt. Persist only in approved device-local storage and report field/status. Never request Google, Firebase, GitHub or email account passwords.

Prefer local ADC/keychain and short-lived workload identity. Treat YouTube upload and analytics permissions separately. Restrict publishing tokens to the publisher; do not forward the entire environment to every service.

Resolve third-party secret-store conflicts before cloud execution. Plan rotation of disclosed secrets with shared-project dependencies in mind. Formatting checks and ignore rules do not prove token validity, least privilege, device-only storage or safe publication.
