-- Additive knowledge schema. Preserve legacy objects/render_jobs tables.

-- Logical areas share the existing dataset; do not duplicate cloud projects.

-- No rows are loaded and no existing table is replaced by this DDL.

CREATE SCHEMA IF NOT EXISTS `smart_glasses_core` OPTIONS(location='US');

CREATE TABLE IF NOT EXISTS `smart_glasses_core.semantic_concepts` (
  row_id STRING NOT NULL,
  recorded_at TIMESTAMP NOT NULL,
  concept_id STRING,
  definition_hash STRING,
  canonical_name STRING,
  category STRING,
  value_type STRING,
  canonical_unit STRING,
  status STRING)
PARTITION BY DATE(recorded_at)
CLUSTER BY concept_id
OPTIONS(require_partition_filter=true);

CREATE TABLE IF NOT EXISTS `smart_glasses_core.content_cards` (
  row_id STRING NOT NULL, recorded_at TIMESTAMP NOT NULL, card_id STRING,
  object_version INT64, product_id STRING, product_version INT64, theme STRING,
  field_keys ARRAY<STRING>, claims JSON, practical_impact STRING, status STRING, publish_state STRING)
PARTITION BY DATE(recorded_at)
CLUSTER BY card_id, product_id
OPTIONS(require_partition_filter=true);

CREATE TABLE IF NOT EXISTS `smart_glasses_core.content_card_bundles` (
  row_id STRING NOT NULL, recorded_at TIMESTAMP NOT NULL, bundle_id STRING,
  object_version INT64, product_versions JSON, card_versions JSON,
  themes ARRAY<STRING>, generation_policy STRING, status STRING)
PARTITION BY DATE(recorded_at)
CLUSTER BY bundle_id
OPTIONS(require_partition_filter=true);

CREATE TABLE IF NOT EXISTS `smart_glasses_core.content_shorts_plans` (
  row_id STRING NOT NULL, recorded_at TIMESTAMP NOT NULL, plan_id STRING,
  object_version INT64, bundle_id STRING, bundle_version INT64, duration_seconds FLOAT64,
  aspect_ratio STRING, scenes JSON, status STRING, publish_state STRING)
PARTITION BY DATE(recorded_at)
CLUSTER BY plan_id, bundle_id
OPTIONS(require_partition_filter=true);

CREATE TABLE IF NOT EXISTS `smart_glasses_core.analytics_feed_metric_snapshots` (
  row_id STRING NOT NULL, recorded_at TIMESTAMP NOT NULL, card_id STRING,
  platform STRING, captured_at TIMESTAMP, metric_values JSON, collection_method STRING)
PARTITION BY DATE(recorded_at)
CLUSTER BY card_id, platform
OPTIONS(require_partition_filter=true);

CREATE TABLE IF NOT EXISTS `smart_glasses_core.semantic_definitions` (
  row_id STRING NOT NULL,
  recorded_at TIMESTAMP NOT NULL,
  concept_id STRING,
  definition_hash STRING,
  definition STRING,
  constraints JSON,
  origin STRING)
PARTITION BY DATE(recorded_at)
CLUSTER BY concept_id
OPTIONS(require_partition_filter=true);

CREATE TABLE IF NOT EXISTS `smart_glasses_core.semantic_relationships` (
  row_id STRING NOT NULL,
  recorded_at TIMESTAMP NOT NULL,
  subject_id STRING,
  predicate_concept_id STRING,
  object_id STRING,
  object_version INT64,
  valid_from TIMESTAMP,
  valid_to TIMESTAMP,
  evidence_ids ARRAY<STRING>)
PARTITION BY DATE(recorded_at)
CLUSTER BY subject_id, predicate_concept_id
OPTIONS(require_partition_filter=true);

CREATE TABLE IF NOT EXISTS `smart_glasses_core.semantic_rules` (
  row_id STRING NOT NULL,
  recorded_at TIMESTAMP NOT NULL,
  rule_id STRING,
  concept_id STRING,
  rule_type STRING,
  parameters JSON,
  severity STRING,
  definition_hash STRING)
PARTITION BY DATE(recorded_at)
CLUSTER BY concept_id
OPTIONS(require_partition_filter=true);

CREATE TABLE IF NOT EXISTS `smart_glasses_core.catalog_products` (
  row_id STRING NOT NULL,
  recorded_at TIMESTAMP NOT NULL,
  product_id STRING,
  object_version INT64,
  brand STRING,
  model STRING,
  category STRING,
  market STRING,
  variant STRING,
  buyer_job STRING,
  status STRING,
  review_state STRING)
PARTITION BY DATE(recorded_at)
CLUSTER BY product_id, category
OPTIONS(require_partition_filter=true);

