from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from packages.contracts import ActorType, CurationPatch, UniversalObject
from packages.domain_engine.profile import active_domain

ROOT = Path(__file__).resolve().parents[2]
ROSTER_PATH = ROOT / "config" / "agent-roster.json"
TIERS = {"deterministic", "economical", "balanced", "strong"}
SECRET_PATTERN = re.compile(r"(?:sk-[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{20,}|(?:password|token|secret)\s*[=:]\s*\S+)", re.I)


def _base() -> dict[str, Any]:
    return json.loads(ROSTER_PATH.read_text(encoding="utf-8"))


def effective_roster(store) -> dict[str, Any]:
    roster = _base()
    overrides = {item.payload.get("agent_id"): item for item in store.list_objects() if item.object_type == "agent_profile"}
    agents = []
    for base in roster["agents"]:
        saved = overrides.get(base["agent_id"])
        profile = {**base, **(saved.payload if saved else {})}
        profile["object_id"] = saved.object_id if saved else f"agent_profile_{base['agent_id']}"
        profile["object_version"] = saved.version if saved else 0
        agents.append(profile)
    return {**roster, "agents": agents}


def update_profile(store, agent_id: str, *, expected_version: int, instructions: str, model_tier: str, enabled: bool, change_reason: str, actor_id: str, actor_type: ActorType, idempotency_key: str | None = None) -> dict[str, Any]:
    roster = effective_roster(store)
    current = next((item for item in roster["agents"] if item["agent_id"] == agent_id), None)
    if current is None:
        raise KeyError(agent_id)
    if current["object_version"] != expected_version:
        raise RuntimeError("Agent profile changed; reload before saving.")
    if model_tier not in TIERS:
        raise ValueError("Unsupported model tier.")
    if SECRET_PATTERN.search(instructions) or SECRET_PATTERN.search(change_reason):
        raise ValueError("Agent instructions cannot contain credentials or token values.")
    payload = {key: value for key, value in current.items() if key not in {"object_id", "object_version"}}
    payload.update({"instructions": instructions.strip(), "model_tier": model_tier, "enabled": enabled, "change_reason": change_reason.strip()})
    object_id = current["object_id"]
    existing = next((item for item in store.list_objects() if item.object_id == object_id), None)
    if existing:
        saved = store.curate(object_id, CurationPatch(payload=payload, metadata={"control_scope": "instructions_model_tier_and_disable_only"}), actor_id=actor_id, actor_type=actor_type, expected_version=expected_version, idempotency_key=idempotency_key)
    else:
        saved = store.capture(UniversalObject(object_id=object_id, object_type="agent_profile", domain=active_domain().domain_id.replace("-", "_"), title=f"Agent profile: {current['label']}", purpose="Version the operator-visible instructions and routing preference for a task-scoped agent role.", payload=payload, metadata={"control_scope": "instructions_model_tier_and_disable_only"}), actor_id=actor_id, actor_type=actor_type, idempotency_key=idempotency_key)
    return next(item for item in effective_roster(store)["agents"] if item["agent_id"] == saved.payload["agent_id"])
