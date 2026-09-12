#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[INFO] Bootstrapping Smart Glasses Intelligence Platform..."

if [ ! -f "$PROJECT_ROOT/.env" ]; then
  cp "$PROJECT_ROOT/.env.template" "$PROJECT_ROOT/.env"
  chmod 600 "$PROJECT_ROOT/.env"
  echo "[INFO] Created private .env from the public template."
else
  PYTHONDONTWRITEBYTECODE=1 python3 "$PROJECT_ROOT/scripts/env_config.py" normalize \
    --env "$PROJECT_ROOT/.env" \
    --template "$PROJECT_ROOT/.env.template"
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
  "$PROJECT_ROOT/.github/workflows" \
  "$PROJECT_ROOT/tests"

echo "[INFO] Bootstrap complete. Run: bash scripts/check-env.sh"
