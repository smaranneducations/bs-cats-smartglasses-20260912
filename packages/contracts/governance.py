from __future__ import annotations

import ipaddress
from datetime import datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator

from .content import VideoScript
from .production import RefreshJobPayload, StoryboardPayload
from .object import ObjectStatus, StrictContract, UniversalObject
from .smart_glasses import SmartGlassesObject, SmartGlassesObjectType, SmartGlassesPayload


def safe_source_uri(uri: str) -> str:
    parts = urlsplit(uri)
    if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
        raise ValueError("Sources require an HTTP(S) URL without credentials.")
    host = parts.hostname.lower().rstrip(".")
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("Private source addresses are not allowed.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError("Private source addresses are not allowed.")
    return uri


class FieldDefinition(StrictContract):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    label: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=800)
    value_type: Literal["number", "text", "boolean"]
    unit: str | None = Field(default=None, max_length=30)
    category: Literal["all", "display", "camera_audio", "ar"] = "all"
    minimum: float | None = None
    maximum: float | None = None


def _field(key, label, kind, unit, description, category="all"):
    return FieldDefinition(key=key, label=label, value_type=kind, unit=unit,
        description=description, category=category, minimum=0 if kind == "number" else None)


BASE_FIELDS = [
    _field("weight_g", "Weight", "number", "g", "Stated mass; specify frame and included parts."),
    _field("display_type", "Display technology", "text", None, "Panel/optical technology, not visual quality.", "display"),
    _field("resolution", "Resolution per eye", "text", None, "Pixel dimensions per eye and mode.", "display"),
    _field("fov_deg", "Field of view", "number", "degrees", "Stated FOV; axis/methodology may be unspecified.", "display"),
    _field("refresh_hz", "Maximum refresh rate", "number", "Hz", "Record resolution and 2D/3D conditions.", "display"),
    _field("brightness_nits", "Claimed brightness", "number", "nits", "Measurement methods may differ.", "display"),
    _field("ipd_fit", "IPD fitting range", "text", None, "Frame-size or software-dependent fit.", "display"),
    _field("tracking", "Screen tracking", "text", None, "Degrees of freedom and required accessories.", "display"),
    _field("dimming", "Lens dimming", "text", None, "Dimming levels and control method.", "display"),
    _field("connection", "Connection", "text", None, "Port and required video-output capability."),
    _field("camera_mp", "Camera resolution", "number", "MP", "Pixel count is not image quality.", "camera_audio"),
    _field("video_modes", "Video modes", "text", None, "Resolution, frame rate and duration conditions.", "camera_audio"),
    _field("battery_hours", "Claimed battery life", "number", "hours", "Use case and conditions affect comparability.", "camera_audio"),
    _field("charging_case", "Charging case", "text", None, "Included hardware and extra charge capacity.", "camera_audio"),
    _field("audio", "Audio", "text", None, "Speaker configuration and accessory dependencies."),
    _field("microphones", "Microphones", "number", "count", "Documented microphone count."),
    _field("prescription", "Prescription option", "text", None, "Supported inserts/lenses and extra purchases."),
    _field("water_resistance", "Water resistance", "text", None, "Exact published rating and limitations."),
    _field("phone_support", "Phone support", "text", None, "Platform/version and adapter requirements."),
    _field("pc_support", "Computer support", "text", None, "Display output and software requirements."),
    _field("ai_features", "AI features", "text", None, "Country, language and update dependencies.", "camera_audio"),
    _field("offline_features", "Offline use", "text", None, "Functionality without an internet connection."),
    _field("monthly_subscription", "Recurring subscription", "text", None, "Whether core or optional functions require a recurring payment; record plan, market and observation date."),
    _field("app_ecosystem", "App ecosystem", "text", None, "First-party app store, companion application or supported software catalogue, including device and market constraints."),
    _field("privacy_indicator", "Recording indicator", "text", None, "Documented indicator and behavior.", "camera_audio"),
    _field("warranty", "Warranty", "text", None, "Seller/country-specific terms."),
    _field("included_accessories", "Included accessories", "text", None, "Contents of the cited regional package."),
]
BASE_FIELD_MAP = {item.key: item for item in BASE_FIELDS}


class EvidenceValue(StrictContract):
    value: str | int | float | bool | None = None
    source_ids: list[str] = Field(default_factory=list, max_length=12)
    evidence_kind: Literal["manufacturer_stated", "independent_test", "human_observation", "inference"] = "manufacturer_stated"
    conditions: str = Field(default="", max_length=1000)
    observed_at: datetime
    confidence: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def needs_evidence(self):
        if self.observed_at.tzinfo is None:
            raise ValueError("Observation dates require a timezone.")
        if self.value is not None and not self.source_ids:
            raise ValueError("A known field value requires a structured source.")
        return self


