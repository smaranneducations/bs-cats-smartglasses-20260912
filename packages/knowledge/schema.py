"""Canonical additive warehouse definitions. Workflow state stays in Firestore."""

DATASET = "smart_glasses_core"
SCHEMA_VERSION = "knowledge-1"
COMMON = [("row_id", "STRING", "REQUIRED"), ("recorded_at", "TIMESTAMP", "REQUIRED")]
TABLES = {
    "semantic_concepts": [("concept_id", "STRING"), ("definition_hash", "STRING"), ("canonical_name", "STRING"), ("category", "STRING"), ("value_type", "STRING"), ("canonical_unit", "STRING"), ("status", "STRING")],
    "semantic_definitions": [("concept_id", "STRING"), ("definition_hash", "STRING"), ("definition", "STRING"), ("constraints", "JSON"), ("origin", "STRING")],
    "semantic_relationships": [("subject_id", "STRING"), ("predicate_concept_id", "STRING"), ("object_id", "STRING"), ("object_version", "INTEGER"), ("valid_from", "TIMESTAMP"), ("valid_to", "TIMESTAMP"), ("evidence_ids", "STRING", "REPEATED")],
    "semantic_rules": [("rule_id", "STRING"), ("concept_id", "STRING"), ("rule_type", "STRING"), ("parameters", "JSON"), ("severity", "STRING"), ("definition_hash", "STRING")],
    "catalog_products": [("product_id", "STRING"), ("object_version", "INTEGER"), ("brand", "STRING"), ("model", "STRING"), ("category", "STRING"), ("market", "STRING"), ("variant", "STRING"), ("buyer_job", "STRING"), ("status", "STRING"), ("review_state", "STRING")],
    "catalog_assertions": [("assertion_id", "STRING"), ("subject_id", "STRING"), ("object_version", "INTEGER"), ("concept_id", "STRING"), ("definition_hash", "STRING"), ("value_number", "FLOAT"), ("value_text", "STRING"), ("value_boolean", "BOOLEAN"), ("value_state", "STRING"), ("unit", "STRING"), ("observed_at", "TIMESTAMP"), ("valid_from", "TIMESTAMP"), ("valid_to", "TIMESTAMP"), ("evidence_kind", "STRING"), ("confidence", "FLOAT"), ("confidence_reason", "STRING"), ("conditions", "STRING"), ("review_state", "STRING"), ("source_ids", "STRING", "REPEATED"), ("evidence_ids", "STRING", "REPEATED")],
    "evidence_sources": [("source_id", "STRING"), ("local_source_id", "STRING"), ("uri", "STRING"), ("title", "STRING"), ("publisher", "STRING"), ("policy_state", "STRING")],
    "evidence_items": [("evidence_id", "STRING"), ("source_id", "STRING"), ("captured_at", "TIMESTAMP"), ("evidence_kind", "STRING"), ("content_sha256", "STRING"), ("artifact_uri", "STRING"), ("notes", "STRING")],
    "operations_change_events": [("object_id", "STRING"), ("object_type", "STRING"), ("object_version", "INTEGER"), ("event_type", "STRING"), ("actor_id", "STRING"), ("actor_type", "STRING"), ("snapshot_sha256", "STRING")],
    "content_ideas": [("idea_id", "STRING"), ("object_version", "INTEGER"), ("title", "STRING"), ("audience", "STRING"), ("hypothesis", "STRING"), ("status", "STRING"), ("evidence_ids", "STRING", "REPEATED")],
    "content_scripts": [("script_id", "STRING"), ("object_version", "INTEGER"), ("workflow_family", "STRING"), ("input_versions", "JSON"), ("claims", "JSON"), ("scene_plan", "JSON"), ("status", "STRING")],
    "content_videos": [("video_id", "STRING"), ("object_version", "INTEGER"), ("script_id", "STRING"), ("artifact_uri", "STRING"), ("artifact_sha256", "STRING"), ("creative_profile_revision", "STRING"), ("recipe", "JSON"), ("publish_state", "STRING")],
    "content_cards": [("card_id", "STRING"), ("object_version", "INTEGER"), ("product_id", "STRING"), ("product_version", "INTEGER"), ("theme", "STRING"), ("field_keys", "STRING", "REPEATED"), ("claims", "JSON"), ("practical_impact", "STRING"), ("status", "STRING"), ("publish_state", "STRING")],
    "content_card_bundles": [("bundle_id", "STRING"), ("object_version", "INTEGER"), ("product_versions", "JSON"), ("card_versions", "JSON"), ("themes", "STRING", "REPEATED"), ("generation_policy", "STRING"), ("status", "STRING")],
    "content_shorts_plans": [("plan_id", "STRING"), ("object_version", "INTEGER"), ("bundle_id", "STRING"), ("bundle_version", "INTEGER"), ("duration_seconds", "FLOAT"), ("aspect_ratio", "STRING"), ("scenes", "JSON"), ("status", "STRING"), ("publish_state", "STRING")],
    "analytics_feed_metric_snapshots": [("card_id", "STRING"), ("platform", "STRING"), ("captured_at", "TIMESTAMP"), ("metric_values", "JSON"), ("collection_method", "STRING")],
    "analytics_metric_snapshots": [("video_id", "STRING"), ("platform", "STRING"), ("post_id", "STRING"), ("captured_at", "TIMESTAMP"), ("metric_values", "JSON"), ("collection_method", "STRING")],
    "analytics_primitive_usage": [("video_id", "STRING"), ("scene_id", "STRING"), ("primitive_id", "STRING"), ("primitive_version", "STRING"), ("parameters", "JSON")],
}
CLUSTERS = {
    "semantic_concepts": ["concept_id"], "semantic_definitions": ["concept_id"],
    "semantic_relationships": ["subject_id", "predicate_concept_id"], "semantic_rules": ["concept_id"],
    "catalog_products": ["product_id", "category"], "catalog_assertions": ["subject_id", "concept_id"],
    "evidence_sources": ["source_id"], "evidence_items": ["source_id"],
    "operations_change_events": ["object_id", "object_type"], "content_ideas": ["idea_id"],
    "content_scripts": ["script_id"], "content_videos": ["video_id"],
    "content_cards": ["card_id", "product_id"], "content_card_bundles": ["bundle_id"],
    "content_shorts_plans": ["plan_id", "bundle_id"], "analytics_feed_metric_snapshots": ["card_id", "platform"],
    "analytics_metric_snapshots": ["video_id", "platform"], "analytics_primitive_usage": ["video_id", "primitive_id"],
}


