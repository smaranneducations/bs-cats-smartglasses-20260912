from __future__ import annotations

from collections import defaultdict, deque
from typing import Literal

from pydantic import Field, model_validator

from packages.contracts.object import ActorType, UniversalObject
from packages.runtime.context import canonical, fingerprint, reject_obvious_credentials
from packages.runtime.contracts import RuntimeContract

FAMILIES = {"category", "product", "feature", "comparison", "use_case", "value", "change", "compatibility", "question", "myth", "market", "commercial"}


def scalar(value):
    return getattr(value, "value", value)


class CreativeRule(RuntimeContract):
    key: Literal["background_music_required", "voiceover_enabled", "imagery_mode", "kinetic_text", "duration_min_seconds", "duration_max_seconds"]
    value: bool | int | str

    @model_validator(mode="after")
    def allowed_values(self):
        if self.key in {"background_music_required", "kinetic_text"} and self.value is not True:
            raise ValueError("The current creative charter requires music and kinetic text.")
        if self.key == "voiceover_enabled" and type(self.value) is not bool:
            raise ValueError("Voiceover selection must be boolean and cannot authorize a paid provider.")
        if self.key == "imagery_mode" and self.value not in {"original_or_licensed_realistic", "original_illustration_labelled"}:
            raise ValueError("Imagery must preserve rights and illustration labeling.")
        if self.key in {"duration_min_seconds", "duration_max_seconds"} and (type(self.value) is not int or not 30 <= self.value <= 90):
            raise ValueError("This creative profile stays within 30-90 seconds.")
        return self


class LearningProposal(RuntimeContract):
    schema_version: Literal["learning-proposal-1"] = "learning-proposal-1"
    kind: Literal["scoped_preference", "evaluation_case", "ontology_change_proposal", "correction_impact", "no_change"]
    domain_id: Literal["smart_glasses"] = "smart_glasses"
    workflow_families: list[str] = Field(default_factory=list, max_length=12)
    feedback_versions: dict[str, int] = Field(min_length=1, max_length=10)
    target_ids: list[str] = Field(default_factory=list, max_length=30)
    proposed_rules: list[CreativeRule] = Field(default_factory=list, max_length=8)
    expected_benefit: str = Field(min_length=8, max_length=1500)
    evaluation: str = Field(min_length=8, max_length=1500)
    rollback: str = Field(min_length=8, max_length=1500)

    @model_validator(mode="after")
    def coherent_scope(self):
        if set(self.workflow_families) - FAMILIES or len(set(self.workflow_families)) != len(self.workflow_families):
            raise ValueError("Use distinct supported workflow families.")
        if any(type(version) is not int or version < 1 for version in self.feedback_versions.values()):
            raise ValueError("Feedback inputs must pin positive versions.")
        if len({rule.key for rule in self.proposed_rules}) != len(self.proposed_rules):
            raise ValueError("A proposal cannot contain conflicting duplicate rules.")
        if self.kind != "scoped_preference" and self.proposed_rules:
            raise ValueError("Ontology and correction proposals cannot automatically change creative policy.")
        reject_obvious_credentials(self.model_dump(mode="json"))
        return self


def object_map(store):
    objects = store.list_objects()
    if len(objects) > 500:
        raise ValueError("The intelligence working set requires a paginated adapter beyond 500 objects.")
    return {item.object_id: item for item in objects}


