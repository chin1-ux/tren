-- ==============================================================================
-- Migration 019: Quality Gate (Shadow Mode) Schema
-- Description: Creates trend_quality table for recording tier, signals, and reasons.
-- Never deletes rows. Safe for shadow testing.
-- ==============================================================================

CREATE TABLE IF NOT EXISTS trend_quality (
    trend_id BIGINT PRIMARY KEY REFERENCES trends(id) ON DELETE CASCADE,
    tier VARCHAR(5) NOT NULL CHECK (tier IN ('A', 'B', 'C')),
    reasons TEXT[] NOT NULL DEFAULT '{}',
    signals JSONB NOT NULL DEFAULT '{}'::jsonb,
    scored_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Separate column checks if table already existed (per agent rule: never rely on CREATE TABLE IF NOT EXISTS for columns)
ALTER TABLE trend_quality ADD COLUMN IF NOT EXISTS tier VARCHAR(5);
ALTER TABLE trend_quality ADD COLUMN IF NOT EXISTS reasons TEXT[];
ALTER TABLE trend_quality ADD COLUMN IF NOT EXISTS signals JSONB;
ALTER TABLE trend_quality ADD COLUMN IF NOT EXISTS scored_at TIMESTAMPTZ;

-- Indexes for fast tier filtering
CREATE INDEX IF NOT EXISTS idx_trend_quality_tier ON trend_quality(tier);
CREATE INDEX IF NOT EXISTS idx_trend_quality_scored_at ON trend_quality(scored_at);

-- Row Level Security
ALTER TABLE trend_quality ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'trend_quality' AND policyname = 'Allow public read-only access to trend_quality'
    ) THEN
        CREATE POLICY "Allow public read-only access to trend_quality" ON trend_quality FOR SELECT USING (true);
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'trend_quality' AND policyname = 'Allow service_role full access to trend_quality'
    ) THEN
        CREATE POLICY "Allow service_role full access to trend_quality" ON trend_quality FOR ALL USING (auth.role() = 'service_role');
    END IF;
END
$$;
