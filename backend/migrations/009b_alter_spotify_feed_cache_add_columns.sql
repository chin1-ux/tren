-- Migration 009b: Add Order 37 search feed columns to spotify_feed_cache
ALTER TABLE spotify_feed_cache ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE spotify_feed_cache ADD COLUMN IF NOT EXISTS artist TEXT;
ALTER TABLE spotify_feed_cache ADD COLUMN IF NOT EXISTS album_name TEXT;
ALTER TABLE spotify_feed_cache ADD COLUMN IF NOT EXISTS release_year INTEGER;
ALTER TABLE spotify_feed_cache ADD COLUMN IF NOT EXISTS preview_url TEXT;
ALTER TABLE spotify_feed_cache ADD COLUMN IF NOT EXISTS image_url TEXT;
ALTER TABLE spotify_feed_cache ADD COLUMN IF NOT EXISTS spotify_url TEXT;
ALTER TABLE spotify_feed_cache ADD COLUMN IF NOT EXISTS is_spotted_on_instagram BOOLEAN DEFAULT FALSE;
ALTER TABLE spotify_feed_cache ADD COLUMN IF NOT EXISTS ig_reel_count INTEGER DEFAULT 0;
ALTER TABLE spotify_feed_cache ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_spotify_feed_cache_spotted ON spotify_feed_cache (is_spotted_on_instagram);
CREATE INDEX IF NOT EXISTS idx_spotify_feed_cache_release_date ON spotify_feed_cache (release_date DESC);
