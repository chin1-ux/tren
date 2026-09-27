-- Migration 009c: Add UNIQUE index on spotify_id for spotify_feed_cache upserts
CREATE UNIQUE INDEX IF NOT EXISTS idx_spotify_feed_cache_unique_spotify_id ON spotify_feed_cache (spotify_id);
