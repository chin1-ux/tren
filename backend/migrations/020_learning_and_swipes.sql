-- ==============================================================================
-- Migration 020: Learning Engine v1 & Swipe Deck Schema
-- Description: Creates swipe_events (14-day TTL), user_taste, trend_feedback, and user_picks
-- ==============================================================================

-- 1. Swipe Events (Ephemeral, 14-day TTL)
CREATE TABLE IF NOT EXISTS swipe_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    trend_id BIGINT NOT NULL REFERENCES trends(id) ON DELETE CASCADE,
    action VARCHAR(10) NOT NULL CHECK (action IN ('like', 'skip', 'save')),
    reason_chip VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE swipe_events ADD COLUMN IF NOT EXISTS reason_chip VARCHAR(50);
CREATE INDEX IF NOT EXISTS idx_swipe_events_user_action ON swipe_events(user_id, action);
CREATE INDEX IF NOT EXISTS idx_swipe_events_trend_id ON swipe_events(trend_id);
CREATE INDEX IF NOT EXISTS idx_swipe_events_created_at ON swipe_events(created_at);

-- 2. User Taste Profiles
CREATE TABLE IF NOT EXISTS user_taste (
    user_id UUID PRIMARY KEY,
    taste_profile JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE user_taste ADD COLUMN IF NOT EXISTS taste_profile JSONB DEFAULT '{}'::jsonb;
ALTER TABLE user_taste ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

-- 3. Trend Feedback Daily Rollup (For crowd demotion: >= 30 impressions & >= 85% skips)
CREATE TABLE IF NOT EXISTS trend_feedback (
    trend_id BIGINT NOT NULL REFERENCES trends(id) ON DELETE CASCADE,
    report_date DATE NOT NULL DEFAULT CURRENT_DATE,
    impressions INT NOT NULL DEFAULT 0,
    skips INT NOT NULL DEFAULT 0,
    likes INT NOT NULL DEFAULT 0,
    saves INT NOT NULL DEFAULT 0,
    PRIMARY KEY (trend_id, report_date)
);

CREATE INDEX IF NOT EXISTS idx_trend_feedback_date ON trend_feedback(report_date);

-- 4. User Picks (Saved -> Posted -> Reviewed)
CREATE TABLE IF NOT EXISTS user_picks (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    trend_id BIGINT NOT NULL REFERENCES trends(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'saved' CHECK (status IN ('saved', 'posted', 'reviewed')),
    posted_at TIMESTAMPTZ,
    performance_rating INT,
    feedback JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_picks_user_status ON user_picks(user_id, status);

-- Row Level Security
ALTER TABLE swipe_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_taste ENABLE ROW LEVEL SECURITY;
ALTER TABLE trend_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_picks ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'swipe_events' AND policyname = 'Users can insert their own swipes') THEN
        CREATE POLICY "Users can insert their own swipes" ON swipe_events FOR INSERT WITH CHECK (auth.uid() = user_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'swipe_events' AND policyname = 'Users can view their own swipes') THEN
        CREATE POLICY "Users can view their own swipes" ON swipe_events FOR SELECT USING (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'user_taste' AND policyname = 'Users can manage their taste profile') THEN
        CREATE POLICY "Users can manage their taste profile" ON user_taste FOR ALL USING (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'user_picks' AND policyname = 'Users can manage their picks') THEN
        CREATE POLICY "Users can manage their picks" ON user_picks FOR ALL USING (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'trend_feedback' AND policyname = 'Public can read trend feedback') THEN
        CREATE POLICY "Public can read trend feedback" ON trend_feedback FOR SELECT USING (true);
    END IF;
END
$$;
