"""Commercial evidence and non-authorizing readiness assessments."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

CommercialGate = Literal["source_freshness", "record_review", "checkout", "publisher_approval", "product_eligibility", "editorial_independence", "commercial_reuse", "attribution", "payment"]
EvidenceGate = Literal["checkout", "publisher_approval", "product_eligibility", "editorial_independence", "commercial_reuse", "attribution", "payment"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CommercialFinding(Contract):
    gate: EvidenceGate
    finding: Literal["clear", "not_clear", "unknown"]
    rationale: str = Field(min_length=1, max_length=1000)
    evidence_source_ids: list[str] = Field(min_length=1, max_length=8)


class CommercialEvidencePayload(Contract):
    summary: str = Field(min_length=1, max_length=2000)
    path_id: str = Field(pattern=r"^[A-Za-z0-9_.:-]{3,128}$")
    path_version: int = Field(ge=1)
    checked_at: datetime
    recheck_after: datetime
    findings: list[CommercialFinding] = Field(min_length=1, max_length=7)
    authority_basis: Literal["public_document_analysis", "account_holder_reviewed_documents", "provider_approval_notice"]

    @model_validator(mode="after")
    def bounded_evidence(self):
        if self.checked_at.tzinfo is None or self.recheck_after.tzinfo is None or self.recheck_after <= self.checked_at:
            raise ValueError("Commercial evidence requires an ordered timezone-aware validity window")
        if (self.recheck_after - self.checked_at).total_seconds() > 30 * 86400:
            raise ValueError("Commercial evidence must be reassessed within thirty days")
        if len({finding.gate for finding in self.findings}) != len(self.findings):
            raise ValueError("Commercial evidence cannot contain conflicting duplicate gates")
        if self.authority_basis == "public_document_analysis" and any(finding.gate == "publisher_approval" and finding.finding == "clear" for finding in self.findings):
            raise ValueError("A public program page is not our publisher approval")
        return self


class GateAssessment(Contract):
    gate: CommercialGate
    state: Literal["clear", "unknown", "blocked"]
    reason: str = Field(min_length=1, max_length=500)
    evidence_object_id: str | None = None


class PathAssessment(Contract):
    path_id: str
    path_version: int = Field(ge=1)
    title: str
    customer_market: str
    stage: Literal["blocked_by_evidence", "awaiting_evidence", "ready_for_exact_artifact_review"]
    gates: list[GateAssessment] = Field(min_length=9, max_length=9)
    next_agent_action: str
    reserved_human_boundary: str


class CommerceAssessmentPayload(Contract):
    summary: str = Field(min_length=1, max_length=2000)
    policy_version: Literal["commerce-readiness-1"] = "commerce-readiness-1"
    assessed_at: datetime
    valid_until: datetime
    input_versions: dict[str, int]
    input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    paths: list[PathAssessment] = Field(min_length=1, max_length=4)
    publication_authorized: Literal[False] = False
    tracked_links_authorized: Literal[False] = False
    financial_commitment_authorized: Literal[False] = False
    predicted_earnings_included: Literal[False] = False
    human_action_required_now: Literal[False] = False

    @model_validator(mode="after")
    def exact_inputs(self):
        if self.assessed_at.tzinfo is None or self.valid_until.tzinfo is None or self.valid_until <= self.assessed_at:
            raise ValueError("Assessment requires a positive timezone-aware validity window")
        if not 1 <= len(self.input_versions) <= 8 or any(type(version) is not int or version < 1 for version in self.input_versions.values()):
            raise ValueError("Assessment requires one to eight exact positive input versions")
        for path in self.paths:
            if self.input_versions.get(path.path_id) != path.path_version or len({gate.gate for gate in path.gates}) != 9:
                raise ValueError("Assessment gates and path versions must be complete and unambiguous")
        return self
