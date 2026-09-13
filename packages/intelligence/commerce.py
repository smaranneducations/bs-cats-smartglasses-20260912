"""Deterministic commerce evidence assessment over governed object snapshots."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any

from packages.contracts.commerce_assessment import CommercialEvidencePayload, CommerceAssessmentPayload, GateAssessment, PathAssessment

EVIDENCE_GATES = ("checkout", "publisher_approval", "product_eligibility", "editorial_independence", "commercial_reuse", "attribution", "payment")
EXPLANATIONS = {
    "checkout": "A product page or buy button does not demonstrate a destination-specific checkout path.",
    "publisher_approval": "A public program listing, application or invitation is not our publisher approval.",
    "product_eligibility": "Confirm the exact smart-glasses products, market and permitted channel under the applicable terms.",
    "editorial_independence": "Assess endorsement, content-editing and promotional obligations against editorial independence.",
    "commercial_reuse": "Document the commercial permissions needed for this path; this does not clear every future asset.",
    "attribution": "Document permitted tracking, attribution windows, exclusions and reversals.",
    "payment": "Document contractual payout conditions; marketing rates are not collected revenue.",
}


def _instant(value: Any) -> datetime:
    result = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("An observation timezone is required")
    return result


def _fingerprint(records: list[dict[str, Any]]) -> str:
    selected = [{key: record.get(key) for key in ("object_id", "version", "status", "review", "payload", "sources")} for record in sorted(records, key=lambda item: item["object_id"])]
    return hashlib.sha256(json.dumps({"policy": "commerce-readiness-1", "inputs": selected}, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def assess_commerce(paths: list[dict[str, Any]], evidence: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    from packages.contracts.governance import PAYLOAD_TYPES

    if now.tzinfo is None or not 1 <= len(paths) <= 4:
        raise ValueError("Assess one to four paths with an explicit observation time")
    if len({path["object_id"] for path in paths}) != len(paths):
        raise ValueError("Duplicate commercial paths are not allowed")
    if len(evidence) > 100:
        raise ValueError("Commercial evidence history exceeds this bounded assessment")
    inputs = list(paths)
    sources: dict[str, dict[str, Any]] = {}
    results = []
    expiry = now + timedelta(hours=1)
    for path in sorted(paths, key=lambda record: record["object_id"]):
        payload = PAYLOAD_TYPES["commerce_path"].model_validate(path["payload"])
        gates = []
        source_map = {item["source_id"]: item for item in path.get("sources", []) if item.get("source_id")}
        source_ids = payload.evidence_source_ids
        fresh = bool(source_ids) and set(source_ids).issubset(source_map)
        freshness_reason = "Current dated source references are present; freshness alone does not establish accuracy or reuse rights."
        try:
            observations = [payload.observed_at] + [_instant(source_map[key]["captured_at"]) for key in source_ids if key in source_map]
            for observed in observations:
                fresh = fresh and timedelta(minutes=-1) <= now - observed < timedelta(days=30)
                if observed + timedelta(days=30) > now:
                    expiry = min(expiry, observed + timedelta(days=30))
        except (KeyError, TypeError, ValueError):
            fresh = False
        if not fresh:
            freshness_reason = "Source references are absent, stale, future-dated or incomplete; refresh the evidence first."
        gates.append(GateAssessment(gate="source_freshness", state="clear" if fresh else "unknown", reason=freshness_reason))
        review_state = path.get("review", {}).get("state")
        retired = path.get("status") in {"deprecated", "rejected", "archived"}
        gates.append(GateAssessment(gate="record_review", state="blocked" if retired or review_state == "rejected" else "clear" if review_state == "approved" else "unknown", reason="The exact path version needs human review; this assessment cannot approve it." if review_state != "approved" else "The recorded path review is approved; publication remains a separate decision."))
        candidates = [record for record in evidence if record.get("payload", {}).get("path_id") == path["object_id"]]
        chosen = max(candidates, key=lambda record: (_instant(record.get("updated_at", record.get("recorded_at"))), record["object_id"])) if candidates else None
        proof = None
        proof_reason = "No reviewed, current, version-matched commercial evidence is attached."
        if chosen is not None:
            inputs.append(chosen)
            proof_candidate = CommercialEvidencePayload.model_validate(chosen["payload"])
            if chosen.get("review", {}).get("state") == "approved" and chosen.get("status") not in {"deprecated", "rejected", "archived"} and proof_candidate.path_version == path["version"] and proof_candidate.checked_at <= now < proof_candidate.recheck_after:
                proof = proof_candidate
                expiry = min(expiry, proof.recheck_after)
            else:
                proof_reason = "The latest commercial evidence is unreviewed, expired, retired or bound to a different path version."
        proof_sources = {item["source_id"]: item for item in (chosen or {}).get("sources", []) if item.get("source_id")}
        findings = {item.gate: item for item in proof.findings} if proof is not None else {}
        for gate in EVIDENCE_GATES:
            finding = findings.get(gate)
            state = "unknown"
            reason = EXPLANATIONS[gate] + " " + proof_reason
            if finding is not None and set(finding.evidence_source_ids).issubset(proof_sources):
                state = {"clear": "clear", "not_clear": "blocked", "unknown": "unknown"}[finding.finding]
                reason = finding.rationale
            if gate == "publisher_approval" and payload.publisher_access != "approved":
                state = "blocked" if payload.publisher_access == "rejected" else "unknown"
                reason = EXPLANATIONS[gate] + " Current access state: " + payload.publisher_access + "."
            if gate == "checkout" and payload.checkout != "observed":
                state = "unknown"
                reason = EXPLANATIONS[gate]
            gates.append(GateAssessment(gate=gate, state=state, reason=reason[:500], evidence_object_id=chosen["object_id"] if chosen is not None else None))
        if any(gate.state == "blocked" for gate in gates):
            stage = "blocked_by_evidence"
        elif all(gate.state == "clear" for gate in gates):
            stage = "ready_for_exact_artifact_review"
        else:
            stage = "awaiting_evidence"
        results.append(PathAssessment(path_id=path["object_id"], path_version=path["version"], title=path["title"], customer_market=payload.customer_market, stage=stage, gates=gates, next_agent_action="Prepare missing source and terms evidence; do not forecast income or issue tracked links from a marketing page.", reserved_human_boundary="Only the account holder may approve agreements or eligibility actions; exact-artifact publication approval remains separate."))
        for key in source_ids:
            if key in source_map:
                sources[key] = source_map[key]
        for key, value in proof_sources.items():
            sources[key] = value
    if len(sources) > 40:
        raise ValueError("Select fewer paths to preserve every source within the governed capture limit")
    assessment = CommerceAssessmentPayload(summary="Readiness of the selected commercial paths, based on governed evidence rather than expected commissions or traffic.", assessed_at=now, valid_until=expiry, input_versions={record["object_id"]: record["version"] for record in inputs}, input_fingerprint=_fingerprint(inputs), paths=results)
    return {"assessment": assessment.model_dump(mode="json"), "sources": list(sources.values()), "scope": "selected commercial paths, not proof of audience demand or collected revenue"}
