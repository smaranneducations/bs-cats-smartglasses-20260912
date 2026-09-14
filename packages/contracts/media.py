from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .object import StrictContract

Primitive = Literal["question_hook", "product_card", "feature_callout", "comparison_table", "decision_map", "metric_card", "timeline", "compatibility_chain", "question_reveal", "evidence_note", "uncertainty_card", "takeaway"]


class MediaAssetPayload(StrictContract):
    summary: str = Field(min_length=1, max_length=2000)
    asset_kind: Literal["image", "font", "procedural_audio"]
    asset_uri: str = Field(min_length=1, max_length=500)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    provenance_kind: Literal["legacy_workspace", "open_license", "generated_recipe"]
    provenance_reference: str = Field(min_length=1, max_length=1000)
    representation: Literal["concept_illustration", "typography", "original_synthesis", "product_photography", "editorial_photography"]
    private_preview_allowed: bool = False
    rights_state: Literal["unassessed", "documented", "denied"] = "unassessed"
    commercial_use_allowed: bool | None = None
    credit: str = Field(min_length=1, max_length=1500)

    @model_validator(mode="after")
    def truthful_photography_representation(self):
        if self.representation in {"product_photography", "editorial_photography"}:
            if self.asset_kind != "image":
                raise ValueError("Photography representation requires an image asset.")
            if self.provenance_kind == "generated_recipe":
                raise ValueError("Generated imagery cannot be represented as photography.")
        return self


class RenderCell(StrictContract):
    claim_id: str
    object_id: str
    product_title: str = Field(min_length=1, max_length=240)
    concept_key: str
    concept_label: str
    value_display: str = Field(min_length=1, max_length=200)
    source_statement: str = Field(min_length=1, max_length=1500)
    source_ids: list[str] = Field(min_length=1, max_length=12)


class ImageBeat(StrictContract):
    beat_id: str
    source_scene_id: str
    primitive: Primitive
    heading: str = Field(min_length=1, max_length=240)
    lines: list[str] = Field(min_length=1, max_length=4)
    notes: list[str] = Field(default_factory=list, max_length=20)
    claim_cells: list[RenderCell] = Field(default_factory=list, max_length=4)
    duration_seconds: float = Field(ge=2, le=12)
    image_asset_id: str
    crop: tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)
    accent: Literal["orange", "mint", "cyan", "amber"]

    @model_validator(mode="after")
    def valid_frame(self):
        left, top, right, bottom = self.crop
        if not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
            raise ValueError("The image crop must remain inside its source.")
        if any(not line.strip() or len(line) > 1000 for line in self.lines):
            raise ValueError("Beat text must be nonempty and bounded.")
        if self.primitive == "comparison_table" and len(self.claim_cells) != 2:
            raise ValueError("A paired comparison needs exactly two source-linked cells.")
        return self


class RenderRecipePayload(StrictContract):
    summary: str
    recipe_version: Literal["image-kinetic-1"] = "image-kinetic-1"
    storyboard_object_id: str
    storyboard_version: int = Field(ge=1)
    workflow_family: str
    aspect_ratio: Literal["9:16"]
    duration_seconds: float = Field(ge=30, le=90)
    creative_profile_revision: int = Field(ge=1)
    creative_profile_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    ontology_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    renderer_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_versions: dict[str, int] = Field(min_length=1, max_length=60)
    creative_settings: dict
    governed_memory: dict
    assets: dict[str, MediaAssetPayload] = Field(min_length=4, max_length=12)
    beats: list[ImageBeat] = Field(min_length=5, max_length=40)
    soundtrack_asset_id: str
    display_font_asset_id: str
    body_font_asset_id: str
    media_mode: Literal["image_led_private_preview"] = "image_led_private_preview"
    adaptation_reason: str = Field(min_length=1, max_length=1000)
    publication_allowed: Literal[False] = False

    @model_validator(mode="after")
    def complete_recipe(self):
        if abs(sum(beat.duration_seconds for beat in self.beats) - self.duration_seconds) > 0.001:
            raise ValueError("Beat timing must equal the complete video duration.")
        if len({beat.beat_id for beat in self.beats}) != len(self.beats):
            raise ValueError("Beat IDs must be distinct.")
        for beat in self.beats:
            if beat.image_asset_id not in self.assets or self.assets[beat.image_asset_id].asset_kind != "image":
                raise ValueError("Each beat requires a registered image asset.")
        required = [(self.soundtrack_asset_id, "procedural_audio"), (self.display_font_asset_id, "font"), (self.body_font_asset_id, "font")]
        if any(key not in self.assets or self.assets[key].asset_kind != kind for key, kind in required):
            raise ValueError("Music and typography assets must be registered explicitly.")
        return self


class RenderArtifactPayload(StrictContract):
    summary: str
    recipe_object_id: str
    recipe_version: int = Field(ge=1)
    artifact_uri: str
    poster_uri: str
    manifest_uri: str
    video_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    metadata_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    publish_metadata: dict
    duration_seconds: float = Field(ge=29.9, le=90.1)
    width: int = Field(ge=200, le=3840)
    height: int = Field(ge=200, le=3840)
    audio_present: Literal[True] = True
    media_mode: Literal["image_led_private_preview"] = "image_led_private_preview"
    rights_gate: Literal["not_cleared_for_publication"] = "not_cleared_for_publication"
    factual_gate: Literal["requires_review"] = "requires_review"
    publication_allowed: Literal[False] = False
