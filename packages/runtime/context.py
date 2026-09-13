from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SECRET_PATTERNS = re.compile(
    r"(?:-----BEGIN [A-Z ]*PRIVATE KEY-----|\bsk-(?:proj-)?[A-Za-z0-9_-]{18,}|"
    r"\bGOCSPX-[A-Za-z0-9_-]+|\bAIza[A-Za-z0-9_-]{20,}|"
    r"\b(?:access_token|refresh_token|client_secret|api_key|password)\s*[=:]\s*\S+)",
    re.IGNORECASE,
)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def reject_obvious_credentials(value):
    if SECRET_PATTERNS.search(canonical(value)):
        raise ValueError("Possible credential content is not accepted as runtime context.")


def load_profile(profile_id):
    document = json.loads((ROOT / "config/runtime-profiles.json").read_text())
    profile = document["profiles"].get(profile_id)
    if profile is None or profile.get("execution") != "deterministic":
        raise ValueError("The requested executable profile is unavailable.")
    if profile.get("external_cost_cents") != 0:
        raise ValueError("This runtime has no paid provider adapter.")
    return profile


def execution_context(task, profile):
    from packages.intelligence.learning import creative_settings, retrieve_memory
    from services.api.src.main import get_store

    creative = json.loads((ROOT / "config/creative-direction.json").read_text())
    memory = retrieve_memory(get_store(), task.workflow_family, [item.object_id for item in task.inputs])
    context = {
        "schema_version": "execution-context-1",
        "charter_version": task.charter_version,
        "profile_id": task.profile_id,
        "profile_revision": task.profile_revision,
        "profile": profile,
        "creative_direction": creative,
        "creative_settings": creative_settings(creative, memory),
        "governed_memory": memory,
        "input_versions": {item.object_id: item.version for item in task.inputs},
        "constraints": {
            "external_network": False,
            "provider_api_calls": False,
            "publication": False,
            "production_policy_mutation": False,
            "credential_access": False,
            "result_is_proposal": True,
        },
        "memory_basis": "Versioned configuration, pinned objects, and human-reviewed scoped decisions; not raw conversations or self-granted permissions.",
        "automatic_learning_promotion": False,
    }
    reject_obvious_credentials(context)
    return context
