from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Self

from pydantic import Field, model_validator

from .object import SourceReference, StrictContract
from .smart_glasses import (
    AudienceIntent,
    CommercialIntent,
    EvidenceClaim,
    EvidenceTier,
    PresentationPlan,
    SmartGlassesObject,
    SmartGlassesObjectType,
    SmartGlassesPayload,
)


class ResearchStage(str, Enum):
    queued = "queued"
    gathering_sources = "gathering_sources"
    drafting = "drafting"
    ready_for_human_review = "ready_for_human_review"
    approved = "approved"
    rejected = "rejected"


class ResearchSourceDigest(StrictContract):
    source_id: str = Field(..., min_length=3, max_length=128)
    uri: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=500)
    publisher: str = Field(..., min_length=1, max_length=240)
    evidence_tier: EvidenceTier
    published_at: datetime | None = None
    retrieved_at: datetime
    digest: str = Field(..., min_length=1, max_length=4000)
    caveats: list[str] = Field(default_factory=list)

    def to_source_reference(self) -> SourceReference:
        notes = self.digest
        if self.caveats:
            notes = f"{notes} Caveats: {'; '.join(self.caveats)}"
        return SourceReference(
            source_id=self.source_id,
            uri=self.uri,
            title=self.title,
            publisher=self.publisher,
            published_at=self.published_at,
            captured_at=self.retrieved_at,
            notes=notes,
        )


class ResearchManifest(StrictContract):
    manifest_version: Literal["1.0"] = "1.0"
    research_id: str = Field(..., min_length=3, max_length=128)
    brief_object_id: str = Field(..., min_length=3, max_length=128)
    stage: ResearchStage = ResearchStage.ready_for_human_review
    title: str = Field(..., min_length=1, max_length=240)
    purpose: str = Field(..., min_length=1, max_length=1000)
    summary: str = Field(..., min_length=1, max_length=4000)
    sources: list[ResearchSourceDigest] = Field(..., min_length=1)
    claims: list[EvidenceClaim] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    audience_intent: AudienceIntent = AudienceIntent.learn
    commercial_intent: CommercialIntent = CommercialIntent.none
    disclosure_required: bool = False
    recommended_next_action: str | None = Field(default=None, max_length=1000)
    presentation: PresentationPlan

    @model_validator(mode="after")
    def enforce_manifest_links(self) -> Self:
        source_ids = [source.source_id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("research source IDs must be unique")
        known_source_ids = set(source_ids)
        missing_source_ids = {
            source_id
            for claim in self.claims
            for source_id in claim.source_ids
            if source_id not in known_source_ids
        }
        if missing_source_ids:
            raise ValueError("every research claim must reference a manifest source")
        claim_ids = {claim.claim_id for claim in self.claims}
        missing_claim_ids = {
            claim_id
            for section in self.presentation.sections
            for claim_id in section.claim_ids
            if claim_id not in claim_ids
        }
        if missing_claim_ids:
            raise ValueError("every presentation claim ID must reference a manifest claim")
        return self

    def to_object(self) -> SmartGlassesObject:
        source_references = [source.to_source_reference() for source in self.sources]
        return SmartGlassesObject(
            object_id=self.brief_object_id,
            object_type=SmartGlassesObjectType.content_brief,
            title=self.title,
            purpose=self.purpose,
            created_by="research-agent",
            source=[source.uri for source in self.sources],
            sources=source_references,
            tags=self.tags,
            payload=SmartGlassesPayload(
                summary=self.summary,
                claims=self.claims,
                entities=self.entities,
                topics=self.topics,
                audience_intent=self.audience_intent,
                commercial_intent=self.commercial_intent,
                disclosure_required=self.disclosure_required,
                recommended_next_action=self.recommended_next_action,
                presentation=self.presentation,
            ),
            metadata={
                "research_id": self.research_id,
                "research_stage": self.stage.value,
                "manifest_version": self.manifest_version,
            },
        )
