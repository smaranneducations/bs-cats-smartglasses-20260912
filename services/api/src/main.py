from __future__ import annotations

import hmac
import os
import sys
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.contracts import (  # noqa: E402
    ActorType,
    CurationPatch,
    DuplicateObjectError,
    InvalidTransitionError,
    LocalObjectStore,
    ObjectNotFoundError,
    ObjectRecord,
    ObjectStatus,
    ObjectStoreError,
    ReviewDecision,
    SourceReference,
    UniversalObject,
)
from packages.contracts.smart_glasses import (  # noqa: E402
    AudienceIntent,
    CommercialIntent,
    EvidenceTier,
    SmartGlassesObject,
    SmartGlassesObjectType,
    VerificationState,
)


class ApiContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CaptureRequest(ApiContract):
    object_id: str | None = None
    object_type: str = Field(..., min_length=2, max_length=80)
    domain: str = "smart_glasses"
    title: str = Field(..., min_length=1, max_length=240)
    purpose: str = Field(..., min_length=1, max_length=1000)
    created_by: str = "founder"
    source: list[str] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    parent_ids: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    actor_id: str = "founder"
    actor_type: ActorType = ActorType.human

    def to_object(self) -> UniversalObject:
        values = self.model_dump(
            exclude={"actor_id", "actor_type"},
            exclude_none=True,
        )
        return UniversalObject(**values)


class CurationRequest(ApiContract):
    patch: CurationPatch
    actor_id: str = "curation-agent"
    actor_type: ActorType = ActorType.agent


class ReviewRequest(ApiContract):
    decision: ReviewDecision
    reviewer_id: str = "founder"
    notes: str | None = None


app = FastAPI(
    title="BS CATS Smart Glasses API",
    version="0.2.0",
    description="Human-gated capture and curation API for SmartGlasses domain objects.",
)


def get_store() -> LocalObjectStore:
    configured_path = Path(
        os.getenv("OBJECT_STORE_PATH", ".local/object-events.jsonl")
    ).expanduser()
    if not configured_path.is_absolute():
        configured_path = PROJECT_ROOT / configured_path
    return LocalObjectStore(configured_path)


def require_api_access(
    supplied_token: str | None = Header(default=None, alias="X-BS-CATS-Key"),
) -> None:
    environment = os.getenv("ENVIRONMENT", "dev").lower()
    expected_token = os.getenv("API_WRITE_TOKEN", "")
    if environment in {"dev", "local", "test"} and not expected_token:
        return
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API access token is not configured.",
        )
    if supplied_token is None or not hmac.compare_digest(supplied_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid API access token required.",
        )


@app.exception_handler(ObjectNotFoundError)
async def object_not_found_handler(
    _request: Request, exc: ObjectNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(DuplicateObjectError)
async def duplicate_object_handler(
    _request: Request, exc: DuplicateObjectError
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(InvalidTransitionError)
async def invalid_transition_handler(
    _request: Request, exc: InvalidTransitionError
) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(ObjectStoreError)
async def object_store_handler(
    _request: Request, _exc: ObjectStoreError
) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Object store failure."})


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "bs-cats-smart-glasses-api", "status": "ok", "version": "0.2.0"}


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "healthy",
        "environment": os.getenv("ENVIRONMENT", "dev"),
        "project_id": os.getenv("GCP_PROJECT_ID", ""),
        "object_store": "local",
    }


@app.post(
    "/v1/objects",
    response_model=UniversalObject,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_access)],
)
def capture_object(request: CaptureRequest) -> UniversalObject:
    return get_store().capture(
        request.to_object(),
        actor_id=request.actor_id,
        actor_type=request.actor_type,
    )


@app.get(
    "/v1/objects",
    response_model=list[UniversalObject],
    dependencies=[Depends(require_api_access)],
)
def list_objects(
    object_type: str | None = Query(default=None),
    object_status: ObjectStatus | None = Query(default=None, alias="status"),
) -> list[UniversalObject]:
    return get_store().list_objects(object_type=object_type, status=object_status)


@app.get(
    "/v1/objects/{object_id}",
    response_model=UniversalObject,
    dependencies=[Depends(require_api_access)],
)
def get_object(object_id: str) -> UniversalObject:
    return get_store().get(object_id)


@app.get(
    "/v1/objects/{object_id}/history",
    response_model=list[ObjectRecord],
    dependencies=[Depends(require_api_access)],
)
def get_object_history(object_id: str) -> list[ObjectRecord]:
    return get_store().history(object_id)


@app.post(
    "/v1/objects/{object_id}/curate",
    response_model=UniversalObject,
    dependencies=[Depends(require_api_access)],
)
def curate_object(object_id: str, request: CurationRequest) -> UniversalObject:
    return get_store().curate(
        object_id,
        request.patch,
        actor_id=request.actor_id,
        actor_type=request.actor_type,
    )


@app.post(
    "/v1/objects/{object_id}/review",
    response_model=UniversalObject,
    dependencies=[Depends(require_api_access)],
)
def review_object(object_id: str, request: ReviewRequest) -> UniversalObject:
    return get_store().review(
        object_id,
        request.decision,
        reviewer_id=request.reviewer_id,
        notes=request.notes,
    )


@app.post(
    "/v1/validate/smart-glasses",
    response_model=SmartGlassesObject,
    dependencies=[Depends(require_api_access)],
)
def validate_smart_glasses_object(item: SmartGlassesObject) -> SmartGlassesObject:
    return item


@app.get(
    "/v1/taxonomy/smart-glasses",
    dependencies=[Depends(require_api_access)],
)
def smart_glasses_taxonomy() -> dict[str, list[str]]:
    return {
        "object_types": [item.value for item in SmartGlassesObjectType],
        "evidence_tiers": [item.value for item in EvidenceTier],
        "verification_states": [item.value for item in VerificationState],
        "audience_intents": [item.value for item in AudienceIntent],
        "commercial_intents": [item.value for item in CommercialIntent],
    }
