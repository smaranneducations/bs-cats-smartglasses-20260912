from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ObjectStatus(str, Enum):
    draft = "draft"
    proposed = "proposed"
    active = "active"
    deprecated = "deprecated"
    rejected = "rejected"
    archived = "archived"


class UniversalObject(BaseModel):
    object_id: str = Field(..., description="Stable object identifier")
    object_type: str
    title: str
    purpose: str
    status: ObjectStatus = ObjectStatus.draft
    version: int = 1
    valid_from: str | None = None
    valid_to: str | None = None
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str | None = None
    source: list[str] = Field(default_factory=list)
    confidence: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
