from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.contracts import (
    ActorType, CurationPatch, LocalObjectStore, ObjectStatus, ReviewDecision,
    SourceReference, UniversalObject,
)
from packages.contracts.store import (
    ContractViolationError, DuplicateObjectError, InvalidTransitionError,
    ObjectNotFoundError, ObjectStoreError, PermissionDeniedError, VersionConflictError,
)
from packages.contracts.governance import PAYLOAD_TYPES
from packages.contracts.smart_glasses import (
    AudienceIntent, CommercialIntent, EvidenceTier, SmartGlassesObject,
    SmartGlassesObjectType, VerificationState,
)
from packages.contracts.workflows import WORKFLOWS, compose_brief
from services.api.src.body_limit import RequestBodyLimit
from services.api.src.workspace_planning import planning_router

app = FastAPI(title="SmartGlasses Intelligence", version="0.3.0",
              docs_url=None, redoc_url=None)
app.add_middleware(RequestBodyLimit, maximum=524288)
WEB_ROOT = PROJECT_ROOT / "apps" / "web"
PUBLIC_ROOT = PROJECT_ROOT / "apps" / "public"
app.mount("/assets", StaticFiles(directory=WEB_ROOT), name="assets")
app.mount("/discover-assets", StaticFiles(directory=PUBLIC_ROOT), name="discover-assets")


class ApiContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CaptureRequest(ApiContract):
    object_id: str | None = None
    object_type: str = Field(min_length=2, max_length=80)
    domain: str = "smart_glasses"
    title: str = Field(min_length=1, max_length=240)
    purpose: str = Field(min_length=1, max_length=1000)
    created_by: str | None = None
    source: list[str] = Field(default_factory=list, max_length=40)
    sources: list[SourceReference] = Field(default_factory=list, max_length=40)
    tags: list[str] = Field(default_factory=list, max_length=40)
    parent_ids: list[str] = Field(default_factory=list, max_length=40)
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    actor_id: str | None = None
    actor_type: ActorType | None = None


class CurationRequest(ApiContract):
    patch: CurationPatch
    expected_version: int = Field(ge=1)
    actor_id: str | None = None
    actor_type: ActorType | None = None


class ReviewRequest(ApiContract):
    decision: ReviewDecision
    expected_version: int = Field(ge=1)
    reviewer_id: str | None = None
    notes: str | None = Field(default=None, max_length=4000)


class LifecycleRequest(ApiContract):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=1000)


class BriefRequest(ApiContract):
    family: str
    product_ids: list[str] = Field(min_length=1, max_length=4)


@dataclass(frozen=True)
class Principal:
    actor_id: str
    actor_type: ActorType
    role: str
    mode: str
    email: str | None = None


_FIREBASE_TOKEN_CACHE = {}


def _admin_allowlist():
    import json
    path = Path(os.getenv("ADMIN_ALLOWLIST_PATH", str(PROJECT_ROOT / ".local/admin-allowlist.json"))).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    result = {}
    for item in data.get("admins", []):
        email = str(item.get("email", "")).strip().lower()
        role = item.get("role", "reviewer")
        if item.get("enabled", True) and email and role in {"editor", "reviewer"}:
            result[email] = role
    for email in os.getenv("ADMIN_EMAIL_ALLOWLIST", "").split(","):
        normalized = email.strip().lower()
        if normalized and "@" in normalized:
            result[normalized] = "reviewer"
    return result


