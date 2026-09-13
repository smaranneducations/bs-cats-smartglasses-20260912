"""Explicit allowlisted projection; never export raw conversations or configuration."""

from datetime import UTC, datetime
from hashlib import sha256
import json

from .schema import TABLES

EXPORT_TYPES = {"product", "source_policy", "field_definition", "content_brief", "storyboard", "video_script",
                "content_card", "card_bundle", "shorts_plan"}
RETIRED = {"archived", "rejected", "deprecated"}


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                             allow_nan=False, default=str).encode()).hexdigest()


def scalar(value):
    return value.value if hasattr(value, "value") else value


def stamp(value):
    if value is None:
        return None
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Knowledge timestamps require a timezone.")
    return parsed.astimezone(UTC).isoformat()


def source_key(source):
    return "source_" + digest([source.source_id, source.uri])[:32]


def evidence_key(source):
    return "evidence_ref_" + digest([source_key(source), stamp(source.captured_at)])[:32]


def definition_rows(definitions, recorded_at):
    rows = {name: [] for name in TABLES}
    for definition in definitions:
        data = definition.model_dump(mode="json")
        key = "concept_" + definition.key
        fingerprint = digest(data)
        base = {"row_id": key + ":" + fingerprint, "recorded_at": recorded_at,
                "concept_id": key, "definition_hash": fingerprint}
        rows["semantic_concepts"].append(base | {
            "canonical_name": definition.label, "category": definition.category,
            "value_type": definition.value_type, "canonical_unit": definition.unit, "status": "active"})
        rows["semantic_definitions"].append(base | {
            "definition": definition.description, "constraints": data,
            "origin": "Current code registry plus approved custom field definitions; not a reconstructed historical ontology."})
        for name in ["minimum", "maximum"]:
            bound = data.get(name)
            if bound is not None:
                rid = key + ":" + fingerprint + ":" + name
                rows["semantic_rules"].append({"row_id": rid, "recorded_at": recorded_at,
                    "rule_id": rid, "concept_id": key, "rule_type": name,
                    "parameters": {"value": bound}, "severity": "error", "definition_hash": fingerprint})
    return rows


