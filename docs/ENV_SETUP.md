# Environment Setup Guide

Your `.env` is private, ignored by Git, excluded from the root container context, and restricted to the local owner account by the setup tool. Because the workspace path contains `OneDrive`, confirm the folder's actual sync policy before treating it as device-only storage.

## 1) Copy template

```bash
cp .env.template .env
```

## 2) Fill required values first (minimum working set)

### Required to run locally

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

After you confirm budget and ownership, run:

```bash
bash scripts/provision-gcp-firebase.sh
```

The script reads allow-listed non-secret values through `scripts/env_config.py`; it never sources `.env`. It enables core APIs and creates or reuses:
- storage bucket (if missing)
- BigQuery dataset (if missing)

Firebase Auth, Firebase Storage product initialization, rules, IAM, budgets and application deployment remain separate gates. Use the [Firebase setup guide](./GCP_FIREBASE_SETUP.md).

## 5) How I can guide you step-by-step

If you want, provide values in this order and I will update `.env`:

1. Core infra block (GCP/Firebase)
2. LLM and agent keys
3. GitHub CI block
4. YouTube block
5. LinkedIn block
6. Storage/render and security extras
