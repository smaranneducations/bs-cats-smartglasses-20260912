from __future__ import annotations

from fastapi import FastAPI


app = FastAPI(
    title="Smart Glasses Publisher Worker",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ready", "service": "publisher-worker"}


@app.get("/publish")
def publish() -> dict[str, str | bool]:
    return {
        "status": "placeholder",
        "enabled": False,
        "message": "Wire channel adapters and approvals before live publishing.",
    }
