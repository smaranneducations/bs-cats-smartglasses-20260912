from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from packages.runtime.runner import local_ledger


def runtime_router(require_access):
    router = APIRouter(prefix="/v1/runtime", tags=["runtime"], dependencies=[Depends(require_access)])

    @router.get("/status")
    def status():
        return {"schema_version": "runtime-status-1", "ledger": local_ledger().status(),
                "implementation": "local_deterministic_workers",
                "cloud_worker_deployed": False, "language_model_provider_connected": False,
                "supported_tools": ["catalogue_coverage", "source_policy_queue", "workflow_readiness"],
                "writes": "Local operator CLI only; no public task-submission or pause endpoint."}

    @router.get("/tasks")
    def tasks():
        return {"tasks": local_ledger().recent()}

    @router.get("/tasks/{task_id}")
    def task(task_id: str):
        if not task_id.startswith("task_") or len(task_id) != 37:
            raise HTTPException(404, "Task not found.")
        try:
            return local_ledger().get(task_id)
        except KeyError:
            raise HTTPException(404, "Task not found.") from None

    return router
