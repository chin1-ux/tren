-- ==============================================================================
-- Migration 021: Search V2 Schema & Full-Text Search Optimization
-- Description: Adds search_text to trends with GIN full-text search index
-- ==============================================================================

-- 1. Add search_text column if not exists
ALTER TABLE trends ADD COLUMN IF NOT EXISTS search_text TEXT;

-- 2. Populate search_text initially from existing columns
UPDATE trends
SET search_text = trim(
    coalesce(audio_title, '') || ' ' ||
    coalesce(audio_artist, '') || ' ' ||
    coalesce(niche_tag, '') || ' ' ||
    coalesce(array_to_string(semantic_niches, ' '), '') || ' ' ||
    coalesce(used_for_note, '') || ' ' ||
    coalesce(why_this_works, '') || ' ' ||
    coalesce(vibe_tag, '') || ' ' ||
    coalesce(trend_classification, '') || ' ' ||
    coalesce(language, '') || ' ' ||
    coalesce(language_final, '')
)
WHERE search_text IS NULL OR search_text = '';

-- 3. Create GIN index on tsvector of search_text for fast full-text matching
CREATE INDEX IF NOT EXISTS idx_trends_search_text_gin
ON trends USING gin(to_tsvector('simple', coalesce(search_text, '')));

-- 4. Create index on audio_artist for artist deduplication (max 2 per artist in top 10)
CREATE INDEX IF NOT EXISTS idx_trends_audio_artist ON trends(audio_artist);
