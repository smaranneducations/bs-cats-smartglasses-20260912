# Smart Glasses Intelligence Platform (Bootstrap Edition)

This repository is the foundation for a reusable domain-intelligence platform, with SmartGlasses as its first domain.

## What is included

The scaffold is intentionally conservative and aligned with the blueprint:

- Firebase web app skeleton
- Cloud Run-ready Python services
- Render and publisher worker placeholders
- Shared contract packages
- Terraform-like infrastructure placeholders
- GitHub Actions baseline pipeline
- Docker Compose local stack
- Zero-cost local video renderer and founder demo dashboard
- Secrets/config template (`.env.template`)
- `.env` ignore policy and onboarding docs

## Folder layout

```
apps/web                 # Firebase web frontend
services/api             # Main Cloud Run API / orchestration
services/agent-runtime   # Reusable generic agent runtime
services/render-worker   # Playwright + FFmpeg render worker
services/publisher-worker # Social channel adapters
packages/contracts       # Shared JSON/Pydantic contract placeholders
packages/mcp-tools       # Domain/tool layer placeholders
infra/terraform          # Infrastructure placeholders
docs                    # Setup and secrets guides
scripts                 # Bootstrap and validation helpers
```

## Quick start

1. Copy env template to `.env`:

```bash
cp .env.template .env
```

2. Fill only the values needed for the current phase. Never source `.env` in a shell.

```text
GCP_PROJECT_ID
FIREBASE_PROJECT_ID
OPENAI_API_KEY
YOUTUBE_API_CLIENT_ID / YOUTUBE_API_CLIENT_SECRET
LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET
GITHUB_OWNER / GITHUB_REPO (the local GitHub CLI keychain may provide authentication)
```

3. Canonicalize and check the private configuration:

```bash
bash scripts/bootstrap.sh
bash scripts/check-env.sh
```

4. Start local services:

```bash
docker compose up --build
```

## Zero-cost local content demo

The demo path uses Pillow, FFmpeg, and the built-in macOS `say` voice. It does not call an external model, speech, image, or hosting API. Generated media and source data stay under the Git-ignored `.local/` directory.

```bash
python3 -m pip install -r scripts/requirements-demo.txt
python3 scripts/render_local_video.py .local/content/<script>.json
python3 scripts/build_demo_dashboard.py .local/content/<script>.json \
  --video .local/renders/<script-id>/demo.mp4 \
  --captions .local/renders/<script-id>/captions.en.srt \
  --thumbnail .local/renders/<script-id>/thumbnail.png \
  --review-packet .local/reviews/<script-id>.html
python3 scripts/serve_demo.py
```

The preview binds only to `127.0.0.1` and serves only the self-contained `.local/demo/` package. It cannot expose the broader private `.local/` research and event store.

## Note

The `.env` file must never be committed or included in a container image. `scripts/env_config.py` treats it as data, reports statuses without values, removes duplicate assignments atomically, and sets mode `0600`.

Before staging or pushing, scan public repository candidates without printing matched values:

```bash
python3 scripts/secret_scan.py --mode worktree
```

## Technical charter

- Keep architecture simple, incremental, and low-cost by default.
- Do not create or run cost-intensive workloads without explicit approval.
- Keep all secrets on local disk only (`.env`).
- Build internal, zero-cost drafts autonomously; require explicit approval for external publishing, material spend, and irreversible actions.

## Next milestone after this setup

- Implement schema and data model migrations
- Add object registry and charter persistence
- Add MCP tool endpoints
- Add publisher adapter for first channel (YouTube) once OAuth is configured
- Wire review/approval gates before automated publishing
