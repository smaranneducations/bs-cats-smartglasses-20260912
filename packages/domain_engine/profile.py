"""Load a domain pack without coupling the engine to its subject matter."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DOMAIN_ROOT = ROOT / "config" / "domains"
ACTIVE_DOMAIN = ROOT / "config" / "active-domain.json"


@dataclass(frozen=True)
class DomainProfile:
    domain_id: str
    version: str
    label: str
    primary_entity_type: str
    payload: dict[str, Any]

    def public_dict(self) -> dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "version": self.version,
            "label": self.label,
            "primary_entity_type": self.primary_entity_type,
            "buyer_jobs": self.payload["buyer_jobs"],
            "content_lenses": self.payload["content_lenses"],
            "workflow_roles": [item["role_id"] for item in self.payload["workflow_roles"]],
        }


def load_domain(domain_id: str) -> DomainProfile:
    if not domain_id or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for char in domain_id):
        raise ValueError("domain_id must be a lowercase filesystem-safe identifier")
    path = DOMAIN_ROOT / f"{domain_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {"domain_id", "version", "label", "primary_entity_type", "ontology", "buyer_jobs", "content_lenses", "workflow_roles", "source_classes", "commercial_paths"}
    missing = sorted(required - set(data))
    if missing:
        raise ValueError("Domain pack is incomplete: " + ", ".join(missing))
    if data["domain_id"] != domain_id:
        raise ValueError("Domain filename and domain_id must match")
    if not data["ontology"] or not data["buyer_jobs"] or not data["workflow_roles"]:
        raise ValueError("A domain pack needs ontology, buyer jobs, and workflow roles")
    forbidden = {key for key in data if "secret" in key.lower() or "token" in key.lower() or "password" in key.lower()}
    if forbidden:
        raise ValueError("Domain packs cannot contain credentials")
    return DomainProfile(domain_id, str(data["version"]), str(data["label"]), str(data["primary_entity_type"]), data)


def active_domain() -> DomainProfile:
    selector = json.loads(ACTIVE_DOMAIN.read_text(encoding="utf-8"))
    return load_domain(str(selector["domain_id"]))
