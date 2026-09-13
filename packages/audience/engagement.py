from __future__ import annotations

from datetime import UTC, datetime
import os
from pathlib import Path
from uuid import uuid4

from pydantic import Field, model_validator

from packages.contracts.object import StrictContract
from packages.runtime.context import reject_obvious_credentials


class AudienceEvent(StrictContract):
    schema_version: str = "audience-event-2"
    event_id: str = Field(default_factory=lambda: "aud_" + uuid4().hex)
    event_type: str = Field(pattern=r"^(impression|like|dislike|comment|chat_question|outbound_intent)$")
    card_id: str | None = Field(default=None, min_length=3, max_length=128)
    content_id: str | None = Field(default=None, min_length=3, max_length=128)
    content_kind: str = Field(default="card", pattern=r"^(card|canonical_video)$")
    session_id: str = Field(pattern=r"^[A-Za-z0-9_-]{8,96}$")
    text: str | None = Field(default=None, max_length=1000)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    moderation_state: str = Field(pattern=r"^(not_applicable|pending)$")

    @model_validator(mode="after")
    def one_subject(self):
        if bool(self.card_id) == bool(self.content_id):
            raise ValueError("Exactly one card or canonical video subject is required.")
        if self.content_kind == "card" and not self.card_id:
            raise ValueError("Card events require card_id.")
        if self.content_kind == "canonical_video" and not self.content_id:
            raise ValueError("Canonical-video events require content_id.")
        return self


class LocalAudienceEventStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event):
        event = AudienceEvent.model_validate(event)
        reject_obvious_credentials(event.model_dump(mode="json"))
        descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.fchmod(descriptor, 0o600)
            os.write(descriptor, (event.model_dump_json() + "\n").encode())
        finally:
            os.close(descriptor)
        return event

    def recent(self, limit=100):
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()[-min(max(limit, 1), 200):]
        return [AudienceEvent.model_validate_json(line) for line in lines]
