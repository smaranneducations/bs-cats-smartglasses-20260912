"""Authenticated views over the existing governed commerce objects."""

from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from packages.intelligence.commerce import assess_commerce

ROOT = Path(__file__).resolve().parents[3]
WEB = ROOT / "apps" / "web" / "intelligence"


def commerce_router(get_store, require_access):
    router = APIRouter(dependencies=[Depends(require_access)])

    @router.get("/v1/intelligence/commerce")
    def commercial_readiness(path_id: list[str] | None = Query(None)):
        store = get_store()
        paths = store.list_objects(object_type="commerce_path")
        if path_id:
            if len(path_id) > 4 or len(set(path_id)) != len(path_id):
                raise HTTPException(400, "Select one to four distinct commercial paths.")
            selected = set(path_id)
            paths = [path for path in paths if path.object_id in selected]
            if {path.object_id for path in paths} != selected:
                raise HTTPException(404, "A selected commercial path is unavailable.")
        evidence = store.list_objects(object_type="commerce_evidence")
        try:
            return assess_commerce([path.model_dump(mode="json") for path in paths], [record.model_dump(mode="json") for record in evidence], datetime.now(timezone.utc))
        except (ValueError, KeyError, TypeError):
            raise HTTPException(422, "Commercial assessment needs one to four valid paths and bounded, dated evidence.") from None

    @router.get("/commerce")
    def commerce_page():
        return FileResponse(WEB / "commerce.html")

    @router.get("/commerce-review-assets/commerce.js")
    def commerce_script():
        return FileResponse(WEB / "commerce.js", media_type="text/javascript")

    @router.get("/commerce-review-assets/commerce.css")
    def commerce_style():
        return FileResponse(WEB / "commerce.css", media_type="text/css")

    return router
