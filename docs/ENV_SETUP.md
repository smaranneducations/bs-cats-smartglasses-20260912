# Environment Setup Guide

Your `.env` is the only private file and is not uploaded to GitHub.

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
12. `GOOGLE_APPLICATION_CREDENTIALS` or `GOOGLE_SERVICE_ACCOUNT_KEY_JSON`
13. `OPENAI_API_KEY`
14. `GITHUB_OWNER`
15. `GITHUB_REPO`
16. `GITHUB_TOKEN`
17. `APP_SECRET_KEY`
18. `JWT_SECRET`

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

It creates missing folders and writes a ready-to-run local env check file.

## 4) Validate input (without sending secrets anywhere)

```bash
bash scripts/check-env.sh
```

## 4.1 Optional project provisioning (cost-safe)

After you confirm budget and ownership, run:

```bash
bash scripts/provision-gcp-firebase.sh
```

The script currently enables core APIs and creates:
- storage bucket (if missing)
- BigQuery dataset (if missing)

It intentionally does not auto-create Firebase in case of policy/billing ambiguity; use the [Firebase setup guide](./GCP_FIREBASE_SETUP.md).

## 5) How I can guide you step-by-step

If you want, provide values in this order and I will update `.env`:

1. Core infra block (GCP/Firebase)
2. LLM and agent keys
3. GitHub CI block
4. YouTube block
5. LinkedIn block
6. Storage/render and security extras