class ProductPayload(StrictContract):
    summary: str = Field(min_length=1, max_length=4000)
    brand: str = Field(min_length=1, max_length=120)
    category: Literal["display", "camera_audio", "ar"]
    market: str = Field(min_length=1, max_length=160)
    variant: str = Field(min_length=1, max_length=240)
    buyer_job: str = Field(min_length=1, max_length=1000)
    fields: dict[str, EvidenceValue] = Field(default_factory=dict, max_length=60)
    caveats: list[str] = Field(default_factory=list, max_length=20)


class ObservationPayload(StrictContract):
    raw_note: str = Field(default="", max_length=4000)
    summary: str = Field(default="", max_length=4000)


class SourcePolicyPayload(StrictContract):
    summary: str = Field(min_length=1, max_length=2000)
    source_uri: str
    publisher: str = Field(min_length=1, max_length=200)
    access: Literal["manual_excerpt", "api", "licensed_feed"]
    automation: Literal["pending", "allowed", "denied"] = "pending"
    media_reuse: Literal["pending", "allowed", "denied"] = "pending"
    commercial_reuse: Literal["pending", "allowed", "denied"] = "pending"
    rights_basis: str = Field(min_length=1, max_length=2000)
    attribution: str = Field(min_length=1, max_length=1000)
    refresh_days: int = Field(default=30, ge=1, le=365)
    last_observed_at: datetime
    terms_uri: str | None = None
    permission_expires_at: datetime | None = None

    @model_validator(mode="after")
    def bounded_permission(self):
        if self.last_observed_at.tzinfo is None:
            raise ValueError("Source observations require a timezone.")
        if self.permission_expires_at is not None and self.permission_expires_at.tzinfo is None:
            raise ValueError("Permission expiry requires a timezone.")
        if self.automation == "allowed" and (not self.terms_uri or not self.permission_expires_at):
            raise ValueError("An automation permission proposal needs terms evidence and a review expiry.")
        return self


class CommercePathPayload(StrictContract):
    summary: str = Field(min_length=1, max_length=2000)
    merchant_uri: str
    program_uri: str | None = None
    customer_market: str = Field(min_length=1, max_length=200)
    checkout: Literal["observed", "unknown"] = "unknown"
    publisher_access: Literal["unknown", "not_applied", "invitation_required", "applied", "approved", "rejected"] = "unknown"
    purchase_friction: list[str] = Field(default_factory=list, max_length=20)
    obligations: list[str] = Field(default_factory=list, max_length=20)
    attribution_terms: str = Field(default="Unknown", max_length=2000)
    payment_terms: str = Field(default="Unknown", max_length=2000)
    commission_rate: float | None = Field(default=None, ge=0, le=1)
    evidence_source_ids: list[str] = Field(default_factory=list)
    observed_at: datetime


class FeedbackPayload(StrictContract):
    summary: str = Field(min_length=1, max_length=1000)
    input: str = Field(min_length=1, max_length=4000)
    classification: Literal["preference", "correction", "operating_directive", "hypothesis", "ontology_gap"]
    target_ids: list[str] = Field(default_factory=list, max_length=30)
    proposed_improvement: str = Field(default="", max_length=3000)
    system_area: Literal["governance", "agents_workflows", "ontology_schema", "data_evidence", "content_editorial", "media_rights", "release_publication", "commerce", "cost_operations", "audience_experience"] = "governance"
    authority: Literal["observation", "preference", "verified_evidence", "operating_directive"] = "observation"


class DecisionPayload(StrictContract):
    summary: str = Field(min_length=1, max_length=2000)
    feedback_ids: list[str] = Field(min_length=1, max_length=30)
    disposition: Literal["proposed", "no_change", "deferred"]
    rationale: str = Field(min_length=1, max_length=4000)
    target_ids: list[str] = Field(default_factory=list, max_length=30)
    expected_benefit: str = Field(min_length=1, max_length=2000)
    evaluation: str = Field(min_length=1, max_length=2000)
    system_area: Literal["governance", "agents_workflows", "ontology_schema", "data_evidence", "content_editorial", "media_rights", "release_publication", "commerce", "cost_operations", "audience_experience"] = "governance"
    rollback: str = Field(default="Retire the proposed version and restore the last active governed version.", max_length=2000)


