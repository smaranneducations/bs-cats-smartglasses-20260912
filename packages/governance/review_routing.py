"""Route only consequential exceptions to a human decision.

Auditability is universal; human approval is not. This classifier uses explicit
typed boundaries instead of a confidence threshold, so an ordinary unknown can
remain unknown without becoming founder administration.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ReviewRoute:
    required: bool
    category: str
    reason: str
    rule_id: str

    @property
    def display_state(self) -> str:
        return "exception_required" if self.required else "policy_routed"

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


_RESERVED_TYPES = {
    "field_definition": ("ontology", "A shared semantic definition changes generated forms and downstream meaning."),
    "publication_request": ("publication", "The exact public action needs account-holder authorization."),
    "publication_decision": ("publication", "The exact public action needs account-holder authorization."),
    "release_authorization": ("publication", "The exact artifact and metadata need publication authorization."),
    "spend_authorization": ("financial", "A new paid commitment needs financial-owner authorization."),
    "budget_change": ("financial", "Changing the spending envelope needs financial-owner authorization."),
    "credential_transfer": ("security", "Moving or expanding credential access needs account-holder authorization."),
    "account_consent": ("account", "Provider consent can only be completed by the account holder."),
    "contract_acceptance": ("legal", "Accepting external terms or a contract is a reserved human action."),
}


def _value(payload: dict[str, Any], *keys: str) -> str:
    return " ".join(str(payload.get(key, "")).strip().lower() for key in keys)


def classify_review(item: Any, *, operation: str = "observe") -> ReviewRoute:
    payload = dict(getattr(item, "payload", {}) or {})
    object_type = str(getattr(item, "object_type", "") or "").lower()
    if object_type in _RESERVED_TYPES:
        category, reason = _RESERVED_TYPES[object_type]
        return ReviewRoute(True, category, reason, f"reserved:{object_type}")
    if payload.get("human_review_required") is True:
        return ReviewRoute(True, str(payload.get("review_category") or "explicit_exception"), str(payload.get("review_reason") or "A workflow raised a bounded human exception."), "explicit_exception")
    decision = _value(payload, "decision_type", "kind", "proposal_type", "change_class")
    if any(term in decision for term in ("publish", "release_authorization", "spend", "budget_increase", "contract", "credential")):
        return ReviewRoute(True, "reserved_decision", "This proposal crosses a public, financial, legal, or access boundary.", "reserved_decision")
    if payload.get("breaking_change") is True or payload.get("meaning_change") is True or payload.get("permission_expansion") is True:
        return ReviewRoute(True, "ontology_or_policy", "The change expands authority or changes shared meaning.", "material_change")
    evidence_state = _value(payload, "evidence_state", "conflict_state", "validation_state", "source_state")
    consequential = payload.get("consequential") is True or payload.get("decision_critical") is True
    if consequential and any(term in evidence_state for term in ("conflict", "contradict", "unresolved", "failed")):
        return ReviewRoute(True, "evidence_conflict", "Consequential evidence remains conflicting after bounded resolution attempts.", "consequential_conflict")
    rights_state = _value(payload, "rights_state", "permission_state", "commercial_reuse", "license_state")
    if any(term in rights_state for term in ("unresolved", "unknown", "denied", "expired", "restricted")) and payload.get("rights_question_resolved") is not True:
        return ReviewRoute(True, "rights_and_legal", "Intended reuse is blocked by an unresolved rights or permission question.", "unresolved_rights")
    if payload.get("account_holder_action_required") is True:
        return ReviewRoute(True, "account", "The next step requires identity, consent, or provider access unavailable to the agent.", "account_holder_action")
    if payload.get("exact_artifact_publication_candidate") is True:
        return ReviewRoute(True, "publication", "The final artifact and exact metadata are ready for a publication decision.", "exact_artifact")
    return ReviewRoute(False, "automatic", "Routine policy-conforming internal work is audit-logged and monitored without human approval.", f"routine:{operation}")
