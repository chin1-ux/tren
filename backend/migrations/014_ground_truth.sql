-- Migration 014: Add ground_truth table for measurement only
CREATE TABLE IF NOT EXISTS ground_truth (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title TEXT NOT NULL,
    artist TEXT,
    song_key TEXT NOT NULL,
    note TEXT,
    reported_at TIMESTAMPTZ DEFAULT NOW(),
    source TEXT DEFAULT 'user'
);

ALTER TABLE ground_truth ENABLE ROW LEVEL SECURITY;

-- Additive column tag_variant on probe_log if not exists
ALTER TABLE probe_log ADD COLUMN IF NOT EXISTS tag_variant TEXT;