def _firebase_principal(authorization):
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "A Firebase bearer token is required.")
    import base64
    import json
    import time
    from urllib.error import HTTPError, URLError
    from urllib.request import Request as UrlRequest, urlopen
    token = authorization[7:].strip()
    cached = _FIREBASE_TOKEN_CACHE.get(token)
    if cached and cached[0] > time.time() + 30:
        return cached[1]
    api_key = os.getenv("FIREBASE_WEB_API_KEY", "").strip()
    project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip()
    if not api_key or not project_id:
        raise HTTPException(503, "Firebase administrator authentication is not configured.")
    try:
        part = token.split(".")[1]
        payload = json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
        verification = UrlRequest(
            "https://identitytoolkit.googleapis.com/v1/accounts:lookup?key=" + api_key,
            data=json.dumps({"idToken": token}).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(verification, timeout=8) as response:
            verified = json.loads(response.read())
    except (IndexError, ValueError, HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        raise HTTPException(401, "Google identity verification failed.") from None
    users = verified.get("users", [])
    if len(users) != 1:
        raise HTTPException(401, "Google identity verification failed.")
    user = users[0]
    email = str(user.get("email", "")).strip().lower()
    issuer = "https://securetoken.google.com/" + project_id
    if payload.get("aud") != project_id or payload.get("iss") != issuer or user.get("emailVerified") not in {True, "true", "True"}:
        raise HTTPException(401, "A verified Google account from the configured Firebase project is required.")
    role = _admin_allowlist().get(email)
    if not role:
        raise HTTPException(403, "This verified Google account is not on the administrator allowlist.")
    uid = str(user.get("localId") or payload.get("sub") or "")
    if not uid:
        raise HTTPException(401, "The verified identity has no stable Firebase user ID.")
    principal = Principal("firebase:" + uid, ActorType.human, role, "firebase_google", email)
    expiry = min(float(payload.get("exp", time.time() + 60)), time.time() + 300)
    _FIREBASE_TOKEN_CACHE[token] = (expiry, principal)
    if len(_FIREBASE_TOKEN_CACHE) > 100:
        _FIREBASE_TOKEN_CACHE.clear()
        _FIREBASE_TOKEN_CACHE[token] = (expiry, principal)
    return principal


def get_store():
    if os.getenv("OBJECT_STORE_BACKEND", "local").lower() == "firestore":
        from packages.cloud.firestore_store import production_store
        return production_store()
    path = Path(os.getenv("OBJECT_STORE_PATH", str(PROJECT_ROOT / ".local/object-events.jsonl"))).expanduser()
    return LocalObjectStore(path if path.is_absolute() else PROJECT_ROOT / path)


def require_api_access(request: Request,
                       supplied_token: str | None = Header(None, alias="X-BS-CATS-Key"),
                       authorization: str | None = Header(None, alias="Authorization")):
    firebase_principal = _firebase_principal(authorization)
    if firebase_principal:
        return firebase_principal
    environment = os.getenv("ENVIRONMENT", "production").lower()
    profiles = [
        ("API_REVIEW_TOKEN", "reviewer", ActorType.human, os.getenv("API_OPERATOR_ID", "founder")),
        ("API_WRITE_TOKEN", "editor", ActorType.human, os.getenv("API_OPERATOR_ID", "founder")),
        ("API_AGENT_TOKEN", "editor", ActorType.agent, "research-agent"),
        ("API_READ_TOKEN", "reader", ActorType.system, "read-client"),
    ]
    configured = [(os.getenv(name, ""), role, kind, actor) for name, role, kind, actor in profiles if os.getenv(name)]
    if len({token for token, *_ in configured}) != len(configured):
        raise HTTPException(503, "Access roles require distinct credentials.")
    for token, role, kind, actor in configured:
        if supplied_token and hmac.compare_digest(supplied_token.encode(), token.encode()):
            return Principal(actor, kind, role, "token")
    if supplied_token:
        raise HTTPException(401, "Valid API credential required.")
    local = environment in {"dev", "local", "test"} and os.getenv("ALLOW_LOCAL_OPERATOR") == "1" and os.getenv("ADMIN_AUTH_REQUIRED") != "1"
    host = (request.url.hostname or "").lower()
    client = request.client.host if request.client else ""
    try:
        loopback = ipaddress.ip_address(client).is_loopback
    except ValueError:
        loopback = False
    if local and loopback and host in {"127.0.0.1", "localhost", "::1"}:
        return Principal("founder", ActorType.human, "reviewer", "local_operator")
    raise HTTPException(401 if configured else 503, "Configure scoped access or start the explicit local operator server.")


def can_edit(principal=Depends(require_api_access)):
    if principal.role not in {"editor", "reviewer"}:
        raise HTTPException(403, "Editing requires an editor role.")
    return principal


def can_review(principal=Depends(require_api_access)):
    if principal.role != "reviewer" or principal.actor_type != ActorType.human:
        raise HTTPException(403, "Human reviewer authority is required.")
    return principal


def identity_check(principal, actor_id=None, actor_type=None):
    if actor_id is not None and actor_id != principal.actor_id:
        raise HTTPException(403, "Actor identity comes from authentication.")
    if actor_type is not None and actor_type != principal.actor_type:
        raise HTTPException(403, "Actor type comes from authentication.")


@app.get("/v1/admin-auth/config")
def admin_auth_config():
    firebase = {"apiKey": os.getenv("FIREBASE_WEB_API_KEY", ""),
                "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN", ""),
                "projectId": os.getenv("FIREBASE_PROJECT_ID", ""),
                "appId": os.getenv("FIREBASE_WEB_APP_ID", "")}
    return {"provider": "firebase_google", "required": os.getenv("ADMIN_AUTH_REQUIRED") == "1",
            "configured": all(firebase.values()) and bool(_admin_allowlist()), "firebase": firebase}


@app.middleware("http")
async def browser_boundary(request: Request, call_next):
    allowed = set(os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost,::1,testserver").split(","))
    if request.url.hostname not in allowed:
        return JSONResponse({"detail": "Unrecognized host."}, status_code=400)
    if request.url.path.startswith("/v1"):
        if request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"detail": "Cross-site workspace access denied."}, status_code=403)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and origin != str(request.base_url).rstrip("/"):
                return JSONResponse({"detail": "Origin does not match this workspace."}, status_code=403)
            if request.headers.get("x-workspace-action") != "1":
                return JSONResponse({"detail": "Workspace action header required."}, status_code=403)
            try:
                size = int(request.headers.get("content-length", "0"))
            except ValueError:
                return JSONResponse({"detail": "Invalid request length."}, status_code=400)
            if size < 0:
                return JSONResponse({"detail": "Invalid request length."}, status_code=400)
            if size > 524288:
                return JSONResponse({"detail": "Request exceeds the workspace limit."}, status_code=413)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    )
    return response


