-- Migration: scraper_sessions table & cron_runs cookie telemetry
-- Purpose: Dynamic self-renewing Instagram cookie storage & sliding telemetry
-- Apply via Supabase SQL Editor

-- 1. Create scraper_sessions table
CREATE TABLE IF NOT EXISTS scraper_sessions (
    id TEXT PRIMARY KEY,                       -- e.g. 'instagram_primary'
    cookies JSONB NOT NULL,                    -- Array of cookie dicts
    session_status TEXT DEFAULT 'active',      -- 'active' | 'warning' | 'expired' | 'checkpoint'
    account_username TEXT,                     -- Instagram account handle
    last_slid_at TIMESTAMPTZ DEFAULT now(),    -- Timestamp of last in-session cookie renewal
    last_verified_at TIMESTAMPTZ DEFAULT now(),-- Timestamp of last successful reel scrape with this session
    expires_at TIMESTAMPTZ,                    -- Absolute earliest expiry of sessionid cookie
    metadata JSONB DEFAULT '{}'::jsonb,        -- Telemetry: last_run_id, reels_scraped, renewal_count
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2. Add telemetry columns to cron_runs (ALTER TABLE pattern per project rules)
ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS cookie_health_status TEXT;
ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS cookie_slid BOOLEAN DEFAULT false;

-- 3. Row Level Security (RLS) - SERVICE ROLE ONLY
-- This guarantees cookies are completely inaccessible to frontend users or anon clients
ALTER TABLE scraper_sessions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access on scraper_sessions" ON scraper_sessions;
CREATE POLICY "Service role full access on scraper_sessions"
ON scraper_sessions
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- 4. Auto-update updated_at timestamp trigger
CREATE OR REPLACE FUNCTION update_scraper_sessions_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS scraper_sessions_updated_at ON scraper_sessions;
CREATE TRIGGER scraper_sessions_updated_at
    BEFORE UPDATE ON scraper_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_scraper_sessions_timestamp();
