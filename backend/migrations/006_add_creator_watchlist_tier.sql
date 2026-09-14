-- Migration 006: Add watchlist tiering and scheduled polling timestamps to creator_baselines
-- Apply manually via Supabase SQL Editor

ALTER TABLE creator_baselines 
ADD COLUMN IF NOT EXISTS watchlist_tier VARCHAR(50) DEFAULT 'untracked',
ADD COLUMN IF NOT EXISTS watchlist_status VARCHAR(50) DEFAULT 'active',
ADD COLUMN IF NOT EXISTS last_watchlist_scraped_at TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_creator_baselines_watchlist_tier 
ON creator_baselines (watchlist_tier);
