-- Migration 001: Add explicit audio_id and artist columns to content_trends
-- Scoped to Step 2 Audio Deduplication & Cross-Pipeline Resolution

-- 1. Add audio_id column to content_trends for Instagram audio tracking
ALTER TABLE content_trends ADD COLUMN IF NOT EXISTS audio_id TEXT;

-- 2. Add explicit artist column to content_trends for zero-heuristic matching
ALTER TABLE content_trends ADD COLUMN IF NOT EXISTS artist TEXT;

-- 3. Create indexes for fast lookup during ingestion
CREATE INDEX IF NOT EXISTS idx_content_trends_audio_id ON content_trends(audio_id);
CREATE INDEX IF NOT EXISTS idx_content_trends_artist ON content_trends(artist);
