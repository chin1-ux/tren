-- ============================================================
-- Migration: Clean up old emerging/rising junk
-- Apply via Supabase UI > SQL Editor
-- Date: 2026-08-28
-- ============================================================

-- Expire all "Original Audio" variations that are currently active
UPDATE trends
SET status = 'expired', window_hours_remaining = 0
WHERE status IN ('emerging', 'rising')
  AND (
    audio_title ILIKE 'original audio%'
    OR audio_title ILIKE '%original%audio%'
    OR audio_title = 'Original Audio'
  );

-- Expire all active trends with fewer than 3 reels
-- (This clears out the 1-reel noise that is clogging the emerging feed)
UPDATE trends
SET status = 'expired', window_hours_remaining = 0
WHERE status IN ('emerging', 'rising')
  AND (reel_count < 3 OR reel_count IS NULL);

-- Verification: what's left?
SELECT 
    status,
    COUNT(*) as count
FROM trends
WHERE status IN ('rising', 'peaked', 'emerging')
GROUP BY status
ORDER BY status;
