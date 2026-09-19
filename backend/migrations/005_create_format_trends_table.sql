-- Migration: 005_create_format_trends_table.sql
-- Description: Creates format_trends table for storing non-audio caption/format/transition trends.
-- For Chinmay to review and execute manually in Supabase SQL Editor.

CREATE TABLE IF NOT EXISTS format_trends (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cluster_key TEXT UNIQUE NOT NULL,
    format_name TEXT NOT NULL,
    primary_ngrams TEXT[] DEFAULT '{}',
    creator_count INT DEFAULT 0,
    reel_count INT DEFAULT 0,
    velocity_score FLOAT DEFAULT 0.0,
    peak_velocity FLOAT DEFAULT 0.0,
    status TEXT DEFAULT 'emerging', -- 'emerging', 'rising', 'peaked', 'expired'
    first_detected_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    sample_reel_ids TEXT[] DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE
);

-- Index for fast lookup by cluster_key and status
CREATE INDEX IF NOT EXISTS idx_format_trends_cluster_key ON format_trends(cluster_key);
CREATE INDEX IF NOT EXISTS idx_format_trends_status ON format_trends(status);

-- RLS Policy: Public read-only SELECT policy for anon users; backend writes use service_role key
ALTER TABLE format_trends ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow anon read only" ON format_trends;
CREATE POLICY "Allow anon read only" ON format_trends FOR SELECT USING (true);
