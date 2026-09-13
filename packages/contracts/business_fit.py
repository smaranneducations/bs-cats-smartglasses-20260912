"""Conservative feasibility assessment; this is not a revenue forecast."""
from __future__ import annotations

from typing import Literal

from pydantic import Field

from .object import StrictContract

FIT_GATES = {
    "online_operations": "Our operations can be delivered remotely",
    "international_usefulness": "The buyer problem is useful beyond the source country",
    "online_checkout": "The buyer has an evidenced online purchase path",
    "publisher_revenue_access": "We can actually access the proposed earning mechanism",
    "commercial_data_rights": "The intended factual reuse is cleared",
    "credible_coverage": "Evidence covers the promised buyer decision",
    "authorized_media": "The planned visuals have an authorized repeatable path",
    "bounded_maintenance": "Catalogue and refresh effort are manageable",
    "budget_admission": "Costs are reconciled and the experiment is affordable",
    "demand_evidence": "There is evidence of demand for the proposed offer",
}


class GateEvidence(StrictContract):
    status: Literal["pass", "pending", "fail"] = "pending"
    reason: str = Field(min_length=1, max_length=2000)
    source_ids: list[str] = Field(default_factory=list)


def assess_fit(evidence: dict[str, GateEvidence | dict]) -> dict:
    """Unknown gates remain pending; an attractive score cannot cancel a failure.

    This assessment is advisory, not a runtime permission or a revenue forecast.
    Source, spending and publication admission remain separate controls.
    """
    unknown = set(evidence) - set(FIT_GATES)
    if unknown:
        raise ValueError("Unrecognized fit gates: " + ", ".join(sorted(unknown)))
    gates = {}
    for key, label in FIT_GATES.items():
        observation = GateEvidence.model_validate(
            evidence.get(key, {"status": "pending", "reason": "Evidence not recorded."})
        )
        gates[key] = {"label": label, **observation.model_dump(mode="json")}
    failed = [key for key, value in gates.items() if value["status"] == "fail"]
    pending = [key for key, value in gates.items() if value["status"] == "pending"]
    return {
        "model_version": "online-fit-1",
        "outcome": "blocked" if failed else "pending" if pending else "eligible_for_bounded_experiment",
        "failed_gates": failed, "pending_gates": pending, "gates": gates,
        "revenue_forecast": None, "permission_to_spend": False, "permission_to_publish": False,
    }
