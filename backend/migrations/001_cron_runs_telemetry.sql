-- Migration 001: Telemetry & Error Tracking Columns for cron_runs
-- Rule: Never rely on CREATE TABLE IF NOT EXISTS to add new columns to existing tables.
-- Always use ALTER TABLE <table> ADD COLUMN IF NOT EXISTS <col> <type>.

ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS rate_limited_429 BOOLEAN DEFAULT FALSE;
ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS reels_scraped_count INTEGER DEFAULT 0;
ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS trends_promoted_count INTEGER DEFAULT 0;
