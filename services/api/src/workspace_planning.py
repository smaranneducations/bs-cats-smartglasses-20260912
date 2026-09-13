from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field

from packages.contracts.object import StrictContract
from packages.contracts.production import build_storyboard, refresh_job, source_refresh_plan
from packages.contracts.store import DuplicateObjectError, ObjectNotFoundError


class StoryboardRequest(StrictContract):
    brief_object_id: str
    expected_version: int = Field(ge=1)
    aspect_ratio: Literal["9:16"] = "9:16"


def capture_once(store, item, principal):
    try:
        return store.get(item.object_id)
    except ObjectNotFoundError:
        try:
            return store.capture(item, actor_id=principal.actor_id, actor_type=principal.actor_type)
        except DuplicateObjectError:
            return store.get(item.object_id)


def planning_router(get_store, require_access, can_edit):
    router = APIRouter()

    @router.get("/v1/sources/refresh-plan")
    def plan(_principal=Depends(require_access)):
        return {"execution_enabled": False,
                "items": [source_refresh_plan(item) for item in get_store().list_objects(object_type="source_policy")]}

    @router.post("/v1/sources/refresh-plan")
    def queue_plan(principal=Depends(can_edit)):
        store = get_store()
        jobs = [capture_once(store, refresh_job(policy), principal)
                for policy in store.list_objects(object_type="source_policy")]
        return {"execution_enabled": False, "jobs": jobs}

    @router.post("/v1/content/storyboards", status_code=201)
    def storyboard(body: StoryboardRequest, principal=Depends(can_edit)):
        store = get_store()
        brief = store.get(body.brief_object_id)
        if brief.object_type != "content_brief":
            raise HTTPException(422, "Choose a content brief.")
        if brief.version != body.expected_version:
            raise HTTPException(409, "The brief changed. Reload before preparing its visual plan.")
        return capture_once(store, build_storyboard(brief, body.aspect_ratio), principal)

    return router
