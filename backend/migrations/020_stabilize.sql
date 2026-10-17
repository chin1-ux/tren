-- ====================================================================
-- MIGRATION 020_STABILIZE.SQL: Classification Status & Telemetry Schema
-- Review: Idempotent, safe for production, separates language from intel
-- ====================================================================

-- 1. Trends Table: Add Dedicated Analysis Columns
ALTER TABLE trends ADD COLUMN IF NOT EXISTS analysis_status TEXT DEFAULT 'pending';
ALTER TABLE trends ADD COLUMN IF NOT EXISTS analysis_attempts INTEGER DEFAULT 0;
ALTER TABLE trends ADD COLUMN IF NOT EXISTS analysis_last_error TEXT;
ALTER TABLE trends ADD COLUMN IF NOT EXISTS analysis_at TIMESTAMPTZ;

-- 2. Cron Runs Table: Missing Telemetry & Run Tracking Columns
ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS conclusion TEXT;
ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS github_run_id BIGINT;
ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS egress_requests INTEGER DEFAULT 0;
ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS egress_bytes BIGINT DEFAULT 0;

-- 3. Egress Log Table: Per-Run Table Byte & Request Accounting
CREATE TABLE IF NOT EXISTS egress_log (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    workflow TEXT,
    github_run_id BIGINT,
    table_name TEXT,
    requests_count INTEGER DEFAULT 0,
    estimated_bytes BIGINT DEFAULT 0
);

-- 4. Initial Idempotent Data Backfill for analysis_status
-- Mark rows with genuine creator analysis as 'completed'
UPDATE trends
SET analysis_status = 'completed',
    analysis_at = COALESCE(first_detected_at, created_at, NOW())
WHERE llm_classification_status = 'completed'
  AND why_this_works IS NOT NULL
  AND why_this_works NOT LIKE 'The track %is currently driving high engagement%'
  AND (used_for_note IS NULL OR used_for_note != 'Automated fallback classification.');

-- Mark fallback/template/pending rows as 'pending' in analysis_status
UPDATE trends
SET analysis_status = 'pending'
WHERE why_this_works IS NULL
   OR why_this_works LIKE 'The track %is currently driving high engagement%'
   OR used_for_note = 'Automated fallback classification.'
   OR llm_classification_status IN ('skipped_local_fallback', 'pending', 'verified', 'not_needed');

-- ====================================================================
-- ROLLBACK SECTION (Run only if rolling back Migration 020)
-- ====================================================================
/*
ALTER TABLE trends DROP COLUMN IF EXISTS analysis_status;
ALTER TABLE trends DROP COLUMN IF EXISTS analysis_attempts;
ALTER TABLE trends DROP COLUMN IF EXISTS analysis_last_error;
ALTER TABLE trends DROP COLUMN IF EXISTS analysis_at;

ALTER TABLE cron_runs DROP COLUMN IF EXISTS conclusion;
ALTER TABLE cron_runs DROP COLUMN IF EXISTS github_run_id;
ALTER TABLE cron_runs DROP COLUMN IF EXISTS egress_requests;
ALTER TABLE cron_runs DROP COLUMN IF EXISTS egress_bytes;

DROP TABLE IF EXISTS egress_log;
*/
