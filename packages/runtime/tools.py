from __future__ import annotations

from datetime import datetime, timezone


class ToolInputError(ValueError):
    pass


def value_of(value):
    return getattr(value, "value", value)


def pinned_objects(store, request, context):
    profile = context["profile"]
    if len(request["inputs"]) > profile["maximum_objects"]:
        raise ToolInputError("Profile object limit exceeded.")
    result = []
    for reference in request["inputs"]:
        history = store.history(reference["object_id"])
        if not history:
            raise ToolInputError("An input object is unavailable.")
        latest = max(history, key=lambda item: item.snapshot.version).snapshot
        if latest.version != reference["version"]:
            raise ToolInputError("Input versions changed; submit a fresh proposal.")
        if value_of(latest.status) in {"archived", "deprecated", "rejected"}:
            raise ToolInputError("A retired or rejected object cannot supply a new proposal.")
        result.append(latest)
    return result


def catalogue_coverage(store, objects, request, context):
    definitions = store.definitions()
    rows = []
    for obj in objects:
        if obj.object_type != "product":
            raise ToolInputError("Catalogue audit accepts product objects only.")
        category = obj.payload.get("category")
        applicable = {key: definition for key, definition in definitions.items()
                      if value_of(definition.category) in {category, "all", "common", "general"}}
        fields = obj.payload.get("fields", {})
        known = [key for key in applicable if fields.get(key, {}).get("value") is not None]
        sourced = [key for key in known if fields[key].get("source_ids")]
        unknown_confidence = [key for key in sourced if fields[key].get("confidence") is None]
        observations = [{"concept_id": key, "observed_at": fields[key].get("observed_at"),
                         "evidence_kind": fields[key].get("evidence_kind"),
                         "confidence": fields[key].get("confidence"),
                         "source_ids": fields[key].get("source_ids", [])} for key in sourced]
        rows.append({"object_id": obj.object_id, "version": obj.version, "category": category,
                     "market": obj.payload.get("market"), "variant": obj.payload.get("variant"),
                     "applicable_concepts": len(applicable), "present_values": len(known),
                     "source_linked_values": len(sourced), "verified_values": None,
                     "missing_concepts": sorted(set(applicable) - set(known)),
                     "unknown_confidence_concepts": unknown_confidence, "observations": observations,
                     "coverage_fraction": len(sourced) / len(applicable) if applicable else None,
                     "review_required": True})
    return {"products": rows, "coverage_basis": "Current definition registry and recorded source links, not independent verification.",
            "refresh_caveat": "Freshness requires each source policy and field volatility; no generic date implies approval."}


def source_policy_queue(store, objects, request, context):
    now, rows = datetime.now(timezone.utc), []
    for obj in objects:
        if obj.object_type != "source_policy":
            raise ToolInputError("Source policy audit accepts policy objects only.")
        payload, blockers = obj.payload, []
        for key in ("automation", "commercial_reuse", "media_reuse"):
            if payload.get(key) != "allowed":
                blockers.append(key + "_not_allowed")
        review = obj.review.model_dump(mode="json") if getattr(obj, "review", None) is not None else {}
        if review.get("state") != "approved":
            blockers.append("human_source_policy_approval_not_established")
        if not payload.get("terms_uri"):
            blockers.append("terms_reference_missing")
        expiry = payload.get("permission_expires_at")
        try:
            parsed = datetime.fromisoformat(str(expiry).replace("Z", "+00:00"))
            if parsed.tzinfo is None or parsed <= now:
                blockers.append("permission_expired_or_undated")
        except (ValueError, TypeError):
            blockers.append("permission_expiry_unknown")
        rows.append({"object_id": obj.object_id, "version": obj.version,
                     "access_method": payload.get("access"),
                     "last_observed_at": payload.get("last_observed_at"), "refresh_days": payload.get("refresh_days"),
                     "blockers": blockers, "automated_collection_available": False,
                     "next_action": "Resolve the specific rights or consent gap; no collection is authorized by this report." if blockers else "An approved, bounded collector adapter is still required."})
    return {"source_policies": rows, "source_access_is_not_media_permission": True,
            "collection_attempted": False, "approvals_changed": False}


def workflow_readiness(store, objects, request, context):
    from packages.contracts.workflows import WORKFLOWS, PRIMITIVES
    family = request.get("workflow_family")
    workflow = next((item for item in WORKFLOWS if item["id"] == family), None)
    if workflow is None:
        raise ToolInputError("Choose a supported content workflow family.")
    if len(objects) < workflow["minimum_products"] or any(obj.object_type != "product" for obj in objects):
        raise ToolInputError("This workflow needs the required distinct product inputs.")
    if family == "comparison" and len({obj.payload.get("category") for obj in objects}) != 1:
        raise ToolInputError("A comparison requires products from the same category.")
    special = []
    if family == "commercial":
        special = ["approved_active_offer", "merchant_and_market_eligibility", "disclosure", "attribution_and_returns"]
    elif family == "change":
        special = ["dated_before_and_after_evidence", "variant_and_market_match"]
    return {"workflow": workflow, "input_versions": {obj.object_id: obj.version for obj in objects},
            "creative_direction": context["creative_direction"],
            "creative_settings": context["creative_settings"],
            "governed_memory": context["governed_memory"], "candidate_primitives": PRIMITIVES,
            "required_gates": ["source_policy", "factual_review", "image_rights", "background_music_rights",
                               "render_quality", "exact_video_and_metadata_human_approval", "spend_admission"],
            "additional_requirements": special, "publication_allowed": False,
            "script_generated": False, "render_started": False,
            "next_action": "Use the governed evidence and saved image-led/music-backed profile to prepare a reviewable draft."}


TOOLS = {"catalogue_coverage": catalogue_coverage,
         "source_policy_queue": source_policy_queue,
         "workflow_readiness": workflow_readiness}


def dispatch(store, request, context):
    from packages.intelligence.learning import assert_memory_current

    name = context["profile"]["tool"]
    if name not in TOOLS:
        raise ToolInputError("Tool is not allowlisted.")
    objects = pinned_objects(store, request, context)
    if "governed_memory" in context:
        assert_memory_current(store, context["governed_memory"])
    result = TOOLS[name](store, objects, request, context)
    return {"schema_version": "runtime-result-1", "tool": name, "execution": "deterministic",
            "input_versions": context["input_versions"], "context_is_pinned": True,
            "external_api_calls": 0, "external_variable_cost_cents": 0,
            "all_operating_costs_known": False, "proposal_only": True, "result": result}
