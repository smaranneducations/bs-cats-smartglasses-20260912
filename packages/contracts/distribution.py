from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .object import StrictContract

Destination = Literal["owned_app", "youtube", "linkedin", "instagram", "tiktok", "x"]
ContentShape = Literal[
    "one_product_one_attribute",
    "two_products_one_attribute",
    "one_news_event",
    "one_buyer_question",
]


class ChannelCopy(StrictContract):
    title: str | None = Field(default=None, max_length=240)
    text: str = Field(min_length=1, max_length=5000)
    tags: list[str] = Field(default_factory=list, max_length=30)
    disclosure: str = Field(min_length=1, max_length=1000)
    canonical_app_link: str = Field(min_length=1, max_length=500)


class DistributionPackagePayload(StrictContract):
    summary: str = Field(min_length=1, max_length=1200)
    render_artifact_id: str = Field(min_length=3, max_length=128)
    render_artifact_version: int = Field(ge=1)
    exact_video_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    poster_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    captions_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    self_hosted_asset_uri: str = Field(min_length=1, max_length=500)
    duration_seconds: float = Field(ge=29.9, le=90.1)
    aspect_ratio: Literal["9:16"] = "9:16"
    content_shape: ContentShape
    product_ids: list[str] = Field(default_factory=list, max_length=2)
    primary_concept_keys: list[str] = Field(min_length=1, max_length=1)
    destinations: list[Destination] = Field(min_length=1, max_length=6)
    channel_copy: dict[Destination, ChannelCopy]
    manual_kit_destinations: list[Literal["instagram", "tiktok", "x"]] = Field(default_factory=list)
    evidence_review_state: Literal["pending", "passed", "blocked"] = "pending"
    media_rights_state: Literal["pending", "passed", "blocked"] = "pending"
    publication_allowed: Literal[False] = False

    @model_validator(mode="after")
    def coherent_distribution(self):
        if len(set(self.destinations)) != len(self.destinations):
            raise ValueError("Distribution destinations must be distinct.")
        if set(self.channel_copy) != set(self.destinations):
            raise ValueError("Every destination requires exact pinned copy.")
        expected_manual = {destination for destination in self.destinations if destination in {"instagram", "tiktok", "x"}}
        if set(self.manual_kit_destinations) != expected_manual:
            raise ValueError("Manual posting kits must match the manual destinations.")
        if self.content_shape == "one_product_one_attribute" and len(self.product_ids) != 1:
            raise ValueError("One-product content requires exactly one product.")
        if self.content_shape == "two_products_one_attribute" and len(self.product_ids) != 2:
            raise ValueError("A comparison requires exactly two products.")
        if self.content_shape in {"one_news_event", "one_buyer_question"} and len(self.product_ids) > 2:
            raise ValueError("Atomic content cannot exceed two products.")
        return self


class PublicationRequestPayload(StrictContract):
    summary: str = Field(min_length=1, max_length=1200)
    distribution_package_id: str = Field(min_length=3, max_length=128)
    distribution_package_version: int = Field(ge=1)
    exact_package_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    destinations: list[Destination] = Field(min_length=1, max_length=6)
    requested_actions: list[str] = Field(min_length=1, max_length=12)
    human_review_required: Literal[True] = True
    review_category: Literal["publication"] = "publication"
    review_reason: str = Field(
        default="Authorize only the exact canonical video, copy, disclosures and destinations in this package.",
        min_length=1,
        max_length=1000,
    )
    execution_enabled: Literal[False] = False
