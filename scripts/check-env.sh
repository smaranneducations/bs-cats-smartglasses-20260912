#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "[ERROR] Missing .env file. Run: cp .env.template .env"
  exit 1
fi

required=(
  GCP_PROJECT_ID
  GCP_REGION
  FIREBASE_PROJECT_ID
  FIREBASE_WEB_API_KEY
  FIREBASE_AUTH_DOMAIN
  FIREBASE_STORAGE_BUCKET
  FIREBASE_MESSAGING_SENDER_ID
  FIREBASE_APP_ID
  FIRESTORE_DATABASE_ID
  BIGQUERY_PROJECT_ID
  BIGQUERY_DATASET_SMART_GLASSES
  OPENAI_API_KEY
  GITHUB_OWNER
  GITHUB_REPO
  GITHUB_TOKEN
  APP_SECRET_KEY
  JWT_SECRET
)

echo "[INFO] Checking required env vars..."
missing=0
for key in "${required[@]}"; do
  value=$(grep -E "^${key}=" "$ENV_FILE" | tail -n 1 | sed "s/^${key}=//")
  if [ -z "$value" ]; then
    echo "[MISSING] $key"
    missing=1
  else
    echo "[OK] $key"
  fi
done

if [ "$missing" -eq 1 ]; then
  echo "[ERROR] Required values missing. Fill them in .env"
  exit 1
fi

echo "[INFO] Required fields look populated."
