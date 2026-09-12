from __future__ import annotations

from fastapi import FastAPI


app = FastAPI(
    title="Smart Glasses Render Worker",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ready", "service": "render-worker"}


@app.post("/render")
def render_manifest() -> dict[str, str]:
    return {
        "status": "pending",
        "message": "Wire render manifest intake and FFmpeg compose stage next.",
    }
