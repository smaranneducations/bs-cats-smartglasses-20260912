"""Private planning contracts. No network, model calls or publishing capabilities."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .object import StrictContract, UniversalObject

Revision = Annotated[int, Field(ge=1, strict=True)]
Primitive = Literal[
    "question_hook", "product_card", "feature_callout", "comparison_table",
    "decision_map", "metric_card", "timeline", "compatibility_chain",
    "question_reveal", "evidence_note", "uncertainty_card", "takeaway",
]


class RefreshJobPayload(StrictContract):
    summary: str
    source_policy_id: str
    source_policy_version: Revision
    planned_for: datetime
    assessed_at: datetime
    state: Literal["blocked", "scheduled"]
    blockers: list[str]
    execution_enabled: Literal[False] = False


class StoryScene(StrictContract):
    scene_id: str
    primitive: Primitive
    heading: str = Field(min_length=1, max_length=160)
    lines: list[str] = Field(default_factory=list, max_length=4)
    claim_ids: list[str] = Field(default_factory=list, max_length=8)
    notes: list[str] = Field(default_factory=list)
    duration_seconds: int = Field(ge=6, le=30)


class StoryboardPayload(StrictContract):
    summary: str
    brief_object_id: str
    brief_version: Revision
    workflow_family: str
    aspect_ratio: Literal["9:16"] = "9:16"
    duration_seconds: int = Field(ge=30, le=90)
    scenes: list[StoryScene] = Field(min_length=5, max_length=10)
    media_mode: Literal["original_abstract_graphics"] = "original_abstract_graphics"
    narration: Literal["none"] = "none"
    render_state: Literal["preview_only"] = "preview_only"
    publication_allowed: Literal[False] = False

    @model_validator(mode="after")
    def valid_timeline(self):
        if sum(scene.duration_seconds for scene in self.scenes) != self.duration_seconds:
            raise ValueError("Scene durations must exactly match the storyboard duration.")
        if len({scene.scene_id for scene in self.scenes}) != len(self.scenes):
            raise ValueError("Scene identifiers must be unique.")
        return self


PROFILES = {
    "category": ["decision_map", "product_card", "feature_callout"],
    "product": ["product_card", "metric_card", "feature_callout"],
    "feature": ["feature_callout", "metric_card", "evidence_note"],
    "comparison": ["comparison_table"],
    "use_case": ["decision_map", "compatibility_chain", "product_card"],
    "value": ["uncertainty_card", "product_card", "evidence_note"],
    "compatibility": ["compatibility_chain", "feature_callout", "evidence_note"],
    "question": ["question_reveal", "feature_callout", "evidence_note"],
    "myth": ["question_reveal", "evidence_note", "uncertainty_card"],
    "market": ["product_card", "metric_card", "uncertainty_card"],
}


def _date(value):
    result = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Source dates require a timezone.")
    return result


def source_refresh_plan(policy: UniversalObject, now=None):
    now = now or datetime.now(UTC)
    data = policy.payload
    due = _date(data["last_observed_at"]) + timedelta(days=data["refresh_days"])
    blockers = []
    if policy.status.value != "active" or policy.review.state.value != "approved":
        blockers.append("Source policy has not been approved.")
    if data.get("automation") != "allowed":
        blockers.append("Automated collection permission is not allowed.")
    if data.get("commercial_reuse") != "allowed":
        blockers.append("Intended commercial factual reuse is not cleared.")
    if data.get("access") not in {"api", "licensed_feed"}:
        blockers.append("No approved API or licensed-feed acquisition method.")
    expiry = data.get("permission_expires_at")
    if not expiry:
        blockers.append("A permission review expiry is not recorded.")
    elif _date(expiry) <= now:
        blockers.append("Source permission review has expired.")
    if not data.get("terms_uri"):
        blockers.append("Source-specific terms evidence is missing.")
    blockers.append("Collector adapter is not connected; no network request will run.")
    return {
        "source_policy_id": policy.object_id, "source_policy_version": policy.version,
        "title": policy.title, "source_uri": data["source_uri"],
        "planned_for": due.isoformat(), "assessed_at": now.isoformat(),
        "due": due <= now, "state": "blocked", "blockers": blockers,
        "execution_enabled": False,
    }


def refresh_job(policy, now=None):
    plan = source_refresh_plan(policy, now)
    identity = f"{policy.object_id}:{policy.version}:{plan['planned_for']}"
    oid = "refresh_" + sha256(identity.encode()).hexdigest()[:32]
    title = "Refresh plan: " + policy.title
    return UniversalObject(object_id=oid, object_type="refresh_job",
        title=title if len(title) <= 240 else title[:237] + "...",
        purpose="Track due work and unresolved collection gates without granting network access.",
        parent_ids=[policy.object_id], sources=policy.sources,
        payload={key: plan[key] for key in
                 ["source_policy_id", "source_policy_version", "planned_for", "assessed_at",
                  "state", "blockers", "execution_enabled"]} | {"summary": "Private source-refresh planning record."},
        metadata={"operational_only": True, "full_title": title})


def build_storyboard(brief, aspect_ratio="9:16"):
    from .store import ContractViolationError
    if aspect_ratio != "9:16":
        raise ContractViolationError("Canonical storyboards support only the 9:16 aspect ratio.")
    family = brief.payload.get("workflow_family")
    if family not in PROFILES or not brief.payload.get("input_versions"):
        raise ContractViolationError("Compose a current supported workflow brief before preparing a visual plan.")
    if brief.status.value in {"rejected", "archived", "deprecated"}:
        raise ContractViolationError("Retired briefs cannot supply a new storyboard.")
    claims = {claim["claim_id"]: claim for claim in brief.payload.get("claims", [])}
    if not claims:
        raise ContractViolationError("A visual plan needs source-linked claims.")
    inputs = brief.metadata.get("claim_inputs", {})
    sections = brief.payload.get("presentation", {}).get("sections", [])
    groups = [[claims[cid] for cid in section.get("claim_ids", []) if cid in claims] for section in sections]
    selected = []
    while any(groups) and len(selected) < 1:
        for group in groups:
            if group and len(selected) < 1:
                selected.append(group.pop(0))
    if not selected:
        raise ContractViolationError("The brief has no claims assigned to its presentation sections.")
    scenes = [
        {"primitive": "question_hook", "heading": "Start with the buyer's question",
         "lines": [brief.payload.get("presentation", {}).get("hook") or brief.payload["summary"]],
         "claim_ids": [], "notes": []},
        {"primitive": "decision_map", "heading": "The scope of this story",
         "lines": ["A limited research sample, not a complete market ranking.",
                   "Check the product's market, variant, fit and connected device."],
         "claim_ids": [], "notes": ["Do not infer a recommendation from a larger specification number."]},
    ]
    if family == "comparison":
        by_field = {}
        for claim in claims.values():
            info = inputs.get(claim["claim_id"], {})
            if info.get("field_key") and info.get("object_id"):
                by_field.setdefault(info["field_key"], {})[info["object_id"]] = claim
        entities = brief.payload["entities"]
        if len(entities) != 2:
            raise ContractViolationError("The visual comparison currently supports exactly two products.")
        matched = [list(group.values()) for group in by_field.values() if set(group) == set(entities)]
        if not matched:
            raise ContractViolationError("No matched, source-linked fields are available for this comparison.")
        for pair in matched[:1]:
            scenes.append({"primitive": "comparison_table", "heading": "A difference, not an automatic winner",
                "lines": [claim["statement"] for claim in pair],
                "claim_ids": [claim["claim_id"] for claim in pair],
                "notes": list(dict.fromkeys(note for claim in pair for note in claim.get("caveats", [])))})
    else:
        for index, claim in enumerate(selected):
            scenes.append({"primitive": PROFILES[family][index % len(PROFILES[family])],
                "heading": {"feature": "What this specification says", "compatibility": "Check the complete connection",
                            "question": "What the evidence can answer", "myth": "Inspect the evidence, not the slogan"
                            }.get(family, "A source-linked detail"),
                "lines": [claim["statement"]], "claim_ids": [claim["claim_id"]],
                "notes": claim.get("caveats", [])})
    scenes += [
        {"primitive": "uncertainty_card", "heading": "Keep the limits visible",
         "lines": ["Manufacturer statements are not hands-on tests.",
                   "Availability, fit and extra costs need current buyer-specific checks."],
         "claim_ids": [], "notes": ["No active affiliate relationship or complete market coverage is claimed."]},
        {"primitive": "takeaway", "heading": "Evidence over hype",
         "lines": ["Use the source-linked comparison to decide what to investigate next.",
                   "Check the evidence before deciding what to buy."], "claim_ids": [], "notes": []},
    ]
    if any(len(line) > 240 for scene in scenes for line in scene["lines"]):
        raise ContractViolationError("A claim is too long for a readable kinetic card; prepare concise reviewed wording first.")
    duration = brief.payload.get("duration_seconds", 90)
    seconds, remainder = divmod(duration, len(scenes))
    for index, scene in enumerate(scenes):
        scene["scene_id"] = f"scene_{index + 1:02d}"
        scene["duration_seconds"] = seconds + (index < remainder)
    identity = f"{brief.object_id}:{brief.version}:{aspect_ratio}:scene-plan-1"
    oid = "storyboard_" + sha256(identity.encode()).hexdigest()[:32]
    title = "Visual plan: " + brief.title
    return UniversalObject(object_id=oid, object_type="storyboard",
        title=title if len(title) <= 240 else title[:237] + "...",
        purpose="Prepare a private kinetic-text preview from one versioned evidence brief.",
        sources=brief.sources, parent_ids=[brief.object_id],
        payload={"summary": "Animated storyboard only; not an exported or approved video.",
                 "brief_object_id": brief.object_id, "brief_version": brief.version,
                 "workflow_family": family, "aspect_ratio": aspect_ratio,
                 "duration_seconds": duration, "scenes": scenes},
        metadata={"full_title": title, "primitive_registry_version": "scene-plan-1",
                  "needs_layout_and_claim_review": True, "publication_allowed": False})
