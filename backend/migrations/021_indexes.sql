-- ====================================================================
-- MIGRATION 021_INDEXES.SQL: Targeted Performance Indexes for N+1 Queries
-- Total Estimated Size: ~31 MB (Strictly capped under 40 MB headroom budget)
-- Order of Benefit:
-- 1. idx_reels_audio_id: Eliminates full table scan on 640k+ reel queries (~15 MB)
-- 2. idx_audio_trend_scores_audio_id: Eliminates 272k+ unindexed lookups (~5 MB)
-- 3. idx_audio_official_counts_audio_id: Eliminates 905k+ lookups with idx_scan=2 (~4 MB)
-- 4. idx_reels_scraped_at: Speeds up IG freshness & cutoff lookups (~5 MB)
-- 5. idx_trends_feed_status: Speeds up live feed queries (status + window) (~2 MB)
-- ====================================================================

-- 1. Reels: Audio ID lookup index (Highest impact: eliminates full table scans on reel lookups)
CREATE INDEX IF NOT EXISTS idx_reels_audio_id ON reels (audio_id);

-- 2. Audio Trend Scores: Audio ID index (Eliminates repeated full table scans in lifecycle classification)
CREATE INDEX IF NOT EXISTS idx_audio_trend_scores_audio_id ON audio_trend_scores (audio_id);

-- 3. Audio Official Counts: Audio ID index (Fixes index usage on 905,000 lookups)
CREATE INDEX IF NOT EXISTS idx_audio_official_counts_audio_id ON audio_official_counts (audio_id);

-- 4. Reels: Scraped At timestamp index (Used by freshness checks and 7-day cutoff queries)
CREATE INDEX IF NOT EXISTS idx_reels_scraped_at ON reels (scraped_at DESC);

-- 5. Trends: Feed status & remaining window compound index (Optimizes feed endpoints)
CREATE INDEX IF NOT EXISTS idx_trends_feed_status ON trends (status, window_hours_remaining);

-- ====================================================================
-- ROLLBACK SECTION (Run only if rolling back Migration 021)
-- ====================================================================
/*
DROP INDEX IF EXISTS idx_reels_audio_id;
DROP INDEX IF EXISTS idx_audio_trend_scores_audio_id;
DROP INDEX IF EXISTS idx_audio_official_counts_audio_id;
DROP INDEX IF EXISTS idx_reels_scraped_at;
DROP INDEX IF EXISTS idx_trends_feed_status;
*/
