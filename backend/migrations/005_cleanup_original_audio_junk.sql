-- ============================================================
-- Migration: Clean original_audio junk and fix NULL timestamps
-- Apply via Supabase UI > SQL Editor
-- Date: 2026-08-28
-- ============================================================

-- STEP 1: Expire all original_audio::* trends with sentinel use_count (501034)
-- These have reel_count=0 and fake velocity — they should not be shown to users
UPDATE trends
SET 
    status = 'expired',
    window_hours_remaining = 0
WHERE 
    audio_title ILIKE 'original_audio::%'
    AND audio_use_count = 501034;

-- STEP 2: Rename remaining original_audio::* titles to "Original Audio" (clean display)
-- Only runs on ones that survived the above (i.e. real use_count, multiple creators)
UPDATE trends
SET audio_title = 'Original Audio'
WHERE audio_title ILIKE 'original_audio::%';

-- STEP 3: Backfill first_detected_at from created_at where NULL
-- Prevents the delay-gate from returning 0 rows for free users
UPDATE trends
SET first_detected_at = created_at
WHERE first_detected_at IS NULL;

-- VERIFICATION: Check what remains
SELECT 
    status,
    COUNT(*) as count,
    COUNT(CASE WHEN audio_title = 'Original Audio' THEN 1 END) as original_audio_count,
    COUNT(CASE WHEN first_detected_at IS NULL THEN 1 END) as null_timestamps
FROM trends
GROUP BY status
ORDER BY count DESC;
