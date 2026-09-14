from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
from hashlib import sha256
import os
from pathlib import Path
import time

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from packages.audience.composer import compose_audience_package
from packages.audience.engagement import LocalAudienceEventStore
from packages.contracts.audience import ContentCardPayload
from packages.contracts.store import ObjectNotFoundError


class RequestContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ComposeRequest(RequestContract):
    product_id: str = Field(min_length=3, max_length=128)
    max_cards: int = Field(default=6, ge=3, le=12)
    short_duration_seconds: int = Field(default=60, ge=30, le=90)


class EngagementRequest(RequestContract):
    event_type: str = Field(pattern=r"^(impression|like|dislike|comment|chat_question|outbound_intent)$")
    card_id: str | None = Field(default=None, min_length=3, max_length=128)
    content_id: str | None = Field(default=None, min_length=3, max_length=128)
    session_id: str = Field(pattern=r"^[A-Za-z0-9_-]{8,96}$")
    text: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def one_subject(self):
        if bool(self.card_id) == bool(self.content_id):
            raise ValueError("Exactly one card or canonical video subject is required.")
        return self


RATE = defaultdict(deque)


def audience_router(get_store, require_access, can_edit, root):
    router = APIRouter(tags=["audience"])
    event_store = LocalAudienceEventStore(Path(root) / ".local" / "audience-events.jsonl")

    def card_view(card):
        current = dict(card.payload)
        if len(current.get("field_keys", [])) > 1 or len(current.get("claims", [])) > 1:
            current["field_keys"] = current.get("field_keys", [])[:1]
            current["claims"] = current.get("claims", [])[:1]
            current["source_ids"] = sorted({source_id for claim in current["claims"]
                                             for source_id in claim.get("source_ids", [])})
        payload = ContentCardPayload.model_validate(current)
        return {"object_id": card.object_id, "version": card.version, "title": card.title,
            "status": card.status.value, "theme": payload.theme, "hook": payload.hook,
            "practical_impact": payload.practical_impact, "field_keys": payload.field_keys,
            "claims": [claim.model_dump(mode="json") for claim in payload.claims],
            "sources": [{"source_id": source.source_id, "title": source.title,
                "publisher": source.publisher, "uri": source.uri} for source in card.sources],
            "visual_mode": payload.visual_mode,
            "legacy_atomic_projection": current != card.payload}

    def retain(store, item, principal, request_key):
        try:
            return store.get(item.object_id)
        except ObjectNotFoundError:
            key = sha256((request_key + ":" + item.object_id).encode()).hexdigest()
            return store.capture(item, actor_id=principal.actor_id, actor_type=principal.actor_type,
                idempotency_key=key)

    @router.post("/v1/audience/compose", status_code=201)
    def compose(body: ComposeRequest, principal=Depends(can_edit),
                request_key: str = Header(..., alias="Idempotency-Key")):
        store = get_store()
        product = store.get(body.product_id)
        cards, bundle, plan = compose_audience_package(store, product, body.max_cards, body.short_duration_seconds)
        cards = [retain(store, card, principal, request_key) for card in cards]
        bundle = retain(store, bundle, principal, request_key)
        plan = retain(store, plan, principal, request_key)
        return {"cards": [card.object_id for card in cards], "bundle_id": bundle.object_id,
            "shorts_plan_id": plan.object_id, "preview_url": "/discover?preview=1",
            "publication_allowed": False}

    @router.get("/v1/audience/preview", dependencies=[Depends(require_access)])
    def preview():
        cards = [item for item in get_store().list_objects() if item.object_type == "content_card"
                 and item.status.value not in {"rejected", "archived", "deprecated"}]
        return {"mode": "private_preview", "cards": [card_view(card) for card in cards],
            "publication_allowed": False}

    @router.get("/v1/public/feed")
    def public_feed():
        from packages.audience.public_evidence import published_cards
        return {"mode": "public", "cards": published_cards(get_store(), card_view)}

    @router.get("/v1/public/videos")
    def public_videos():
        media_root = Path(root) / "apps" / "public" / "media"
        videos = []
        for path in sorted(media_root.glob("*.json"), key=lambda item: item.stat().st_mtime_ns, reverse=True)[:100]:
            try:
                value = __import__("json").loads(path.read_text(encoding="utf-8"))
                if value.get("schema_version") == "canonical-video-public-1" and value.get("publication_state") == "published":
                    videos.append(value)
            except (OSError, ValueError, TypeError):
                continue
        return {"mode": "public", "videos": videos}

    @router.post("/v1/public/events", status_code=202)
    def engagement(body: EngagementRequest, request: Request):
        local = os.getenv("ENVIRONMENT", "production").lower() in {"local", "dev", "test"}
        if not local and os.getenv("PUBLIC_ENGAGEMENT_ENABLED") != "1":
            raise HTTPException(503, "Public engagement storage is not activated.")
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        bucket = RATE[client]
        while bucket and bucket[0] < now - 60:
            bucket.popleft()
        if len(bucket) >= 30:
            raise HTTPException(429, "Engagement rate limit reached.")
        bucket.append(now)
        subject_id = body.content_id or body.card_id
        try:
            subject = get_store().get(subject_id)
        except ObjectNotFoundError:
            raise HTTPException(404, "Content not found.") from None
        expected_type = "distribution_package" if body.content_id else "content_card"
        if subject.object_type != expected_type or (not local and expected_type == "content_card" and subject.status.value != "published"):
            raise HTTPException(404, "Content not found.")
        if body.event_type in {"comment", "chat_question"} and not (body.text or "").strip():
            raise HTTPException(422, "Text is required for this interaction.")
        event = event_store.append(body.model_dump() | {
            "content_kind": "canonical_video" if body.content_id else "card",
            "moderation_state": "pending" if body.event_type in {"comment", "chat_question"} else "not_applicable",
            "recorded_at": datetime.now(timezone.utc)})
        response = {"event_id": event.event_id, "accepted": True,
            "moderation_state": event.moderation_state}
        if body.event_type == "chat_question":
            claim = subject.payload.get("claims", [{}])[0].get("statement", subject.payload.get("summary", "This content has no answerable claim."))
            response["answer"] = claim + " Open the evidence links for conditions and source context."
        return response

    @router.get("/v1/audience/events", dependencies=[Depends(require_access)])
    def events():
        return {"events": [event.model_dump(mode="json") for event in event_store.recent()]}

    return router
