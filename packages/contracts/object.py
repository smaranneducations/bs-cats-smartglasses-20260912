from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


CONTRACT_VERSION = "1.0"


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_identifier(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ObjectStatus(str, Enum):
    draft = "draft"
    captured = "captured"
    proposed = "proposed"
    active = "active"
    published = "published"
    deprecated = "deprecated"
    rejected = "rejected"
    archived = "archived"


class ReviewState(str, Enum):
    pending = "pending"
    approved = "approved"
    changes_requested = "changes_requested"
    rejected = "rejected"


class ReviewDecision(str, Enum):
    approved = "approved"
    changes_requested = "changes_requested"
    rejected = "rejected"


class ActorType(str, Enum):
    human = "human"
    agent = "agent"
    system = "system"


class ObjectEventType(str, Enum):
    captured = "captured"
    curated = "curated"
    reviewed = "reviewed"


class SourceReference(StrictContract):
    source_id: str = Field(default_factory=lambda: new_identifier("src"))
    uri: str = Field(..., min_length=1)
    title: str | None = None
    publisher: str | None = None
    published_at: datetime | None = None
    captured_at: datetime = Field(default_factory=utc_now)
    notes: str | None = None


class HumanReview(StrictContract):
    required: bool = True
    state: ReviewState = ReviewState.pending
    requested_at: datetime = Field(default_factory=utc_now)
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    notes: str | None = None


class UniversalObject(StrictContract):
    contract_version: Literal["1.0"] = CONTRACT_VERSION
    object_id: str = Field(default_factory=lambda: new_identifier("obj"), min_length=3, max_length=128)
    object_type: str = Field(..., min_length=2, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    domain: str = Field(default="smart_glasses", min_length=2, max_length=80)
    title: str = Field(..., min_length=1, max_length=240)
    purpose: str = Field(..., min_length=1, max_length=1000)
    status: ObjectStatus = ObjectStatus.captured
    version: int = Field(default=1, ge=1)
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    recorded_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    created_by: str = "founder"
    source: list[str] = Field(
        default_factory=list,
        description="Backward-compatible source URI list; prefer structured sources.",
    )
    sources: list[SourceReference] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)
    tags: list[str] = Field(default_factory=list)
    parent_ids: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    review: HumanReview = Field(default_factory=HumanReview)


class CurationPatch(StrictContract):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    purpose: str | None = Field(default=None, min_length=1, max_length=1000)
    confidence: float | None = Field(default=None, ge=0, le=1)
    tags: list[str] | None = None
    payload: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class ObjectEvent(StrictContract):
    contract_version: Literal["1.0"] = CONTRACT_VERSION
    event_id: str = Field(default_factory=lambda: new_identifier("evt"))
    event_type: ObjectEventType
    object_id: str
    object_version: int = Field(..., ge=1)
    sequence: int = Field(..., ge=1)
    actor_type: ActorType
    actor_id: str = Field(..., min_length=1)
    occurred_at: datetime = Field(default_factory=utc_now)
    data: dict[str, Any] = Field(default_factory=dict)


class ObjectRecord(StrictContract):
    event: ObjectEvent
    snapshot: UniversalObject
