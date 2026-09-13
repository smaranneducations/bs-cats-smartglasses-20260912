from __future__ import annotations

from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from .governance import BASE_FIELD_MAP
from .object import ObjectStatus, UniversalObject
from .store import ContractViolationError

WORKFLOWS = [
    {"id": "category", "label": "Category guide", "question": "Which kind of glasses fits the job?", "minimum_products": 1},
    {"id": "product", "label": "Product profile", "question": "What does this product actually offer?", "minimum_products": 1},
    {"id": "feature", "label": "Feature explainer", "question": "What does one specification mean in practice?", "minimum_products": 1},
    {"id": "comparison", "label": "Matched comparison", "question": "How do comparable options differ?", "minimum_products": 2},
    {"id": "use_case", "label": "Use-case guide", "question": "Which requirements matter for this activity?", "minimum_products": 1},
    {"id": "value", "label": "Value and ownership", "question": "Which extras and unknown costs should a buyer check?", "minimum_products": 1},
    {"id": "change", "label": "Change or launch", "question": "What changed, supported by dated evidence?", "minimum_products": 1},
    {"id": "compatibility", "label": "Compatibility guide", "question": "What must the connected device support?", "minimum_products": 1},
    {"id": "question", "label": "Audience question", "question": "What should a buyer ask before ordering?", "minimum_products": 1},
    {"id": "myth", "label": "Claim investigation", "question": "Does the evidence support the claim?", "minimum_products": 1},
    {"id": "market", "label": "Market briefing", "question": "What can this limited selection tell us?", "minimum_products": 1},
    {"id": "commercial", "label": "Transparent offer", "question": "What is the offer, and who benefits?", "minimum_products": 1},
]
PRIMITIVES = ["question_hook", "product_card", "feature_callout", "comparison_table",
              "decision_map", "metric_card", "timeline", "compatibility_chain",
              "question_reveal", "evidence_note", "uncertainty_card", "takeaway"]


EVIDENCE_LABELS = {
    "manufacturer_stated": ("fact", "primary_manufacturer", "Manufacturer states", "Not independently tested."),
    "independent_test": ("fact", "independent_unassessed", "Independent source reports", "Recorded as an independent test; source quality and methodology need review."),
    "human_observation": ("fact", "anecdotal", "Human observation records", "An individual observation, not a general performance finding."),
    "inference": ("interpretation", "synthetic", "Analysis suggests", "An inference, not a directly measured specification."),
}


def project_field_claim(product, key, definitions):
    """Project one governed field independently of an editorial selection limit."""
    if product.object_type != "product" or product.status in {
        ObjectStatus.rejected, ObjectStatus.archived, ObjectStatus.deprecated,
    }:
        raise ContractViolationError("A current governed product is required.")
    field = product.payload.get("fields", {}).get(key)
    definition = definitions.get(key)
    if definition is None or not field or field.get("value") is None or not field.get("source_ids"):
        raise ContractViolationError("The claim requires a defined, populated, source-linked field.")
    category = getattr(definition.category, "value", definition.category)
    if category not in {"all", product.payload.get("category")}:
        raise ContractViolationError("The field definition does not apply to this product category.")
    if not set(field["source_ids"]).issubset({source.source_id for source in product.sources}):
        raise ContractViolationError("The claim has an unresolved source identity.")
    evidence_kind = field.get("evidence_kind", "manufacturer_stated")
    if evidence_kind not in EVIDENCE_LABELS:
        raise ContractViolationError("The field evidence kind is unsupported.")
    kind, tier, attribution, caveat = EVIDENCE_LABELS[evidence_kind]
    claim_id = "claim_" + sha256((product.object_id + ":" + key).encode()).hexdigest()[:24]
    value = str(field["value"]).lower() if isinstance(field["value"], bool) else str(field["value"])
    units = (" " + definition.unit) if definition.unit else ""
    claim = {
        "claim_id": claim_id,
        "statement": f"{attribution} for {product.title}: {definition.label} = {value}{units}.",
        "kind": kind, "source_ids": field["source_ids"], "evidence_tier": tier,
        "verification_state": "unverified", "confidence": field.get("confidence"),
        "caveats": [text for text in [field.get("conditions", ""), caveat,
            "Observation date: " + str(field.get("observed_at", "Unknown")),
            *product.payload.get("caveats", [])] if text],
        "freshness_check_required": True,
    }
    binding = {"object_id": product.object_id, "field_key": key,
        "observed_at": field.get("observed_at"), "evidence_kind": field.get("evidence_kind"),
        "definition": definition.model_dump(mode="json")}
    return claim, binding


