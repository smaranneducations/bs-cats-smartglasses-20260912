"""An inspectable artifact review packet, never a publication authorization."""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReleaseCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    check_id: str = Field(min_length=1, max_length=80)
    state: Literal["passed", "needs_review", "blocked", "unavailable"]
    reason: str = Field(min_length=1, max_length=1200)
    object_ids: list[str] = Field(default_factory=list, max_length=40)


class ReleaseReviewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(min_length=1, max_length=2000)
    policy_version: Literal["artifact-review-1"] = "artifact-review-1"
    checked_at: datetime
    artifact_id: str
    artifact_version: int = Field(ge=1)
    recipe_id: str
    recipe_version: int = Field(ge=1)
    video_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    metadata_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_versions: dict[str, int]
    input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    missing_input_ids: list[str] = Field(default_factory=list, max_length=40)
    observed_hashes: dict[str, str | None]
    checks: list[ReleaseCheck] = Field(min_length=14, max_length=14)
    prerequisites_satisfied: bool
    assessment_scope: Literal["artifact_and_lineage_only"] = "artifact_and_lineage_only"
    recheck_required_before_use: Literal[True] = True
    permission_granted: Literal[False] = False
    cloud_and_spend_admission_assessed: Literal[False] = False

    @model_validator(mode="after")
    def coherent_packet(self):
        if self.checked_at.tzinfo is None:
            raise ValueError("A review packet requires an explicit observation timezone")
        if not 2 <= len(self.input_versions) <= 40 or any(type(value) is not int or value < 1 for value in self.input_versions.values()):
            raise ValueError("Review packets require bounded exact input versions")
        if self.input_versions.get(self.artifact_id) != self.artifact_version or self.input_versions.get(self.recipe_id) != self.recipe_version:
            raise ValueError("Artifact and recipe must be among the exact packet inputs")
        if len({check.check_id for check in self.checks}) != len(self.checks):
            raise ValueError("A review packet cannot contain duplicate checks")
        expected = all(check.state == "passed" for check in self.checks if check.check_id != "human_artifact_review")
        if self.prerequisites_satisfied != expected:
            raise ValueError("Prerequisite state must agree with every prerequisite check")
        return self
