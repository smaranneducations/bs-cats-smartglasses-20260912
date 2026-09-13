#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ARCHIFY_HOME="${CODEX_HOME:-$HOME/.codex}/skills/archify"
SOURCE="$ROOT/docs/architecture/platform-overview.architecture.json"
OUTPUT="$ROOT/docs/architecture/platform-overview.html"

if [ ! -f "$ARCHIFY_HOME/bin/archify.mjs" ]; then
  printf '%s\n' "Archify is not installed at $ARCHIFY_HOME. Install the user-level skill before regenerating documentation." >&2
  exit 2
fi

ARCHIFY_UPDATE_CHECK_DISABLED=1 node "$ARCHIFY_HOME/bin/archify.mjs" deliver architecture "$SOURCE" "$OUTPUT" --quality showcase --json
