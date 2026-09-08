-- Migration 003: Shazam Audio Telemetry & Original Audio Resolution
-- Target Tables: trends, reels

-- 1. Add Shazam Canonical Metadata Columns to 'trends' table
ALTER TABLE trends ADD COLUMN IF NOT EXISTS shazam_canonical_title TEXT;
ALTER TABLE trends ADD COLUMN IF NOT EXISTS shazam_canonical_artist TEXT;
ALTER TABLE trends ADD COLUMN IF NOT EXISTS shazam_canonical_album TEXT;
ALTER TABLE trends ADD COLUMN IF NOT EXISTS shazam_canonical_genre TEXT;
ALTER TABLE trends ADD COLUMN IF NOT EXISTS shazam_id TEXT;
ALTER TABLE trends ADD COLUMN IF NOT EXISTS is_original_audio_resolved BOOLEAN DEFAULT FALSE;

-- 2. Add Shazam Canonical Metadata Columns to 'reels' table
ALTER TABLE reels ADD COLUMN IF NOT EXISTS shazam_canonical_title TEXT;
ALTER TABLE reels ADD COLUMN IF NOT EXISTS shazam_canonical_artist TEXT;
ALTER TABLE reels ADD COLUMN IF NOT EXISTS shazam_id TEXT;
ALTER TABLE reels ADD COLUMN IF NOT EXISTS is_original_audio_resolved BOOLEAN DEFAULT FALSE;

-- 3. Add Index for Fast Lookups by Shazam ID
CREATE INDEX IF NOT EXISTS idx_trends_shazam_id ON trends(shazam_id) WHERE shazam_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_reels_shazam_id ON reels(shazam_id) WHERE shazam_id IS NOT NULL;