@app.exception_handler(ObjectStoreError)
async def store_error(_request, exc):
    code = 404 if isinstance(exc, ObjectNotFoundError) else 409 if isinstance(
        exc, (DuplicateObjectError, InvalidTransitionError, VersionConflictError)) else 422 if isinstance(
        exc, ContractViolationError) else 403 if isinstance(exc, PermissionDeniedError) else 500
    return JSONResponse({"detail": str(exc) if code != 500 else "Object store failure."}, status_code=code)


@app.get("/")
def home():
    return FileResponse(WEB_ROOT / "index.html")


@app.get("/discover")
def discover():
    return FileResponse(PUBLIC_ROOT / "consumer.html")


@app.get("/health")
def health():
    return {"status": "healthy", "object_store": os.getenv("OBJECT_STORE_BACKEND", "local"), "version": "0.4.0"}


@app.get("/v1/session")
def session(principal=Depends(require_api_access)):
    return {"actor_id": principal.actor_id, "actor_type": principal.actor_type,
            "role": principal.role, "mode": principal.mode}


@app.get("/v1/schema")
def schema(_principal=Depends(require_api_access)):
    return {"fields": [f.model_dump(mode="json") for f in get_store().definitions().values()],
            "object_types": {name: model.model_json_schema() for name, model in PAYLOAD_TYPES.items()},
            "workflows": WORKFLOWS}


@app.get("/v1/objects")
def list_objects(object_type: str | None = None,
                 object_status: ObjectStatus | None = Query(None, alias="status"),
                 _principal=Depends(require_api_access)):
    return get_store().list_objects(object_type=object_type, status=object_status)


@app.post("/v1/objects", status_code=201)
def capture_object(body: CaptureRequest, principal=Depends(can_edit),
                   request_key: str | None = Header(None, alias="Idempotency-Key")):
    identity_check(principal, body.actor_id, body.actor_type)
    identity_check(principal, body.created_by)
    values = body.model_dump(exclude={"actor_id", "actor_type", "created_by"}, exclude_none=True)
    if request_key and not values.get("object_id"):
        values["object_id"] = "obj_" + uuid5(NAMESPACE_URL, principal.actor_id + ":" + request_key).hex
    item = UniversalObject(**values)
    return get_store().capture(item, actor_id=principal.actor_id, actor_type=principal.actor_type,
                               idempotency_key=request_key,
                               request_input=body.model_dump(mode="json", exclude_unset=True))


@app.get("/v1/objects/{object_id}")
def get_object(object_id: str, _principal=Depends(require_api_access)):
    return get_store().get(object_id)


@app.get("/v1/objects/{object_id}/history")
def history(object_id: str, _principal=Depends(require_api_access)):
    return get_store().history(object_id)


