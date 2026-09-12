from __future__ import annotations

from fastapi import FastAPI


app = FastAPI(
    title="Smart Glasses Agent Runtime",
    version="0.1.0",
    description="Generic reusable agent runtime scaffold.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ready", "service": "agent-runtime"}


@app.get("/agent/run")
def run_agent() -> dict[str, str | bool]:
    return {
        "status": "placeholder",
        "message": "Wire role-based agent contracts and task invocation next.",
        "enabled": False,
    }
