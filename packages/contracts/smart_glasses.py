from __future__ import annotations

from enum import Enum
from typing import Literal, Self

from pydantic import Field, model_validator

from .object import StrictContract, UniversalObject


class SmartGlassesObjectType(str, Enum):
    product = "product"
    company = "company"
    technology = "technology"
    feature = "feature"
    specification = "specification"
    use_case = "use_case"
    market_observation = "market_observation"
    buyer_question = "buyer_question"
    claim = "claim"
    comparison = "comparison"
    content_brief = "content_brief"
    content_asset = "content_asset"
    distribution = "distribution"
    performance_metric = "performance_metric"
    experiment = "experiment"
    correction = "correction"


class ClaimKind(str, Enum):
    fact = "fact"
    estimate = "estimate"
    interpretation = "interpretation"
    opinion = "opinion"
    prediction = "prediction"


class EvidenceTier(str, Enum):
    primary_manufacturer = "primary_manufacturer"
    primary_regulatory = "primary_regulatory"
    primary_first_party_test = "primary_first_party_test"
    reputable_independent = "reputable_independent"
    community_report = "community_report"
    anecdotal = "anecdotal"
    synthetic = "synthetic"


class VerificationState(str, Enum):
    unverified = "unverified"
    corroborated = "corroborated"
    verified = "verified"
    disputed = "disputed"
    superseded = "superseded"


class AudienceIntent(str, Enum):
    learn = "learn"
    compare = "compare"
    buy = "buy"
    implement = "implement"
    monitor = "monitor"


class CommercialIntent(str, Enum):
    none = "none"
    affiliate = "affiliate"
    sponsorship = "sponsorship"
    subscription = "subscription"
    lead_generation = "lead_generation"
    research_license = "research_license"


class EvidenceClaim(StrictContract):
    claim_id: str = Field(..., min_length=3, max_length=128)
    statement: str = Field(..., min_length=1, max_length=2000)
    kind: ClaimKind
    source_ids: list[str] = Field(default_factory=list)
    evidence_tier: EvidenceTier
    verification_state: VerificationState = VerificationState.unverified
    confidence: float = Field(..., ge=0, le=1)
    caveats: list[str] = Field(default_factory=list)
    freshness_check_required: bool = True

    @model_validator(mode="after")
    def enforce_evidence_quality(self) -> Self:
        source_required = self.kind in {
            ClaimKind.fact,
            ClaimKind.estimate,
            ClaimKind.prediction,
        }
        if source_required and not self.source_ids:
            raise ValueError(f"{self.kind.value} claims require at least one source_id")
        weak_tiers = {
            EvidenceTier.community_report,
            EvidenceTier.anecdotal,
            EvidenceTier.synthetic,
        }
        if self.verification_state == VerificationState.verified and self.evidence_tier in weak_tiers:
            raise ValueError("weak or synthetic evidence cannot be marked verified")
        return self


class SmartGlassesPayload(StrictContract):
    summary: str = Field(..., min_length=1, max_length=4000)
    claims: list[EvidenceClaim] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    audience_intent: AudienceIntent = AudienceIntent.learn
    commercial_intent: CommercialIntent = CommercialIntent.none
    disclosure_required: bool = False
    recommended_next_action: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def require_commercial_disclosure(self) -> Self:
        if self.commercial_intent != CommercialIntent.none and not self.disclosure_required:
            raise ValueError("commercial content must require a disclosure")
        return self


class SmartGlassesObject(UniversalObject):
    domain: Literal["smart_glasses"] = "smart_glasses"
    object_type: SmartGlassesObjectType
    payload: SmartGlassesPayload

    @model_validator(mode="after")
    def link_claims_to_sources(self) -> Self:
        known_source_ids = {source.source_id for source in self.sources}
        missing_source_ids = {
            source_id
            for claim in self.payload.claims
            for source_id in claim.source_ids
            if source_id not in known_source_ids
        }
        if missing_source_ids:
            raise ValueError("every claim source_id must reference a structured source")
        return self
