#!/usr/bin/env bash
set -euo pipefail

project="${GCP_PROJECT_ID:-}"
region="${GCP_REGION:-us-central1}"
bucket_region="${CLOUD_STORAGE_REGION:-$region}"
firebase_project="${FIREBASE_PROJECT_ID:-$project}"

if [ -z "$project" ] || [ -z "$firebase_project" ]; then
  echo "GCP_PROJECT_ID and FIREBASE_PROJECT_ID are required."
  exit 1
fi

echo "Provisioning scaffold for project: $project (region: $region)"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud CLI is not installed. Install Google Cloud SDK first."
  exit 1
fi

echo "Checking active gcloud auth..."
if ! gcloud auth list --filter=status:ACTIVE --format='value(account)' | grep -q .; then
  echo "No active gcloud auth session found. Run: gcloud auth login"
  exit 1
fi

echo "Creating/setting project..."
gcloud projects describe "$project" >/dev/null 2>&1 || gcloud projects create "$project"
gcloud config set project "$project"
gcloud config set compute/region "$region"

echo "Enabling core APIs (cost-safe: no resources created yet)..."
gcloud services enable run.googleapis.com firestore.googleapis.com bigquery.googleapis.com storage.googleapis.com cloudscheduler.googleapis.com
gcloud services enable youtube.googleapis.com

echo "Creating Cloud Storage bucket if missing..."
bucket="${STORAGE_DEFAULT_BUCKET:-$project-assets}"
if ! gsutil ls "gs://$bucket" >/dev/null 2>&1; then
  gsutil mb -l "$bucket_region" "gs://$bucket"
fi

echo "Initializing BigQuery dataset if missing..."
bq ls --project_id "$project" | grep -q "smart_glasses_core" || bq --project_id "$project" mk smart_glasses_core

echo "Note: Firebase bootstrap is intentionally not auto-fired from this script because it can alter project billing/setup state."
echo "Open Firebase Console and enable Firebase for $firebase_project manually when ready:"
echo "https://console.firebase.google.com/"

echo "Provisioning checks passed. Add additional service/resource rollout step-by-step with your approval."
