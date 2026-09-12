from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Self

from pydantic import Field, model_validator

from .object import StrictContract, utc_now


class VideoFormat(str, Enum):
    youtube_long = "youtube_long"
    youtube_short = "youtube_short"
    linkedin_native = "linkedin_native"


class VideoScene(StrictContract):
    scene_id: str = Field(..., min_length=3, max_length=128)
    duration_seconds: int = Field(..., ge=3, le=300)
    narration: str = Field(..., min_length=1, max_length=5000)
    visual_direction: str = Field(..., min_length=1, max_length=2000)
    on_screen_text: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)


class VideoScript(StrictContract):
    script_version: Literal["1.0"] = "1.0"
    script_id: str = Field(..., min_length=3, max_length=128)
    brief_object_id: str = Field(..., min_length=3, max_length=128)
    working_title: str = Field(..., min_length=1, max_length=240)
    thumbnail_text: str = Field(..., min_length=1, max_length=80)
    video_format: VideoFormat = VideoFormat.youtube_long
    language: str = "en"
    target_duration_seconds: int = Field(..., ge=15, le=3600)
    description: str = Field(..., min_length=1, max_length=5000)
    disclosure: str = Field(..., min_length=1, max_length=1000)
    scenes: list[VideoScene] = Field(..., min_length=1)
    keywords: list[str] = Field(default_factory=list)
    editorial_notes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def enforce_timeline(self) -> Self:
        scene_ids = [scene.scene_id for scene in self.scenes]
        if len(scene_ids) != len(set(scene_ids)):
            raise ValueError("video scene IDs must be unique")
        timeline_seconds = sum(scene.duration_seconds for scene in self.scenes)
        if timeline_seconds != self.target_duration_seconds:
            raise ValueError(
                "target_duration_seconds must equal the sum of scene durations"
            )
        return self
