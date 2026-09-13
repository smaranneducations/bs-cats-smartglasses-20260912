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
    story_role: Literal["hook", "tension", "differentiator_and_proof", "implication", "payoff"]
    primitive: Primitive
    heading: str = Field(min_length=1, max_length=160)
    lines: list[str] = Field(default_factory=list, max_length=4)
    claim_ids: list[str] = Field(default_factory=list, max_length=8)
    notes: list[str] = Field(default_factory=list)
    duration_seconds: int = Field(ge=6, le=30)


class StoryStrategy(StrictContract):
    target_audience_id: str = Field(min_length=1, max_length=120)
    audience_tension: str = Field(min_length=12, max_length=240)
    curiosity_gap: str = Field(min_length=12, max_length=240)
    differentiated_thesis: str = Field(min_length=12, max_length=320)
    decision_lever: str = Field(min_length=1, max_length=120)
    evidence_anchor_claim_ids: list[str] = Field(min_length=1, max_length=4)
    implication: str = Field(min_length=12, max_length=320)
    payoff: str = Field(min_length=12, max_length=240)
    visual_motif: str = Field(min_length=1, max_length=160)


class StoryCreativeGate(StrictContract):
    policy_version: Literal["story-quality-1"] = "story-quality-1"
    audience_tension_present: Literal[True] = True
    decision_lever_source_bound: Literal[True] = True
    arc_complete_and_ordered: Literal[True] = True
    at_least_four_distinct_primitives: Literal[True] = True
    hook_eight_seconds_or_less: Literal[True] = True
    payoff_distinct_from_hook: Literal[True] = True
    strong_model_review_state: Literal["required_before_release_candidate"] = "required_before_release_candidate"
    exact_artifact_human_review_required: Literal[True] = True