def prepare_decision(store, feedback_id, proposal, actor_id="agent:intelligence-learning"):
    objects = object_map(store)
    feedback = objects.get(feedback_id)
    if feedback is None or feedback.object_type != "feedback":
        raise ValueError("A governed feedback object is required.")
    if proposal.feedback_versions != {feedback_id: feedback.version}:
        raise ValueError("The decision must pin its exact current feedback version.")
    if any(key not in objects for key in proposal.target_ids):
        raise ValueError("A feedback target is unavailable.")
    data = proposal.model_dump(mode="json")
    proposal_hash = fingerprint(data)
    object_id = "decision_" + proposal_hash[:32]
    if object_id in objects:
        if objects[object_id].metadata.get("intelligence_proposal_hash") != proposal_hash:
            raise ValueError("The existing decision identity has different proposal content.")
        return objects[object_id]
    summary = feedback.payload["summary"]
    reject_obvious_credentials(summary)
    decision = UniversalObject(
        object_id=object_id, object_type="decision_record",
        title=("Feedback disposition: " + summary)[:240],
        purpose="Turn scoped human feedback into a reviewable decision, evaluation and execution-memory proposal.",
        parent_ids=[feedback_id, *[key for key in proposal.target_ids if key != feedback_id]],
        payload={"summary": summary, "feedback_ids": [feedback_id],
                 "disposition": "no_change" if proposal.kind == "no_change" else "proposed",
                 "rationale": "Prepared from a version-pinned feedback object. Human feedback is relevant context, not automatically a verified product fact or authority to change permissions.",
                 "target_ids": proposal.target_ids, "expected_benefit": proposal.expected_benefit,
                 "evaluation": proposal.evaluation},
        metadata={"intelligence_proposal": data, "intelligence_proposal_hash": proposal_hash,
                  "production_policy_promoted": False, "source_feedback_versions": proposal.feedback_versions},
    )
    return store.capture(decision, actor_id=actor_id, actor_type=ActorType.agent,
                         idempotency_key="learning-" + proposal_hash,
                         request_input={"proposal": data, "feedback_summary": summary})


def inspect_proposal(item, objects):
    raw = item.metadata.get("intelligence_proposal")
    if item.object_type != "decision_record" or raw is None:
        return None
    proposal = LearningProposal.model_validate(raw)
    if fingerprint(proposal.model_dump(mode="json")) != item.metadata.get("intelligence_proposal_hash"):
        raise ValueError("Learning proposal content changed without a matching proposal identity.")
    fresh = all(key in objects and objects[key].object_type == "feedback" and objects[key].version == version
                and scalar(objects[key].status) not in {"rejected", "archived", "deprecated"}
                for key, version in proposal.feedback_versions.items())
    approved = scalar(item.review.state) == "approved" and scalar(item.status) not in {"rejected", "archived", "deprecated"}
    return proposal, fresh, approved


def retrieve_memory(store, workflow_family=None, target_ids=()):
    objects, selected, active_rules, pending, stale = object_map(store), [], {}, 0, []
    targets = set(target_ids)
    for item in objects.values():
        inspected = inspect_proposal(item, objects)
        if inspected is None:
            continue
        proposal, fresh, approved = inspected
        if proposal.workflow_families and workflow_family not in proposal.workflow_families:
            continue
        if proposal.target_ids and not targets.intersection(proposal.target_ids):
            continue
        if not fresh:
            stale.append(item.object_id)
            continue
        if not approved:
            pending += 1
            continue
        # Ontology changes and factual corrections need their own migration or
        # evidence process; approval of a decision is not an automatic migration.
        if proposal.kind in {"ontology_change_proposal", "correction_impact", "no_change"}:
            continue
        advice = {"decision_id": item.object_id, "decision_version": item.version,
                  "proposal_hash": item.metadata["intelligence_proposal_hash"],
                  "kind": proposal.kind, "summary": item.payload["summary"],
                  "evaluation": proposal.evaluation, "feedback_versions": proposal.feedback_versions,
                  "authority": "Contextual advice only; not permission, factual proof, or a spending/publication grant."}
        reject_obvious_credentials(advice)
        selected.append(advice)
        for rule in proposal.proposed_rules:
            if rule.key in active_rules and active_rules[rule.key] != rule.value:
                raise ValueError("Approved scoped creative rules conflict; resolve their decisions rather than guessing precedence.")
            active_rules[rule.key] = rule.value
    if len(selected) > 12:
        raise ValueError("Consolidate approved scoped decisions before exceeding the compact memory budget.")
    result = {"schema_version": "governed-memory-1", "workflow_family": workflow_family,
              "target_ids": sorted(targets), "decisions": sorted(selected, key=lambda item: item["decision_id"]),
              "active_creative_rules": active_rules, "pending_relevant_proposals": pending,
              "stale_decision_ids": sorted(stale), "automatic_policy_promotion": False}
    if len(canonical(result).encode()) > 16384:
        raise ValueError("Scoped memory exceeds the fixed 16 KiB context budget.")
    return result