def project_record(record, definitions):
    item = record.snapshot
    rows = {name: [] for name in TABLES}
    if item.object_type not in EXPORT_TYPES:
        return rows
    when = stamp(record.event.occurred_at)
    base = {"recorded_at": when}
    rows["operations_change_events"].append(base | {
        "row_id": f"{item.object_id}:{item.version}", "object_id": item.object_id,
        "object_type": item.object_type, "object_version": item.version,
        "event_type": scalar(record.event.event_type), "actor_id": record.event.actor_id,
        "actor_type": scalar(record.event.actor_type), "snapshot_sha256": digest(item.model_dump(mode="json"))})
    refs = {source.source_id: source for source in item.sources}
    for source in item.sources:
        sid, eid = source_key(source), evidence_key(source)
        rows["evidence_sources"].append(base | {"row_id": sid + ":" + digest(source.model_dump(mode="json")),
            "source_id": sid, "local_source_id": source.source_id, "uri": source.uri,
            "title": source.title, "publisher": source.publisher,
            "policy_state": "Not inferred from public accessibility; consult the source policy."})
        rows["evidence_items"].append(base | {"row_id": eid, "evidence_id": eid, "source_id": sid,
            "captured_at": stamp(source.captured_at), "evidence_kind": "source_reference_only",
            "content_sha256": None, "artifact_uri": None, "notes": source.notes})
    if item.object_type == "product":
        payload = item.payload
        rows["catalog_products"].append(base | {
            "row_id": f"{item.object_id}:{item.version}", "product_id": item.object_id,
            "object_version": item.version, "brand": payload["brand"], "model": item.title,
            "category": payload["category"], "market": payload["market"],
            "variant": payload.get("variant"), "buyer_job": payload.get("buyer_job"),
            "status": scalar(item.status), "review_state": scalar(item.review.state)})
        for key, assertion in payload.get("fields", {}).items():
            definition = definitions.get(key)
            if definition is None:
                raise ValueError(f"Unknown concept {key}; map or propose it before projection.")
            ids = assertion.get("source_ids", [])
            if any(sid not in refs for sid in ids):
                raise ValueError(f"Unresolved source reference on {item.object_id}:{key}.")
            value = assertion.get("value")
            if value is not None and not isinstance(value, (bool, int, float, str)):
                raise ValueError("Unsupported assertion value type.")
            aid = "assertion_" + digest([item.object_id, item.version, key])[:32]
            rows["catalog_assertions"].append(base | {
                "row_id": aid, "assertion_id": aid, "subject_id": item.object_id,
                "object_version": item.version, "concept_id": "concept_" + key,
                "definition_hash": digest(definition.model_dump(mode="json")),
                "value_number": value if isinstance(value, (int, float)) and not isinstance(value, bool) else None,
                "value_text": value if isinstance(value, str) else None,
                "value_boolean": value if isinstance(value, bool) else None,
                "value_state": "unknown" if value is None else "recorded",
                "unit": definition.unit, "observed_at": stamp(assertion.get("observed_at")),
                "valid_from": None, "valid_to": None,
                "evidence_kind": assertion.get("evidence_kind", "manufacturer_stated"),
                "confidence": assertion.get("confidence"),
                "confidence_reason": "Recorded confidence only; reference-only evidence is not independent verification.",
                "conditions": assertion.get("conditions"), "review_state": scalar(item.review.state),
                "source_ids": [source_key(refs[sid]) for sid in ids],
                "evidence_ids": [evidence_key(refs[sid]) for sid in ids]})
    elif item.object_type in {"content_brief", "video_script", "storyboard"}:
        payload = item.payload
        rows["content_scripts"].append(base | {
            "row_id": f"{item.object_id}:{item.version}", "script_id": item.object_id,
            "object_version": item.version, "workflow_family": payload.get("workflow_family"),
            "input_versions": payload.get("input_versions", {}),
            "claims": payload.get("claims", []),
            "scene_plan": payload.get("scenes", payload.get("presentation", {})),
            "status": scalar(item.status)})
    elif item.object_type == "content_card":
        payload = item.payload
        rows["content_cards"].append(base | {"row_id": f"{item.object_id}:{item.version}",
            "card_id": item.object_id, "object_version": item.version, "product_id": payload["product_id"],
            "product_version": payload["product_version"], "theme": payload["theme"],
            "field_keys": payload["field_keys"], "claims": payload["claims"],
            "practical_impact": payload["practical_impact"], "status": scalar(item.status),
            "publish_state": "private" if not payload.get("publication_allowed") else "eligible"})
    elif item.object_type == "card_bundle":
        payload = item.payload
        rows["content_card_bundles"].append(base | {"row_id": f"{item.object_id}:{item.version}",
            "bundle_id": item.object_id, "object_version": item.version,
            "product_versions": payload["product_versions"], "card_versions": payload["card_versions"],
            "themes": payload["themes"], "generation_policy": payload["generation_policy"],
            "status": scalar(item.status)})
    elif item.object_type == "shorts_plan":
        payload = item.payload
        rows["content_shorts_plans"].append(base | {"row_id": f"{item.object_id}:{item.version}",
            "plan_id": item.object_id, "object_version": item.version,
            "bundle_id": payload["card_bundle_id"], "bundle_version": payload["card_bundle_version"],
            "duration_seconds": payload["duration_seconds"], "aspect_ratio": payload["aspect_ratio"],
            "scenes": payload["scenes"], "status": scalar(item.status),
            "publish_state": "private" if not payload.get("publication_allowed") else "eligible"})
    return rows


def project_store(store, max_objects=500, max_history=200):
    objects = store.list_objects()
    if len(objects) > max_objects:
        raise ValueError("Projection object limit exceeded; use a checkpointed batch.")
    definitions = store.definitions()
    now = datetime.now(UTC).isoformat()
    rows = definition_rows(definitions.values(), now)
    for item in objects:
        if item.object_type not in EXPORT_TYPES:
            continue
        history = store.history(item.object_id)
        if len(history) > max_history:
            raise ValueError("Projection history limit exceeded; use a checkpointed batch.")
        for record in history:
            additions = project_record(record, definitions)
            for table, values in additions.items():
                rows[table].extend(values)
    # Warehouse append retries can be deduplicated by these stable row IDs.
    # Retain the earliest recorded reference date instead of inventing a refresh.
    for table, values in rows.items():
        unique = {}
        for row in sorted(values, key=lambda candidate: candidate["recorded_at"]):
            unique.setdefault(row["row_id"], row)
        rows[table] = list(unique.values())
    return rows