class StoryboardPayload(StrictContract):
    summary: str
    brief_object_id: str
    brief_version: Revision
    workflow_family: str
    aspect_ratio: Literal["9:16"] = "9:16"
    duration_seconds: int = Field(ge=30, le=90)
    story_strategy: StoryStrategy
    creative_gate: StoryCreativeGate
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
        expected_arc = ["hook", "tension", "differentiator_and_proof", "implication", "payoff"]
        if [scene.story_role for scene in self.scenes] != expected_arc:
            raise ValueError("Story scenes must complete the governed narrative arc in order.")
        if self.scenes[0].duration_seconds > 8:
            raise ValueError("The opening hook must land within eight seconds.")
        if len({scene.primitive for scene in self.scenes}) < 4:
            raise ValueError("A story needs at least four functionally distinct visual primitives.")
        visible_claims = {claim_id for scene in self.scenes for claim_id in scene.claim_ids}
        if not set(self.story_strategy.evidence_anchor_claim_ids).issubset(visible_claims):
            raise ValueError("The decision lever must be visibly bound to its evidence claims.")
        if self.story_strategy.payoff.strip().casefold() == self.story_strategy.audience_tension.strip().casefold():
            raise ValueError("The payoff must resolve rather than repeat the opening tension.")
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
    presentation = brief.payload.get("presentation", {})
    hook = presentation.get("hook") or brief.payload["summary"]
    scenes = [
        {"story_role": "hook", "primitive": "question_hook", "heading": "The question that changes the choice",
         "lines": [hook],
         "claim_ids": [], "notes": []},
        {"story_role": "tension", "primitive": "decision_map", "heading": "Why the obvious answer can mislead",
         "lines": ["The biggest specification is not automatically the best fit.",
                   "One decision lever matters only in the conditions where you will use it."],
         "claim_ids": [], "notes": ["Do not infer a recommendation from a larger specification number."]},
    ]
    anchor_claims = []
    lever_key = "source-linked evidence"
    if family == "comparison":
        by_field = {}
        for claim in claims.values():
            info = inputs.get(claim["claim_id"], {})
            if info.get("field_key") and info.get("object_id"):
                by_field.setdefault(info["field_key"], {})[info["object_id"]] = claim
        entities = brief.payload["entities"]
        if len(entities) != 2:
            raise ContractViolationError("The visual comparison currently supports exactly two products.")
        matched = [(field_key, list(group.values())) for field_key, group in by_field.items() if set(group) == set(entities)]
        if not matched:
            raise ContractViolationError("No matched, source-linked fields are available for this comparison.")
        lever_key, anchor_claims = matched[0]
        scenes.append({"story_role": "differentiator_and_proof", "primitive": "comparison_table",
            "heading": "The difference worth inspecting",
            "lines": [claim["statement"] for claim in anchor_claims],
            "claim_ids": [claim["claim_id"] for claim in anchor_claims],
            "notes": list(dict.fromkeys(note for claim in anchor_claims for note in claim.get("caveats", [])))})
    else:
        for index, claim in enumerate(selected):
            anchor_claims = [claim]
            lever_key = inputs.get(claim["claim_id"], {}).get("field_key") or "source-linked evidence"
            scenes.append({"story_role": "differentiator_and_proof",
                "primitive": PROFILES[family][index % len(PROFILES[family])],
                "heading": {"feature": "The detail that changes the decision", "compatibility": "The dependency that decides fit",
                            "question": "The evidence that answers it", "myth": "The proof behind the claim"
                            }.get(family, "The evidence worth inspecting"),
                "lines": [claim["statement"]], "claim_ids": [claim["claim_id"]],
                "notes": claim.get("caveats", [])})
    lever_label = lever_key.replace("_", " ").strip()
    implication = f"Use {lever_label} to narrow the fit, not to declare a universal winner."
    payoff = "Now verify this one difference against your own use before you spend."
    scenes += [
        {"story_role": "implication", "primitive": "uncertainty_card", "heading": "What this changes for you",
         "lines": [implication, "Then check comfort, compatibility, availability and extra costs."],
         "claim_ids": [], "notes": ["No active affiliate relationship or complete market coverage is claimed."]},
        {"story_role": "payoff", "primitive": "takeaway", "heading": "Make the difference earn its place",
         "lines": [payoff, "Open the evidence, then decide whether the trade-off fits."],
         "claim_ids": [], "notes": []},
    ]
    if any(len(line) > 240 for scene in scenes for line in scene["lines"]):
        raise ContractViolationError("A claim is too long for a readable kinetic card; prepare concise reviewed wording first.")
    duration = brief.payload.get("duration_seconds", 90)
    remaining = duration - 30
    weights = [4, 21, 30, 24, 21]
    durations = [6 + (remaining * weight // 100) for weight in weights]
    for index in [2, 3, 1, 4, 0][:duration - sum(durations)]:
        durations[index] += 1
    for index, scene in enumerate(scenes):
        scene["scene_id"] = f"scene_{index + 1:02d}"
        scene["duration_seconds"] = durations[index]
    strategy = {
        "target_audience_id": presentation.get("target_audience_id", "buyer_researching_practical_fit"),
        "audience_tension": hook,
        "curiosity_gap": "The most impressive-looking number may not be the difference that improves practical fit.",
        "differentiated_thesis": f"This story makes {lever_label} decision-relevant while preserving its evidence limits.",
        "decision_lever": lever_label,
        "evidence_anchor_claim_ids": [claim["claim_id"] for claim in anchor_claims],
        "implication": implication,
        "payoff": payoff,
        "visual_motif": "question to contrast to proof to consequence",
    }
    payload = StoryboardPayload.model_validate({
        "summary": "Private evidence-bound story strategy and animated storyboard; not an approved video.",
        "brief_object_id": brief.object_id, "brief_version": brief.version,
        "workflow_family": family, "aspect_ratio": aspect_ratio,
        "duration_seconds": duration, "story_strategy": strategy,
        "creative_gate": {}, "scenes": scenes,
    }).model_dump(mode="json")
    identity = f"{brief.object_id}:{brief.version}:{aspect_ratio}:story-quality-1"
    oid = "storyboard_" + sha256(identity.encode()).hexdigest()[:32]
    title = "Visual plan: " + brief.title
    return UniversalObject(object_id=oid, object_type="storyboard",
        title=title if len(title) <= 240 else title[:237] + "...",
        purpose="Prepare a private kinetic-text preview from one versioned evidence brief.",
        sources=brief.sources, parent_ids=[brief.object_id],
        payload=payload,
        metadata={"full_title": title, "primitive_registry_version": "story-quality-1",
                  "strong_model_story_review_required": True,
                  "needs_layout_and_claim_review": True, "publication_allowed": False})
