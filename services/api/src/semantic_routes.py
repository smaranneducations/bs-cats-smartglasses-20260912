from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from packages.contracts.object import StrictContract
from packages.knowledge.semantic import SemanticTools


class CompareRequest(StrictContract):
    product_ids: list[str] = Field(min_length=2, max_length=4)
    concepts: list[str] = Field(min_length=1, max_length=25)
    as_of: datetime | None = None


def semantic_router(get_store, require_access):
    router = APIRouter(prefix="/v1/semantic")

    @router.get("/ontology")
    def ontology(_principal=Depends(require_access)):
        return SemanticTools(get_store()).ontology()

    @router.get("/products/{object_id}/assertions")
    def assertions(object_id: str, as_of: datetime | None = None, _principal=Depends(require_access)):
        try:
            return SemanticTools(get_store()).assertions(object_id, as_of=as_of)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @router.post("/compare")
    def compare(body: CompareRequest, _principal=Depends(require_access)):
        try:
            return SemanticTools(get_store()).compare(body.product_ids, body.concepts, body.as_of)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @router.get("/status")
    def status(_principal=Depends(require_access)):
        return {"semantic_tools": ["get_ontology_context", "get_assertions", "compare_products"],
                "active_read_backend": "local_versioned_store", "warehouse_read_backend_connected": False,
                "warehouse_projection": "explicit allowlist; source-reference evidence labeled",
                "historical_ontology_reconstruction": False, "arbitrary_sql_allowed": False}

    return router
