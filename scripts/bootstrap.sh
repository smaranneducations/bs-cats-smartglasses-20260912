#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[INFO] Bootstrapping Smart Glasses Intelligence Platform..."

if [ ! -f "$PROJECT_ROOT/.env" ]; then
  cp "$PROJECT_ROOT/.env.template" "$PROJECT_ROOT/.env"
  echo "[INFO] Created .env from template."
else
  echo "[INFO] .env already exists, keeping existing values."
fi

mkdir -p \
  "$PROJECT_ROOT/apps/web" \
  "$PROJECT_ROOT/services/api/src" \
  "$PROJECT_ROOT/services/agent-runtime" \
  "$PROJECT_ROOT/services/render-worker" \
  "$PROJECT_ROOT/services/publisher-worker" \
  "$PROJECT_ROOT/packages/contracts" \
  "$PROJECT_ROOT/packages/mcp-tools" \
  "$PROJECT_ROOT/infra/terraform" \
  "$PROJECT_ROOT/docs" \
  "$PROJECT_ROOT/sql/bigquery" \
  "$PROJECT_ROOT/.github/workflows"

cat > "$PROJECT_ROOT/scripts/.bootstrap-status" <<'EOF'
BOOTSTRAPPED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
STATUS=ok
EOF

cat > "$PROJECT_ROOT/.env.local" <<'EOF'
# Optional local-only values only.
# Fill only if you need overrides for local testing.
APP_DEBUG=true
EOF

echo "[INFO] Bootstrap complete. Fill .env, then run: bash scripts/check-env.sh"