def compose_brief(family, products, actor_id, request_key, definitions=None):
    workflow = next((w for w in WORKFLOWS if w["id"] == family), None)
    if not workflow or len(products) < workflow["minimum_products"]:
        raise ContractViolationError("Select a supported workflow and enough products.")
    if len({p.object_id for p in products}) != len(products) or any(p.object_type != "product" for p in products):
        raise ContractViolationError("Select distinct product records.")
    if any(p.status in {ObjectStatus.rejected, ObjectStatus.archived, ObjectStatus.deprecated} for p in products):
        raise ContractViolationError("Retired or rejected products cannot supply a new draft.")
    if family == "comparison" and len({p.payload["category"] for p in products}) != 1:
        raise ContractViolationError("Compare products from the same category.")
    if family == "change":
        raise ContractViolationError("A change story needs dated before-and-after evidence; this workflow is not ready.")
    if family == "commercial":
        raise ContractViolationError("A commercial story needs an approved offer and disclosure; no offer is active.")
    definitions = BASE_FIELD_MAP if definitions is None else definitions
    sources, claims, sections, claim_inputs = {}, [], [], {}
    for product in products:
        for source in product.sources:
            existing = sources.get(source.source_id)
            if existing is not None and existing.model_dump() != source.model_dump():
                raise ContractViolationError("Conflicting source identities require distinct source IDs.")
            sources[source.source_id] = source
        ids = []
        known = [(key, field) for key, field in product.payload.get("fields", {}).items()
                 if field.get("value") is not None and field.get("source_ids")]
        for key, field in known[:6]:
            claim, binding = project_field_claim(product, key, definitions)
            claim_id = claim["claim_id"]
            claims.append(claim)
            claim_inputs[claim_id] = binding
            ids.append(claim_id)
        sections.append({"heading": product.title, "objective": workflow["question"],
                         "claim_ids": ids, "talking_points": [product.payload["buyer_job"]]})
    if not claims:
        raise ContractViolationError("No sourced fields are available for a draft.")
    versions = {p.object_id: p.version for p in products}
    full_title = workflow["label"] + ": " + " / ".join(p.title for p in products)
    oid = "brief_" + uuid5(NAMESPACE_URL, actor_id + ":" + request_key).hex
    return UniversalObject(object_id=oid, object_type="content_brief",
        title=full_title if len(full_title) <= 240 else full_title[:237] + "...",
        purpose="Prepare a source-linked kinetic-text story for evidence and final-artifact review.",
        sources=list(sources.values()), parent_ids=list(versions),
        payload={"summary": workflow["question"], "claims": claims,
                 "entities": list(versions), "workflow_family": family, "input_versions": versions,
                 "duration_seconds": 90, "production_state": "needs_evidence_review",
                 "presentation": {"hook": workflow["question"],
                     "viewer_promise": "Understand the useful differences and what remains unknown.",
                     "sections": sections, "call_to_action": "Read the evidence and check fit before buying.",
                     "do_not_claim": ["Hands-on testing by this publisher", "Guaranteed value", "Worldwide availability", "An active affiliate relationship"]}},
        metadata={"full_title": full_title, "primitive_candidates": PRIMITIVES, "voice": "none",
                  "source_versions": versions, "claim_inputs": claim_inputs, "publication_allowed": False})
