from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .object import StrictContract
from .smart_glasses import EvidenceClaim


class ContentCardPayload(StrictContract):
    summary: str = Field(min_length=1, max_length=1200)
    product_id: str = Field(min_length=3, max_length=128)
    product_version: int = Field(ge=1)
    theme: str = Field(min_length=2, max_length=80)
    hook: str = Field(min_length=1, max_length=240)
    practical_impact: str = Field(min_length=1, max_length=1000)
    field_keys: list[str] = Field(min_length=1, max_length=1)
    claims: list[EvidenceClaim] = Field(min_length=1, max_length=1)
    source_ids: list[str] = Field(min_length=1, max_length=12)
    media_asset_ids: list[str] = Field(default_factory=list, max_length=3)
    visual_mode: Literal["original_graphic", "authorized_product_media"] = "original_graphic"
    channel_targets: list[Literal["web_feed", "youtube_shorts"]] = Field(
        default_factory=lambda: ["web_feed", "youtube_shorts"], min_length=1, max_length=2
    )
    publication_allowed: Literal[False] = False

    @model_validator(mode="after")
    def coherent_card(self):
        if len(set(self.field_keys)) != len(self.field_keys):
            raise ValueError("Card fields must be distinct.")
        if len({claim.claim_id for claim in self.claims}) != len(self.claims):
            raise ValueError("Card claims must be distinct.")
        if len(self.claims) != len(self.field_keys):
            raise ValueError("Each card field requires one exact claim.")
        if set(self.source_ids) != {source_id for claim in self.claims for source_id in claim.source_ids}:
            raise ValueError("Card sources must equal the sources used by its claims.")
        return self


class CardBundlePayload(StrictContract):
    summary: str = Field(min_length=1, max_length=1200)
    product_versions: dict[str, int] = Field(min_length=1, max_length=4)
    card_versions: dict[str, int] = Field(min_length=1, max_length=12)
    themes: list[str] = Field(min_length=1, max_length=12)
    generation_policy: Literal["semantic-card-composer-1"] = "semantic-card-composer-1"
    duplicate_policy: Literal["exact-field-set-and-theme"] = "exact-field-set-and-theme"
    publication_allowed: Literal[False] = False


class ShortCardScene(StrictContract):
    scene_id: str = Field(pattern=r"^scene_[0-9]{2}$")
    card_id: str = Field(min_length=3, max_length=128)
    card_version: int = Field(ge=1)
    duration_seconds: float = Field(ge=3, le=15)


class ShortsPlanPayload(StrictContract):
    summary: str = Field(min_length=1, max_length=1200)
    card_bundle_id: str = Field(min_length=3, max_length=128)
    card_bundle_version: int = Field(ge=1)
    card_versions: dict[str, int] = Field(min_length=1, max_length=8)
    duration_seconds: float = Field(ge=30, le=90)
    aspect_ratio: Literal["9:16"] = "9:16"
    scenes: list[ShortCardScene] = Field(min_length=3, max_length=8)
    motion_profile: Literal["kinetic-card-sequence-1"] = "kinetic-card-sequence-1"
    soundtrack: Literal["original_or_licensed"] = "original_or_licensed"
    narration: Literal["none"] = "none"
    render_state: Literal["preview_only"] = "preview_only"
    publication_allowed: Literal[False] = False

    @model_validator(mode="after")
    def complete_sequence(self):
        if len({scene.scene_id for scene in self.scenes}) != len(self.scenes):
            raise ValueError("Short scene identifiers must be distinct.")
        if {scene.card_id: scene.card_version for scene in self.scenes} != self.card_versions:
            raise ValueError("Short scenes must match the pinned card versions exactly.")
        if abs(sum(scene.duration_seconds for scene in self.scenes) - self.duration_seconds) > 0.001:
            raise ValueError("Short scene timing must equal the requested duration.")
        return self
