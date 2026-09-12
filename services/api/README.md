# Smart Glasses API

The API exposes the first local-first BS CATS object workflow without requiring a
cloud database or model call.

## Local start

```bash
.venv/bin/uvicorn services.api.src.main:app --reload --port 8080
```

Open `http://127.0.0.1:8080/docs` for the generated OpenAPI interface.

## Access control

- `dev`, `local`, and `test` may run without a token only when `API_WRITE_TOKEN`
  is empty.
- Every `/v1` route requires `X-BS-CATS-Key` when `API_WRITE_TOKEN` is set.
- Any other environment fails closed when `API_WRITE_TOKEN` is missing.
- `/` and `/health` expose no object data and remain available for health checks.

## Object workflow

- `POST /v1/objects` captures evidence or another domain object.
- `POST /v1/objects/{object_id}/curate` creates a reviewable version.
- `POST /v1/objects/{object_id}/review` applies the human approval gate.
- `GET /v1/objects` lists current snapshots with optional type/status filters.
- `GET /v1/objects/{object_id}/history` returns the append-only audit history.
- `POST /v1/validate/smart-glasses` validates evidence and commercial disclosure.
- `GET /v1/taxonomy/smart-glasses` returns machine-readable domain choices.

`OBJECT_STORE_PATH` selects the append-only file. Docker Compose uses a named
volume; direct local runs default to the ignored `.local` directory. A Firestore
adapter can replace this store later without changing the versioned contracts.
