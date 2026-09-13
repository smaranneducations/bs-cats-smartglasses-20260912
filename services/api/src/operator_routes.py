from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from packages.agents.registry import effective_roster, update_profile
from packages.domain_engine.profile import active_domain
from packages.governance.review_routing import classify_review

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "apps" / "operator"


class AgentProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())
    expected_version: int = Field(ge=0)
    instructions: str = Field(min_length=20, max_length=6000)
    model_tier: str = Field(pattern="^(deterministic|economical|balanced|strong)$")
    enabled: bool = True
    change_reason: str = Field(min_length=3, max_length=500)


def operator_router(get_store, require_access, can_edit):
    router = APIRouter(tags=["solo-operator"])

    @router.get("/operator", include_in_schema=False)
    def page():
        return FileResponse(ASSETS / "index.html", media_type="text/html")

    @router.get("/operator/app.js", include_in_schema=False)
    def javascript():
        return FileResponse(ASSETS / "operator-v1.js", media_type="text/javascript")

    @router.get("/operator/admin-auth.js", include_in_schema=False)
    def admin_auth_javascript():
        return FileResponse(ASSETS / "admin-auth.js", media_type="text/javascript")

    @router.get("/operator/stage-admin.js", include_in_schema=False)
    def stage_admin_javascript():
        return FileResponse(ASSETS / "stage-admin.js", media_type="text/javascript")

    @router.get("/operator/docs/platform-architecture.html", include_in_schema=False)
    def platform_architecture():
        return FileResponse(ROOT / "docs" / "architecture" / "platform-overview.html", media_type="text/html")

    @router.get("/operator/style.css", include_in_schema=False)
    def stylesheet():
        return FileResponse(ASSETS / "operator-v1.css", media_type="text/css")

    @router.get("/operator/vendor/{asset_name}", include_in_schema=False)
    def firebase_vendor_asset(asset_name: str):
        allowed = {"firebase-app-compat.js", "firebase-auth-compat.js", "FIREBASE-NOTICE.txt"}
        if asset_name not in allowed:
            raise HTTPException(404, "Unknown vendor asset.")
        media_type = "text/javascript" if asset_name.endswith(".js") else "text/plain"
        return FileResponse(ASSETS / "vendor" / asset_name, media_type=media_type)

    @router.get("/global-nav.js", include_in_schema=False)
    def global_navigation():
        return FileResponse(ASSETS / "global-nav.js", media_type="text/javascript")

    @router.get("/v1/operator/workflow")
    def workflow(_principal=Depends(require_access)):
        store = get_store()
        objects = store.list_objects()
        if len(objects) > 500:
            from fastapi import HTTPException
            raise HTTPException(422, "The operator view needs bounded pagination beyond 500 objects.")
        counts = Counter(item.object_type for item in objects)
        definitions = store.definitions()
        domain = active_domain()
        creative = json.loads((ROOT / "config" / "creative-direction.json").read_text(encoding="utf-8"))
        capabilities = json.loads((ROOT / "config" / "external-capabilities.json").read_text(encoding="utf-8"))
        pending = []
        for item in objects:
            route = classify_review(item)
            status = getattr(item.status, "value", str(item.status))
            if route.required and status in {"captured", "proposed"}:
                pending.append({
                    "object_id": item.object_id,
                    "version": item.version,
                    "title": item.title,
                    "object_type": item.object_type,
                    "category": route.category,
                    "reason": route.reason,
                })

        research_count = sum(counts[name] for name in ("source_policy", "research_capture", "evidence", "source", "product"))
        content_count = sum(counts[name] for name in ("content_brief", "content_card", "card_bundle", "storyboard", "shorts_plan"))
        generated_count = sum(counts[name] for name in ("storyboard", "shorts_plan", "render", "media_artifact", "video"))
        feedback_count = sum(counts[name] for name in ("feedback", "interaction", "engagement_event", "decision_proposal"))
        release_count = sum(counts[name] for name in ("publication_request", "publication_decision", "release_authorization"))
        products = [{"object_id": item.object_id, "version": item.version, "title": item.title, "status": item.status.value, "market": item.payload.get("market"), "variant": item.payload.get("variant"), "field_count": len(item.payload.get("fields", {}))} for item in objects if item.object_type == "product"]
        ontology = [{"key": key, **definition.model_dump(mode="json")} for key, definition in definitions.items()]
        source_policies = [{"object_id": item.object_id, "version": item.version, "title": item.title, "commercial_reuse": item.payload.get("commercial_reuse"), "media_reuse": item.payload.get("media_reuse"), "automation": item.payload.get("automation"), "summary": item.payload.get("summary", item.purpose)} for item in objects if item.object_type == "source_policy"]
        content = [{"object_id": item.object_id, "version": item.version, "object_type": item.object_type, "title": item.title, "status": item.status.value, "summary": item.payload.get("summary", item.purpose)} for item in objects if item.object_type in {"content_brief", "content_card", "card_bundle", "storyboard", "shorts_plan"}]
        artifacts = [{"object_id": item.object_id, "version": item.version, "title": item.title, "status": item.status.value, "duration_seconds": item.payload.get("duration_seconds"), "publication_allowed": item.payload.get("publication_allowed", False), "rights_gate": item.payload.get("rights_gate"), "factual_gate": item.payload.get("factual_gate")} for item in objects if item.object_type == "render_artifact"]
        feedback = [{"object_id": item.object_id, "version": item.version, "title": item.title, "classification": item.payload.get("classification"), "summary": item.payload.get("summary", item.purpose), "status": item.status.value} for item in objects if item.object_type in {"feedback", "decision_record"}][-30:]

        stages = [
            {"id": "domain", "number": "01", "label": "Define the domain", "state": "ready", "evidence": f"{domain.label} / pack v{domain.version}", "agent": "Loads the domain pack, validates its identity rules, buyer jobs, source classes and commercial paths.", "human": "Only if you want to replace the domain or materially change its business objective.", "action": "Inspect active domain", "href": "#domain"},
            {"id": "research", "number": "02", "label": "Research and enrich", "state": "ready" if research_count else "active", "evidence": f"{research_count} research and catalogue objects", "agent": "Finds permitted sources, captures evidence, extracts fields, normalizes units and resolves routine gaps.", "human": "Only for inaccessible firsthand knowledge, unresolved rights or consequential source conflicts.", "action": "See research status", "href": "/intelligence#knowledge"},
            {"id": "ontology", "number": "03", "label": "Shape the ontology", "state": "ready" if definitions else "active", "evidence": f"{len(definitions)} active semantic definitions", "agent": "Proposes reusable concepts, relationships, units and generated forms from recurring data needs.", "human": "Only for meaning-changing or breaking proposals; you may add a missing concept whenever useful.", "action": "Review ontology exceptions", "href": "#exceptions"},
            {"id": "dataset", "number": "04", "label": "Grow the dataset", "state": "ready" if counts["product"] else "active", "evidence": f"{counts['product']} product records", "agent": "Maintains versions, provenance, refresh plans, confidence reasons and correction impact automatically.", "human": "Only when an important ambiguity cannot be resolved or safely left unknown.", "action": "Explore the dataset", "href": "/intelligence#knowledge"},
            {"id": "direction", "number": "05", "label": "Set the creative system", "state": "ready", "evidence": f"{len(domain.payload['content_lenses'])} content lenses configured", "agent": "Turns buyer jobs, evidence and your standing creative instructions into reusable themes and formats.", "human": "Set or revise the standing voice, visual style, audience promise and commercial boundaries, not every post.", "action": "Open content direction", "href": "/#content"},
            {"id": "generate", "number": "06", "label": "Generate content", "state": "ready" if content_count else "active", "evidence": f"{content_count} content plans / {generated_count} generated artifacts", "agent": "Composes image-led cards, comparisons, reports and Shorts from governed assertions and licensed assets.", "human": "No draft approval. The agent fixes routine quality failures and only escalates a real unresolved blocker.", "action": "Open generation studio", "href": "/#content"},
            {"id": "release", "number": "07", "label": "Review and publish", "state": "active" if generated_count else "waiting", "evidence": f"{release_count} exact release decisions", "agent": "Builds one final packet containing the exact artifact, metadata, evidence, rights, cost and destination.", "human": "Approve or reject that exact final publication. Broad autonomy never publishes an unseen artifact.", "action": "Open final decisions", "href": "/#review"},
            {"id": "learn", "number": "08", "label": "Learn and improve", "state": "ready" if feedback_count else "waiting", "evidence": f"{feedback_count} feedback and learning objects", "agent": "Measures useful engagement, classifies feedback, proposes corrections and propagates approved changes.", "human": "Give strategic feedback or resolve only the prepared exceptions that can materially improve the system.", "action": "Open learning loop", "href": "/#learning"},
        ]
        current = next((stage["id"] for stage in stages if stage["state"] in {"active", "waiting"}), "learn")
        return {
            "schema_version": "solo-operator-workflow-1",
            "domain": domain.public_dict(),
            "stages": stages,
            "current_stage": current,
            "exceptions": pending,
            "counts": dict(counts),
            "creative_direction": creative,
            "capabilities": capabilities,
            "products": products,
            "ontology": ontology,
            "source_policies": source_policies,
            "content": content,
            "artifacts": artifacts,
            "feedback": feedback,
            "agent_roster": effective_roster(store),
            "operating_rule": "Audit everything. Automate routine work. Ask the human only for consequential exceptions and exact publication.",
        }

    @router.post("/v1/operator/agents/{agent_id}")
    def save_agent(agent_id: str, request: AgentProfileUpdate, principal=Depends(can_edit), idempotency_key: str | None = Header(None, alias="Idempotency-Key")):
        try:
            return update_profile(get_store(), agent_id, expected_version=request.expected_version, instructions=request.instructions, model_tier=request.model_tier, enabled=request.enabled, change_reason=request.change_reason, actor_id=principal.actor_id, actor_type=principal.actor_type, idempotency_key=idempotency_key)
        except KeyError:
            raise HTTPException(404, "Unknown agent profile.") from None
        except RuntimeError as exc:
            raise HTTPException(409, str(exc)) from None
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    return router