def assert_memory_current(store, memory):
    current = retrieve_memory(store, memory.get("workflow_family"), memory.get("target_ids", []))
    # Unreviewed proposals may arrive without invalidating a job. Changes to
    # approved advice or executable rules require a newly admitted context.
    for key in ("decisions", "active_creative_rules"):
        if current[key] != memory.get(key):
            raise ValueError("Approved intelligence context changed; re-admit the task against current decisions.")


def creative_settings(profile, memory):
    values = dict(profile["runtime_settings"])
    values.update(memory["active_creative_rules"])
    if values.get("background_music_required") is not True or values.get("kinetic_text") is not True:
        raise ValueError("The current image/music/kinetic creative charter must remain intact.")
    if values.get("mechanical_narration_allowed") is not False or values.get("media_rights_required") is not True:
        raise ValueError("Creative memory cannot weaken narration or media-rights boundaries.")
    if not 60 <= values["duration_min_seconds"] <= values["duration_max_seconds"] <= 120:
        raise ValueError("Creative duration rules conflict.")
    return values


def impact_report(store, changed_ids):
    objects = object_map(store)
    if len(changed_ids) > 30 or any(key not in objects for key in changed_ids):
        raise ValueError("Choose up to 30 existing change targets.")
    dependents = defaultdict(set)
    untracked = []
    for item in objects.values():
        parents = set(item.parent_ids)
        for mapping in (item.payload.get("input_versions"), item.metadata.get("source_versions"), item.metadata.get("source_feedback_versions")):
            if isinstance(mapping, dict):
                parents.update(mapping)
        for parent in parents:
            dependents[parent].add(item.object_id)
        if item.object_type in {"content_brief", "storyboard", "content_asset"} and not parents:
            untracked.append(item.object_id)
    visited, queue, result = set(changed_ids), deque((key, 0) for key in changed_ids), []
    while queue:
        parent, depth = queue.popleft()
        if depth >= 20:
            raise ValueError("Dependency depth exceeds the bounded impact traversal.")
        for child in sorted(dependents[parent]):
            if child in visited:
                continue
            visited.add(child)
            item = objects[child]
            result.append({"object_id": child, "version": item.version, "object_type": item.object_type,
                           "via_object_id": parent, "state": "requires_revalidation"})
            queue.append((child, depth + 1))
    return {"changed_ids": list(changed_ids), "affected_objects": result,
            "untracked_derived_objects": sorted(untracked), "approval_states_modified": False,
            "meaning": "Computed impact queue; not proof that every affected artifact has already been corrected."}


def learning_overview(store):
    objects, rows = object_map(store), []
    for item in objects.values():
        inspected = inspect_proposal(item, objects)
        if inspected:
            proposal, fresh, approved = inspected
            rows.append({"object_id": item.object_id, "version": item.version, "summary": item.payload["summary"],
                         "kind": proposal.kind, "review_state": scalar(item.review.state), "source_versions_current": fresh,
                         "human_approved": approved, "workflow_families": proposal.workflow_families,
                         "feedback_versions": proposal.feedback_versions, "evaluation": proposal.evaluation,
                         "proposed_rules": [rule.model_dump(mode="json") for rule in proposal.proposed_rules]})
    return {"schema_version": "learning-overview-1", "proposals": rows,
            "automatic_policy_promotion": False, "runtime_retrieval_connected": True,
            "ontology_migration_automatic": False, "permission_changes_allowed": False}
