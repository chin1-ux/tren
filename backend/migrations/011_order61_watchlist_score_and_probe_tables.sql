-- Migration 011: Watchlist Score, Song Key, and Probe Tables (Order 61)
-- Delivered and applied additively per Order 61 authorization.

ALTER TABLE watchlist ADD COLUMN IF NOT EXISTS score double precision;
ALTER TABLE watchlist ADD COLUMN IF NOT EXISTS song_key text;

CREATE TABLE IF NOT EXISTS probe_reels(
    reel_code text PRIMARY KEY,
    audio_id text,
    song_key text,
    creator text,
    taken_at timestamptz,
    views bigint,
    comments int,
    source_tag text,
    first_seen_at timestamptz DEFAULT now(),
    run_id text
);

CREATE TABLE IF NOT EXISTS probe_log(
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ts timestamptz DEFAULT now(),
    tag text,
    trigger text,
    candidate_audio_id text,
    song_key text,
    http_status int,
    medias int,
    matched int,
    creators int,
    run_id text
);

CREATE INDEX IF NOT EXISTS idx_probe_reels_song_key_taken_at ON probe_reels (song_key, taken_at DESC);
CREATE INDEX IF NOT EXISTS idx_probe_log_ts ON probe_log (ts);
CREATE INDEX IF NOT EXISTS idx_probe_reels_run_id ON probe_reels (run_id);
CREATE INDEX IF NOT EXISTS idx_probe_log_run_id ON probe_log (run_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_score ON watchlist (score DESC);
CREATE INDEX IF NOT EXISTS idx_watchlist_song_key ON watchlist (song_key);

-- Enable RLS with zero policies on new tables per Order 61 requirements
ALTER TABLE probe_reels ENABLE ROW LEVEL SECURITY;
ALTER TABLE probe_log ENABLE ROW LEVEL SECURITY;
