#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_TOOL="$PROJECT_ROOT/scripts/env_config.py"

read_config() {
  PYTHONDONTWRITEBYTECODE=1 python3 "$ENV_TOOL" get "$1" --env "$ENV_FILE"
}

project="$(read_config GCP_PROJECT_ID)"
region="$(read_config GCP_REGION)"
bucket_region="$(read_config CLOUD_STORAGE_REGION)"
bucket="$(read_config STORAGE_DEFAULT_BUCKET)"
dataset="$(read_config BIGQUERY_DATASET_SMART_GLASSES)"

echo "Provisioning verified foundation for project: $project (region: $region)"

for command_name in gcloud bq; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "[ERROR] Required CLI is unavailable: $command_name"
    exit 1
  fi
done

active_account="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null)"
if [ -z "$active_account" ]; then
  echo "[ERROR] No active gcloud session. Run: gcloud auth login"
  exit 1
fi

gcloud projects describe "$project" >/dev/null
gcloud config set project "$project" >/dev/null
gcloud config set compute/region "$region" >/dev/null

echo "Enabling foundation APIs. Enabling an API does not itself prove a deployed service is free."
gcloud services enable \
  run.googleapis.com \
  firestore.googleapis.com \
  bigquery.googleapis.com \
  storage.googleapis.com \
  cloudscheduler.googleapis.com \
  youtube.googleapis.com \
  --project "$project"

if gcloud storage buckets describe "gs://$bucket" --project "$project" >/dev/null 2>&1; then
  echo "[OK] Storage bucket exists: $bucket"
else
  gcloud storage buckets create "gs://$bucket" --location "$bucket_region" --project "$project" --uniform-bucket-level-access
fi

if bq --project_id "$project" show --format=none "$project:$dataset" >/dev/null 2>&1; then
  echo "[OK] BigQuery dataset exists: $dataset"
else
  bq --project_id "$project" --location "$region" mk --dataset "$project:$dataset"
fi

echo "[OK] Foundation provisioning finished. Firebase Auth, Storage product setup, rules deployment, service IAM, budgets, and application deployment remain separate gates."
