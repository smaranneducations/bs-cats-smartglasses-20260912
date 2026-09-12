-- BigQuery baseline placeholders
CREATE SCHEMA IF NOT EXISTS `smart_glasses_core`;

CREATE TABLE IF NOT EXISTS `smart_glasses_core.objects` (
  object_id STRING NOT NULL,
  object_type STRING NOT NULL,
  title STRING,
  purpose STRING,
  status STRING,
  version INT64,
  valid_from DATE,
  valid_to DATE,
  recorded_at TIMESTAMP,
  created_by STRING,
  source ARRAY<STRING>,
  confidence FLOAT64,
  metadata JSON
) PARTITION BY DATE(recorded_at);

CREATE TABLE IF NOT EXISTS `smart_glasses_core.render_jobs` (
  job_id STRING NOT NULL,
  video_id STRING,
  status STRING,
  manifest JSON,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  output_uri STRING,
  error_message STRING
) PARTITION BY DATE(created_at);