def schema(table):
    return [{"name": field[0], "type": field[1], "mode": field[2] if len(field) == 3 else "NULLABLE"}
            for field in COMMON + TABLES[table]]


def ddl():
    result = ["-- Additive knowledge schema. Preserve legacy objects/render_jobs tables.",
              "-- Logical areas share the existing dataset; do not duplicate cloud projects.",
              "-- No rows are loaded and no existing table is replaced by this DDL.",
              f"CREATE SCHEMA IF NOT EXISTS `{DATASET}` OPTIONS(location='US');"]
    types = {"INTEGER": "INT64", "FLOAT": "FLOAT64", "BOOLEAN": "BOOL"}
    for table in TABLES:
        columns = []
        for field in schema(table):
            kind = types.get(field["type"], field["type"])
            if field["mode"] == "REPEATED":
                kind = f"ARRAY<{kind}>"
            required = " NOT NULL" if field["mode"] == "REQUIRED" else ""
            columns.append(f"  {field['name']} {kind}{required}")
        result.append(f"CREATE TABLE IF NOT EXISTS `{DATASET}.{table}` (\n" + ",\n".join(columns) +
                      ")\nPARTITION BY DATE(recorded_at)\nCLUSTER BY " + ", ".join(CLUSTERS[table]) +
                      "\nOPTIONS(require_partition_filter=true);")
    return "\n\n".join(result) + "\n"
