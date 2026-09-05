-- Migration: add creator watchlist telemetry columns to cron_runs
-- Apply via Supabase SQL Editor (Dashboard > SQL Editor > New query)
-- These columns record how many creator profiles were checked and how many reels/audios were found per pipeline run.

ALTER TABLE cron_runs
    ADD COLUMN IF NOT EXISTS creator_watchlist_checked INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS creator_watchlist_found INTEGER DEFAULT 0;
