#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
PHASE="${1:-foundation}"
shift || true

if [ ! -f "$ENV_FILE" ]; then
  echo "[ERROR] Missing .env file. Run: bash scripts/bootstrap.sh"
  exit 1
fi

PYTHONDONTWRITEBYTECODE=1 python3 "$PROJECT_ROOT/scripts/env_config.py" check \
  --env "$ENV_FILE" \
  --phase "$PHASE" \
  "$@"
