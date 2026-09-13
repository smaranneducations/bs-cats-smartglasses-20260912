#!/usr/bin/env python3
"""Recommend a development model locally. No credentials, network or writes."""

import argparse
import json
import math
from pathlib import Path


POLICY_PATH = Path(__file__).resolve().parents[1] / "config" / "model-routing.json"


def load_policy():
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def advise(task, risk="low", failed_attempts=0, available_models=None,
           remaining_usage_percent=None, policy=None):
    policy = load_policy() if policy is None else policy
    if task not in policy["task_tiers"]:
        raise ValueError("Unknown task family; classify the task before routing.")
    if risk not in policy["risk_floors"]:
        raise ValueError("Unknown risk level.")
    if isinstance(failed_attempts, bool) or not isinstance(failed_attempts, int) or failed_attempts < 0:
        raise ValueError("failed_attempts must be a nonnegative integer.")
    if remaining_usage_percent is not None:
        if (isinstance(remaining_usage_percent, bool)
                or not isinstance(remaining_usage_percent, (int, float))
                or not math.isfinite(remaining_usage_percent)
                or not 0 <= remaining_usage_percent <= 100):
            raise ValueError("remaining_usage_percent must be finite and between 0 and 100.")
    if available_models is not None and (
        not isinstance(available_models, (list, tuple, set))
        or any(not isinstance(model, str) for model in available_models)
    ):
        raise ValueError("available_models must be a collection of model identifiers.")

    result = {
        "policy_version": policy["version"],
        "task": task,
        "risk": risk,
        "failed_attempts": failed_attempts,
        "action": None,
        "tier": None,
        "model": None,
        "reasoning_effort": None,
        "reason": None,
        "advisory_only": True,
        "model_switched": False,
        "api_calls_made": 0,
        "pricing_verified": False,
        "availability_verified": available_models is not None,
    }
    limits = policy["limits"]
    if failed_attempts >= limits["max_attempts_per_task"]:
        result.update(action="stop_and_replan", reason="Attempt limit reached. Resolve the cause before scheduling more work.")
        return result

    base = policy["task_tiers"][task]
    if base == "deterministic" and risk == "low" and failed_attempts == 0:
        result.update(action="use_deterministic_tool", tier="deterministic", reason="This bounded operation needs no language model.")
        return result

    order = policy["tier_order"]
    # A failed deterministic operation needs diagnosis, not repeated execution.
    if base == "deterministic":
        base = "balanced"
    tier_index = max(order.index(base), order.index(policy["risk_floors"][risk]))
    if failed_attempts >= limits["escalate_after_failed_attempts"]:
        tier_index = min(tier_index + 1, len(order) - 1)
    tier = order[tier_index]
    result["tier"] = tier

    if remaining_usage_percent is not None:
        if remaining_usage_percent == 0 or (
            remaining_usage_percent <= limits["low_usage_remaining_percent"]
            and tier != "economy"
        ):
            result.update(action="defer_model_work", reason="Conserve remaining capacity without lowering the quality floor. Continue suitable deterministic work.")
            return result

    route = policy["tiers"][tier]
    candidates = route["models"]
    if available_models is not None:
        candidates = [model for model in candidates if model in available_models]
    if not candidates:
        result.update(action="resolve_model_availability", reason="No approved model in the required tier is available. Do not silently downgrade or buy capacity.")
        return result

    reason = "Initial task-fit recommendation; measure accepted-result quality and cost."
    if failed_attempts == 1:
        reason += " Make one targeted repair before escalation."
    elif failed_attempts >= limits["escalate_after_failed_attempts"]:
        reason += " Final bounded attempt after repeated quality failure; other blockers need their own remedy."
    result.update(
        action="recommend_model",
        model=candidates[0],
        reasoning_effort=route["reasoning_effort"],
        reason=reason,
        suggested_limits={
            "max_output_tokens": route["max_output_tokens"],
            "max_tool_calls": route["max_tool_calls"],
            "attempts_remaining": limits["max_attempts_per_task"] - failed_attempts,
        },
    )
    return result


def main():
    policy = load_policy()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=sorted(policy["task_tiers"]))
    parser.add_argument("--risk", choices=sorted(policy["risk_floors"]), default="low")
    parser.add_argument("--failed-attempts", type=int, default=0)
    parser.add_argument("--remaining-usage-percent", type=float)
    parser.add_argument("--available-models", nargs="*", default=None)
    args = parser.parse_args()
    try:
        result = advise(args.task, args.risk, args.failed_attempts,
                        args.available_models, args.remaining_usage_percent, policy)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
