-- Migration: content_trends table + niche_relevance columns on trends
-- Apply via Supabase SQL Editor

-- ─── 1. content_trends table ─────────────────────────────────────────────────
-- Stores format trends, meme templates, challenge hashtags, topic clusters, news moments.
-- Separate from the audio-keyed `trends` table.

CREATE TABLE IF NOT EXISTS content_trends (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    trend_type TEXT NOT NULL,            -- 'format' | 'challenge' | 'meme' | 'topic' | 'news'
    trend_name TEXT NOT NULL,
    template_pattern TEXT,               -- pattern key for upsert dedup
    topic_keywords TEXT[] DEFAULT '{}',
    reel_count INTEGER DEFAULT 0,
    velocity_avg FLOAT DEFAULT 0,
    confidence FLOAT DEFAULT 0,
    status TEXT DEFAULT 'emerging',      -- 'emerging' | 'rising' | 'peaked' | 'expired'
    niche_relevance JSONB DEFAULT '{}',  -- e.g. {"fitness": 0.8, "food": 0.3}
    adaptation_briefs JSONB DEFAULT '{}',-- e.g. {"fitness": "Show your gym..."}
    window_hours_remaining FLOAT DEFAULT 24.0,
    first_seen_at TIMESTAMPTZ DEFAULT now(),
    last_updated_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE (trend_type, template_pattern)
);

-- Auto-update last_updated_at
CREATE OR REPLACE FUNCTION update_content_trends_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS content_trends_updated_at ON content_trends;
CREATE TRIGGER content_trends_updated_at
    BEFORE UPDATE ON content_trends
    FOR EACH ROW
    EXECUTE FUNCTION update_content_trends_timestamp();

-- ─── 2. audio_adoption_timeline table ────────────────────────────────────────
-- Time-series table for tracking audio use_count per 1-hour bucket.
-- Enables burst ratio calculation (Virlo's core algorithm).

CREATE TABLE IF NOT EXISTS audio_adoption_timeline (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    audio_id TEXT NOT NULL,
    audio_title TEXT,
    audio_artist TEXT,
    hour_bucket TIMESTAMPTZ NOT NULL,    -- truncated to the hour
    use_count INTEGER DEFAULT 0,
    delta_count INTEGER DEFAULT 0,       -- change vs previous bucket
    burst_ratio FLOAT DEFAULT 0,         -- recent 6h count / 90-day average
    created_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE (audio_id, hour_bucket)
);

CREATE INDEX IF NOT EXISTS idx_audio_adoption_audio_id
    ON audio_adoption_timeline (audio_id, hour_bucket DESC);

-- ─── 3. Extend trends table with niche + type columns ─────────────────────────
ALTER TABLE trends ADD COLUMN IF NOT EXISTS niche_relevance JSONB DEFAULT '{}';
ALTER TABLE trends ADD COLUMN IF NOT EXISTS trend_type TEXT DEFAULT 'audio';
ALTER TABLE trends ADD COLUMN IF NOT EXISTS adaptation_briefs JSONB DEFAULT '{}';

-- ─── 4. Extend users table with creator niche preferences ─────────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS creator_niches TEXT[] DEFAULT '{}';
ALTER TABLE users ADD COLUMN IF NOT EXISTS notification_niches TEXT[] DEFAULT '{}';

-- ─── 5. Row Level Security ────────────────────────────────────────────────────
ALTER TABLE content_trends ENABLE ROW LEVEL SECURITY;

-- Anyone (including anon) can read content trends (they're public signals)
DROP POLICY IF EXISTS "content_trends_read" ON content_trends;
CREATE POLICY "content_trends_read" ON content_trends
    FOR SELECT USING (true);

-- Only service role writes
DROP POLICY IF EXISTS "content_trends_write" ON content_trends;
CREATE POLICY "content_trends_write" ON content_trends
    FOR ALL USING (auth.role() = 'service_role');

ALTER TABLE audio_adoption_timeline ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "audio_timeline_read" ON audio_adoption_timeline;
CREATE POLICY "audio_timeline_read" ON audio_adoption_timeline
    FOR SELECT USING (true);
DROP POLICY IF EXISTS "audio_timeline_write" ON audio_adoption_timeline;
CREATE POLICY "audio_timeline_write" ON audio_adoption_timeline
    FOR ALL USING (auth.role() = 'service_role');