class ContentBriefPayload(SmartGlassesPayload):
    workflow_family: str | None = None
    input_versions: dict[str, Annotated[int, Field(ge=1, strict=True)]] = Field(default_factory=dict, max_length=4)
    duration_seconds: int = Field(default=60, ge=30, le=90)
    aspect_ratios: list[Literal["9:16"]] = Field(default_factory=lambda: ["9:16"])
    production_state: Literal["draft", "needs_evidence_review"] = "draft"


PAYLOAD_TYPES = {
    "refresh_job": RefreshJobPayload, "storyboard": StoryboardPayload,
    "product": ProductPayload, "source_policy": SourcePolicyPayload,
    "commerce_path": CommercePathPayload, "feedback": FeedbackPayload,
    "decision_record": DecisionPayload, "field_definition": FieldDefinition,
    "market_observation": ObservationPayload, "content_brief": ContentBriefPayload,
}


def validate_object(item: UniversalObject, definitions, lookup=None) -> UniversalObject:
    if item.domain != "smart_glasses":
        raise ValueError("Only the smart_glasses domain is enabled.")
    source_ids = [source.source_id for source in item.sources]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("Structured source IDs must be unique.")
    for source in item.sources:
        safe_source_uri(source.uri)
    for uri in item.source:
        safe_source_uri(uri)
    model = PAYLOAD_TYPES.get(item.object_type)
    if item.object_type == "content_asset" and "script_version" in item.payload:
        payload = VideoScript.model_validate(item.payload)
        if lookup:
            brief = lookup(payload.brief_object_id)
            claims = {claim["claim_id"] for claim in brief.payload.get("claims", [])}
            if any(ref not in claims for scene in payload.scenes for ref in scene.claim_ids):
                raise ValueError("Video script references a missing claim.")
    elif model:
        payload = model.model_validate(item.payload)
    elif item.object_type == "claim" and not item.payload:
        return item  # Empty draft; approval is blocked by the store.
    elif item.object_type in {kind.value for kind in SmartGlassesObjectType}:
        payload = SmartGlassesObject.model_validate(item.model_dump(mode="json")).payload
    else:
        raise ValueError("Object type is not registered.")
    data = payload.model_dump(mode="json")
    if item.object_type == "refresh_job" and lookup:
        policy = lookup(payload.source_policy_id)
        if policy.object_type != "source_policy":
            raise ValueError("Refresh plans must reference source policies.")
        if item.status == ObjectStatus.captured and policy.version != payload.source_policy_version:
            raise ValueError("The source policy changed. Rebuild its refresh plan.")
    if item.object_type == "storyboard" and lookup:
        brief = lookup(payload.brief_object_id)
        if brief.object_type != "content_brief":
            raise ValueError("Storyboards must reference a content brief.")
        claims = {claim["claim_id"] for claim in brief.payload.get("claims", [])}
        if any(cid not in claims for scene in payload.scenes for cid in scene.claim_ids):
            raise ValueError("A storyboard scene references a missing claim.")
        if item.status in {ObjectStatus.captured, ObjectStatus.active}:
            if brief.version != payload.brief_version:
                raise ValueError("The brief changed. Rebuild the storyboard.")
            for oid, version in brief.payload.get("input_versions", {}).items():
                if lookup(oid).version != version:
                    raise ValueError("Product evidence changed. Rebuild the brief and storyboard.")
    if item.object_type == "content_brief" and payload.workflow_family:
        versions = payload.input_versions
        if not versions or set(versions) != set(payload.entities) or set(versions) != set(item.parent_ids):
            raise ValueError("Regenerate this draft with complete product-version lineage.")
        if lookup:
            for oid, version in versions.items():
                product = lookup(oid)
                if product.object_type != "product":
                    raise ValueError("Draft lineage must reference product records.")
                if item.status in {ObjectStatus.captured, ObjectStatus.active} and product.version != version:
                    raise ValueError("An input product changed. Regenerate the draft before approval.")
    for key in ("source_uri", "merchant_uri", "program_uri", "terms_uri"):
        if data.get(key):
            safe_source_uri(data[key])
    used = set(data.get("evidence_source_ids", []))
    for claim in data.get("claims", []):
        used.update(claim.get("source_ids", []))
    if item.object_type == "product":
        for key, value in payload.fields.items():
            if key not in definitions:
                raise ValueError(f"Unapproved field definition: {key}")
            field = definitions[key]
            if field.category not in {"all", payload.category}:
                raise ValueError(f"Field is not applicable: {key}")
            used.update(value.source_ids)
            if value.value is None:
                continue
            if field.value_type == "number":
                if isinstance(value.value, bool) or not isinstance(value.value, (int, float)):
                    raise ValueError(f"Field requires a number: {key}")
                if field.minimum is not None and value.value < field.minimum:
                    raise ValueError(f"Field below minimum: {key}")
                if field.maximum is not None and value.value > field.maximum:
                    raise ValueError(f"Field above maximum: {key}")
            elif field.value_type == "boolean" and not isinstance(value.value, bool):
                raise ValueError(f"Field requires true or false: {key}")
            elif field.value_type == "text" and not isinstance(value.value, str):
                raise ValueError(f"Field requires text: {key}")
    if used - set(source_ids):
        raise ValueError("Every factual reference must resolve to a structured source.")
    if item.object_type == "field_definition" and payload.key in BASE_FIELD_MAP:
        raise ValueError("Built-in field definitions cannot be overwritten.")
    if item.object_type == "decision_record" and lookup:
        for oid in payload.feedback_ids:
            if lookup(oid).object_type != "feedback":
                raise ValueError("Decisions must reference feedback objects.")
    if item.object_type == "content_card" and lookup:
        product = lookup(payload.product_id)
        if product.object_type != "product" or product.version != payload.product_version:
            raise ValueError("Cards require the exact current product version.")
        if set(item.parent_ids) != {product.object_id}:
            raise ValueError("A card must identify its exact product parent.")
        for key in payload.field_keys:
            if key not in definitions or product.payload.get("fields", {}).get(key, {}).get("value") is None:
                raise ValueError("Cards require defined, populated product fields.")
    if item.object_type == "card_bundle" and lookup:
        for oid, version in payload.product_versions.items():
            product = lookup(oid)
            if product.object_type != "product" or product.version != version:
                raise ValueError("Card bundles require exact product versions.")
        for oid, version in payload.card_versions.items():
            card = lookup(oid)
            if card.object_type != "content_card" or card.version != version:
                raise ValueError("Card bundles require exact card versions.")
    if item.object_type == "shorts_plan" and lookup:
        bundle = lookup(payload.card_bundle_id)
        if bundle.object_type != "card_bundle" or bundle.version != payload.card_bundle_version:
            raise ValueError("Shorts plans require an exact card bundle version.")
        for oid, version in payload.card_versions.items():
            card = lookup(oid)
            if card.object_type != "content_card" or card.version != version:
                raise ValueError("Shorts plans require exact card versions.")
    if item.object_type == "distribution_package" and lookup:
        artifact = lookup(payload.render_artifact_id)
        if artifact.object_type != "render_artifact" or artifact.version != payload.render_artifact_version:
            raise ValueError("Distribution packages require the exact current render artifact.")
        if artifact.payload.get("video_sha256") != payload.exact_video_sha256:
            raise ValueError("Distribution package video identity differs from its render artifact.")
        if abs(float(artifact.payload.get("duration_seconds", 0)) - payload.duration_seconds) > 0.001:
            raise ValueError("Distribution package duration differs from its render artifact.")
    if item.object_type == "publication_request" and lookup:
        package = lookup(payload.distribution_package_id)
        if package.object_type != "distribution_package" or package.version != payload.distribution_package_version:
            raise ValueError("Publication requests require the exact current distribution package.")
        if set(package.payload.get("destinations", [])) != set(payload.destinations):
            raise ValueError("Publication destinations differ from the pinned distribution package.")
    item.payload = data
    return item

# Typed media objects share the existing governed object store and generated forms.
from .media import MediaAssetPayload, RenderArtifactPayload, RenderRecipePayload

PAYLOAD_TYPES.update({
    "media_asset": MediaAssetPayload,
    "render_recipe": RenderRecipePayload,
    "render_artifact": RenderArtifactPayload,
})

from .commerce_assessment import CommercialEvidencePayload, CommerceAssessmentPayload

PAYLOAD_TYPES.update({
    "commerce_evidence": CommercialEvidencePayload,
    "commerce_assessment": CommerceAssessmentPayload,
})

from .release_review import ReleaseReviewPayload

PAYLOAD_TYPES["release_review_packet"] = ReleaseReviewPayload

from .distribution import DistributionPackagePayload, PublicationRequestPayload

PAYLOAD_TYPES.update({
    "distribution_package": DistributionPackagePayload,
    "publication_request": PublicationRequestPayload,
})

from .audience import CardBundlePayload, ContentCardPayload, ShortsPlanPayload

PAYLOAD_TYPES.update({
    "content_card": ContentCardPayload,
    "card_bundle": CardBundlePayload,
    "shorts_plan": ShortsPlanPayload,
})
