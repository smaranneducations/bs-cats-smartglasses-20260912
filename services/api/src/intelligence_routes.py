from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from packages.runtime.runner import local_ledger
from packages.governance.review_routing import classify_review
from packages.domain_engine.profile import active_domain

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "apps/web/intelligence"


def intelligence_router(get_store, require_access):
    router = APIRouter(tags=["intelligence-workspace"], dependencies=[Depends(require_access)])

    @router.get("/intelligence", include_in_schema=False)
    def page():
        return FileResponse(ASSETS / "index.html", media_type="text/html")

    @router.get("/intelligence/app.js", include_in_schema=False)
    def javascript():
        return FileResponse(ASSETS / "app.js", media_type="text/javascript")

    @router.get("/intelligence/style.css", include_in_schema=False)
    def stylesheet():
        return FileResponse(ASSETS / "style.css", media_type="text/css")

    @router.get("/v1/intelligence/overview")
    def overview():
        store = get_store()
        objects = store.list_objects()
        if len(objects) > 500:
            from fastapi import HTTPException
            raise HTTPException(422, "This workspace view requires pagination beyond 500 objects.")
        definitions = store.definitions()
        cloud = json.loads((ROOT / "config/cloud-resource-state.json").read_text())
        creative = json.loads((ROOT / "config/creative-direction.json").read_text())
        return {
            "schema_version": "intelligence-overview-1",
            "data_backend": "local_versioned_object_store",
            "counts": {"objects": len(objects), "concepts": len(definitions),
                       "by_type": dict(Counter(item.object_type for item in objects))},
            "products": [{"object_id": item.object_id, "title": item.title, "version": item.version,
                          "category": item.payload.get("category"), "market": item.payload.get("market"),
                          "variant": item.payload.get("variant"), "status": item.status.value,
                          "review_state": classify_review(item).display_state,
                          "human_action_required": classify_review(item).required,
                          "recorded_fields": len(item.payload.get("fields", {}))}
                         for item in objects if item.object_type == "product"],
            "runtime": local_ledger().status(),
            "cloud_observation": cloud,
            "creative_direction": creative,
            "active_domain": active_domain().public_dict(),
            "learning": {"governance_feedback_recorded": True, "automatic_policy_promotion": False,
                         "runtime_learning_connected": True},
            "commercial": {"collected_revenue": None, "qualified_audience": None,
                           "active_relationship_verified": False, "currency": "USD"},
            "boundaries": ["A recorded source link is not independent verification.",
                           "The warehouse schema exists; the app still reads local versioned objects.",
                           "Deterministic workers are not connected language-model agents.",
                           "Task completion does not approve facts or an exact final publication."]}

    @router.get("/v1/intelligence/learning")
    def learning():
        from packages.intelligence.learning import learning_overview
        return learning_overview(get_store())

    @router.get("/v1/intelligence/domain")
    def domain_profile():
        return active_domain().public_dict()

    @router.get("/v1/intelligence/impact/{object_id}")
    def impact(object_id: str):
        from fastapi import HTTPException
        from packages.intelligence.learning import impact_report
        try:
            return impact_report(get_store(), [object_id])
        except ValueError:
            raise HTTPException(422, "The impact request needs a current object and a bounded dependency graph.") from None

    return router
