-- Migration 009: Create spotify_feed_cache table for Order 37
CREATE TABLE IF NOT EXISTS spotify_feed_cache (
    id SERIAL PRIMARY KEY,
    spotify_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    artist TEXT NOT NULL,
    album_name TEXT,
    release_date TEXT,
    release_year INTEGER,
    preview_url TEXT,
    image_url TEXT,
    spotify_url TEXT,
    is_spotted_on_instagram BOOLEAN DEFAULT FALSE,
    ig_reel_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_spotify_feed_cache_spotted ON spotify_feed_cache (is_spotted_on_instagram);
CREATE INDEX IF NOT EXISTS idx_spotify_feed_cache_release_date ON spotify_feed_cache (release_date DESC);
