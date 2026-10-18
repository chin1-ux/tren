-- Migration 024: Create user_swipes table for Deck swipe interactions
-- Apply via Supabase SQL Editor
-- Date: Oct 18, 2026

CREATE TABLE IF NOT EXISTS user_swipes (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    trend_id BIGINT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('use', 'skip')),
    reason TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT user_swipes_user_trend_unique UNIQUE(user_id, trend_id)
);

-- Separate column addition per standing rule if table pre-existed
ALTER TABLE user_swipes ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE user_swipes ADD COLUMN IF NOT EXISTS trend_id BIGINT;
ALTER TABLE user_swipes ADD COLUMN IF NOT EXISTS action TEXT;
ALTER TABLE user_swipes ADD COLUMN IF NOT EXISTS reason TEXT;
ALTER TABLE user_swipes ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE user_swipes ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Index on (user_id, updated_at desc)
CREATE INDEX IF NOT EXISTS idx_user_swipes_user_updated ON user_swipes(user_id, updated_at DESC);

-- Enable RLS and restrict to service_role only
ALTER TABLE user_swipes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "user_swipes_service_role" ON user_swipes;
CREATE POLICY "user_swipes_service_role" ON user_swipes FOR ALL USING (auth.role() = 'service_role');

-- ─── ROLLBACK SECTION ────────────────────────────────────────────────────────
-- To rollback migration 024, execute:
-- DROP TABLE IF EXISTS user_swipes CASCADE;