@app.post("/v1/objects/{object_id}/curate")
def curate(object_id: str, body: CurationRequest, principal=Depends(can_edit),
           request_key: str | None = Header(None, alias="Idempotency-Key")):
    identity_check(principal, body.actor_id, body.actor_type)
    return get_store().curate(object_id, body.patch, actor_id=principal.actor_id,
        actor_type=principal.actor_type, expected_version=body.expected_version, idempotency_key=request_key)


@app.post("/v1/objects/{object_id}/review")
def review(object_id: str, body: ReviewRequest, principal=Depends(can_review),
           request_key: str | None = Header(None, alias="Idempotency-Key")):
    identity_check(principal, body.reviewer_id)
    return get_store().review(object_id, body.decision, reviewer_id=principal.actor_id,
        actor_type=principal.actor_type, notes=body.notes,
        expected_version=body.expected_version, idempotency_key=request_key)


@app.post("/v1/objects/{object_id}/archive")
def archive_object(object_id: str, body: LifecycleRequest, principal=Depends(can_edit),
                   request_key: str | None = Header(None, alias="Idempotency-Key")):
    return get_store().archive(object_id, reason=body.reason, actor_id=principal.actor_id,
        actor_type=principal.actor_type, expected_version=body.expected_version,
        idempotency_key=request_key)


@app.post("/v1/objects/{object_id}/restore")
def restore_object(object_id: str, body: LifecycleRequest, principal=Depends(can_edit),
                   request_key: str | None = Header(None, alias="Idempotency-Key")):
    return get_store().restore(object_id, reason=body.reason, actor_id=principal.actor_id,
        actor_type=principal.actor_type, expected_version=body.expected_version,
        idempotency_key=request_key)


@app.post("/v1/validate/smart-glasses")
def validate(item: SmartGlassesObject, _principal=Depends(require_api_access)):
    return item


@app.get("/v1/taxonomy/smart-glasses")
def taxonomy(_principal=Depends(require_api_access)):
    return {"object_types": [v.value for v in SmartGlassesObjectType],
            "evidence_tiers": [v.value for v in EvidenceTier],
            "verification_states": [v.value for v in VerificationState],
            "audience_intents": [v.value for v in AudienceIntent],
            "commercial_intents": [v.value for v in CommercialIntent]}


@app.post("/v1/content/briefs", status_code=201)
def content_brief(body: BriefRequest, principal=Depends(can_edit),
                  request_key: str = Header(..., alias="Idempotency-Key")):
    store = get_store()
    products = [store.get(oid) for oid in body.product_ids]
    item = compose_brief(body.family, products, principal.actor_id, request_key, store.definitions())
    return store.capture(item, actor_id=principal.actor_id, actor_type=principal.actor_type,
                         idempotency_key=request_key,
                         request_input=body.model_dump(mode="json"))


@app.get("/v1/overview")
def overview(_principal=Depends(require_api_access)):
    items = get_store().list_objects()
    return {"objects": len(items), "products": sum(i.object_type == "product" for i in items),
            "review_pending": sum(i.review.required and i.status in {ObjectStatus.captured, ObjectStatus.proposed} for i in items),
            "fields": len(get_store().definitions()), "automatic_publication": False,
            "paid_work_enabled": False, "cloud_connected": False,
            "spend": {"owner_reported_subscription": 80, "currency": "USD",
                      "total_ceiling": 500, "other_costs": None, "reconciled": False}}


app.include_router(planning_router(get_store, require_api_access, can_edit))

from services.api.src.semantic_routes import semantic_router
app.include_router(semantic_router(get_store, require_api_access))
from services.api.src.operator_routes import operator_router
app.include_router(operator_router(get_store, require_api_access, can_edit))

from services.api.src.runtime_routes import runtime_router

app.include_router(runtime_router(require_api_access))

from services.api.src.intelligence_routes import intelligence_router

app.include_router(intelligence_router(get_store, require_api_access))

from services.api.src.media_routes import media_router

app.include_router(media_router(get_store, require_api_access))

from services.api.src.commerce_routes import commerce_router

app.include_router(commerce_router(get_store, require_api_access))

from services.api.src.release_routes import release_router

app.include_router(release_router(get_store, require_api_access))

from services.api.src.warehouse_routes import warehouse_router
app.include_router(warehouse_router(get_store, require_api_access))

from services.api.src.audience_routes import audience_router
app.include_router(audience_router(get_store, require_api_access, can_edit, PROJECT_ROOT))
