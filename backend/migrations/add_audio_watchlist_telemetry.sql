-- Migration: add audio watchlist telemetry columns to cron_runs
-- Apply via Supabase SQL Editor (Dashboard > SQL Editor > New query)
-- These columns record how many audio_ids were re-checked and updated per pipeline run.
-- The cron_runs insert in cron_job.py now writes these values; without the columns the
-- insert would silently fail on that row (Supabase ignores unknown keys).

ALTER TABLE cron_runs
    ADD COLUMN IF NOT EXISTS audio_watchlist_checked INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS audio_watchlist_updated INTEGER DEFAULT 0;
