-- Migration 008: Add is_seed_data flag and mark seed/scraper-originated trends
-- Seed trends = trends with no matching reel in the reels table
-- These trends were injected by the scraper but have no live reel evidence.
-- Two-step approach:
--   Step 1 (this file): Add column + flag seed rows
--   Step 2 (code changes): Add WHERE is_seed_data = false to all production queries

-- ============================================================
-- STEP 1a: Add the is_seed_data column
-- ============================================================
ALTER TABLE trends ADD COLUMN IF NOT EXISTS is_seed_data BOOLEAN DEFAULT false;

-- ============================================================
-- STEP 1b: Add index for query performance
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_trends_is_seed_data ON trends(is_seed_data) WHERE is_seed_data = false;

-- ============================================================
-- STEP 1c: Flag seed trends (no matching reel on audio_id OR title+artist)
-- ============================================================
UPDATE trends SET is_seed_data = true
WHERE id IN (
  SELECT t.id FROM trends t
  WHERE (t.audio_id IS NULL OR NOT EXISTS (
    SELECT 1 FROM reels r WHERE r.audio_id = t.audio_id
  ))
  AND NOT EXISTS (
    SELECT 1 FROM reels r
    WHERE r.audio_title = t.audio_title
    AND r.audio_artist = t.audio_artist
  )
);

-- ============================================================
-- VERIFICATION: Run these after applying to confirm counts
-- ============================================================
-- SELECT is_seed_data, status, COUNT(*) FROM trends GROUP BY is_seed_data, status ORDER BY is_seed_data, status;
-- SELECT COUNT(*) AS seed_flagged FROM trends WHERE is_seed_data = true;
-- SELECT COUNT(*) AS live_remaining FROM trends WHERE is_seed_data = false;
