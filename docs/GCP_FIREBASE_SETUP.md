# GCP + Firebase Setup (local-first, cost-safe)

You gave OAuth/API secrets. To finish full provisioning, we still need a project and service credentials that match your ownership.

If you want me to do this by myself in this thread, I need:
1. Cloud billing-enabled account access,
2. Permission to create projects/services in GCP/Firebase,
3. Approval to run provisioning commands.

If you prefer manual one-by-one, use this exact flow:

1. Create or select a GCP project
- https://console.cloud.google.com/projectcreate
- https://console.cloud.google.com/cloud-resource-manager
- Capture: `GCP_PROJECT_ID`, project number

2. Enable required APIs in that project
- https://console.cloud.google.com/apis/library/run.googleapis.com
- https://console.cloud.google.com/apis/library/firestore.googleapis.com
- https://console.cloud.google.com/apis/library/bigquery.googleapis.com
- https://console.cloud.google.com/apis/library/storage.googleapis.com
- https://console.cloud.google.com/apis/library/cloudscheduler.googleapis.com
- https://console.cloud.google.com/apis/library/youtube.googleapis.com

3. Create Firestore + bucket + BigQuery dataset
- Firestore: https://console.firebase.google.com/ (or GCP console)
- Cloud Storage: https://console.cloud.google.com/storage
- BigQuery dataset: https://console.cloud.google.com/bigquery

4. Create Firebase app/service bindings
- Firebase Console: https://console.firebase.google.com/
- Register web app and copy:
  - `FIREBASE_WEB_API_KEY`
  - `FIREBASE_AUTH_DOMAIN`
  - `FIREBASE_STORAGE_BUCKET`
  - `FIREBASE_MESSAGING_SENDER_ID`
  - `FIREBASE_APP_ID`

5. Create a service account for backend services
- https://console.cloud.google.com/iam-admin/serviceaccounts
- Create a least-privilege service account for:
  - `Cloud Run Invoker`
  - `BigQuery Data Editor` (or narrower roles as needed)
  - `Storage Object Admin`
  - `Firestore User`
- Download JSON key and fill:
  - `GOOGLE_APPLICATION_CREDENTIALS`

6. GitHub pipeline auth
- https://github.com/settings/personal-access-tokens/new
- Use narrow scope token, fill `GITHUB_TOKEN`

Cost safety:
- No heavy deploy/builds are executed by default.
- Cloud Run services are set to run on-demand with minimal instances in bootstrap.
- We keep Playwright/FFmpeg work disabled until you explicitly approve publish-scale rendering.

Important:
- Keep all secrets local only (`.env` is ignored).
- Do not commit any credential strings.