CREATE TABLE IF NOT EXISTS `smart_glasses_core.catalog_assertions` (
  row_id STRING NOT NULL,
  recorded_at TIMESTAMP NOT NULL,
  assertion_id STRING,
  subject_id STRING,
  object_version INT64,
  concept_id STRING,
  definition_hash STRING,
  value_number FLOAT64,
  value_text STRING,
  value_boolean BOOL,
  value_state STRING,
  unit STRING,
  observed_at TIMESTAMP,
  valid_from TIMESTAMP,
  valid_to TIMESTAMP,
  evidence_kind STRING,
  confidence FLOAT64,
  confidence_reason STRING,
  conditions STRING,
  review_state STRING,
  source_ids ARRAY<STRING>,
  evidence_ids ARRAY<STRING>)
PARTITION BY DATE(recorded_at)
CLUSTER BY subject_id, concept_id
OPTIONS(require_partition_filter=true);

CREATE TABLE IF NOT EXISTS `smart_glasses_core.evidence_sources` (
  row_id STRING NOT NULL,
  recorded_at TIMESTAMP NOT NULL,
  source_id STRING,
  local_source_id STRING,
  uri STRING,
  title STRING,
  publisher STRING,
  policy_state STRING)
PARTITION BY DATE(recorded_at)
CLUSTER BY source_id
OPTIONS(require_partition_filter=true);

CREATE TABLE IF NOT EXISTS `smart_glasses_core.evidence_items` (
  row_id STRING NOT NULL,
  recorded_at TIMESTAMP NOT NULL,
  evidence_id STRING,
  source_id STRING,
  captured_at TIMESTAMP,
  evidence_kind STRING,
  content_sha256 STRING,
  artifact_uri STRING,
  notes STRING)
PARTITION BY DATE(recorded_at)
CLUSTER BY source_id
OPTIONS(require_partition_filter=true);

CREATE TABLE IF NOT EXISTS `smart_glasses_core.operations_change_events` (
  row_id STRING NOT NULL,
  recorded_at TIMESTAMP NOT NULL,
  object_id STRING,
  object_type STRING,
  object_version INT64,
  event_type STRING,
  actor_id STRING,
  actor_type STRING,
  snapshot_sha256 STRING)
PARTITION BY DATE(recorded_at)
CLUSTER BY object_id, object_type
OPTIONS(require_partition_filter=true);

CREATE TABLE IF NOT EXISTS `smart_glasses_core.content_ideas` (
  row_id STRING NOT NULL,
  recorded_at TIMESTAMP NOT NULL,
  idea_id STRING,
  object_version INT64,
  title STRING,
  audience STRING,
  hypothesis STRING,
  status STRING,
  evidence_ids ARRAY<STRING>)
PARTITION BY DATE(recorded_at)
CLUSTER BY idea_id
OPTIONS(require_partition_filter=true);

CREATE TABLE IF NOT EXISTS `smart_glasses_core.content_scripts` (
  row_id STRING NOT NULL,
  recorded_at TIMESTAMP NOT NULL,
  script_id STRING,
  object_version INT64,
  workflow_family STRING,
  input_versions JSON,
  claims JSON,
  scene_plan JSON,
  status STRING)
PARTITION BY DATE(recorded_at)
CLUSTER BY script_id
OPTIONS(require_partition_filter=true);

CREATE TABLE IF NOT EXISTS `smart_glasses_core.content_videos` (
  row_id STRING NOT NULL,
  recorded_at TIMESTAMP NOT NULL,
  video_id STRING,
  object_version INT64,
  script_id STRING,
  artifact_uri STRING,
  artifact_sha256 STRING,
  creative_profile_revision STRING,
  recipe JSON,
  publish_state STRING)
PARTITION BY DATE(recorded_at)
CLUSTER BY video_id
OPTIONS(require_partition_filter=true);

CREATE TABLE IF NOT EXISTS `smart_glasses_core.analytics_metric_snapshots` (
  row_id STRING NOT NULL,
  recorded_at TIMESTAMP NOT NULL,
  video_id STRING,
  platform STRING,
  post_id STRING,
  captured_at TIMESTAMP,
  metric_values JSON,
  collection_method STRING)
PARTITION BY DATE(recorded_at)
CLUSTER BY video_id, platform
OPTIONS(require_partition_filter=true);

CREATE TABLE IF NOT EXISTS `smart_glasses_core.analytics_primitive_usage` (
  row_id STRING NOT NULL,
  recorded_at TIMESTAMP NOT NULL,
  video_id STRING,
  scene_id STRING,
  primitive_id STRING,
  primitive_version STRING,
  parameters JSON)
PARTITION BY DATE(recorded_at)
CLUSTER BY video_id, primitive_id
OPTIONS(require_partition_filter=true);
