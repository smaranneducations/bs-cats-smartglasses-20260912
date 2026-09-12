from __future__ import annotations

import os

from fastapi import FastAPI


app = FastAPI(
    title="Smart Glasses API",
    version="0.1.0",
    description="Cloud Run API scaffold for orchestration and object workflows.",
)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "smart-glasses-api", "status": "ok"}


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "healthy",
        "environment": os.getenv("ENVIRONMENT", "dev"),
        "project_id": os.getenv("GCP_PROJECT_ID", ""),
    }
