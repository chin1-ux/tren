-- ============================================================
-- Migration: Expire whr=0 rising trends + reset stale windows
-- Apply via Supabase UI > SQL Editor
-- Date: 2026-08-28
-- ============================================================

-- STEP 1: Move all rising trends with whr=0 to 'peaked'
-- (They had their window close but the refresher didn't finalize them)
UPDATE trends
SET status = 'peaked'
WHERE status = 'rising'
  AND (window_hours_remaining IS NULL OR window_hours_remaining <= 0);

-- STEP 2: For any remaining rising trends where whr is very small (<=3)
-- and the trend is older than 48h, also peak them
UPDATE trends
SET status = 'peaked', window_hours_remaining = 0
WHERE status = 'rising'
  AND window_hours_remaining <= 3
  AND first_detected_at < NOW() - INTERVAL '48 hours';

-- VERIFICATION
SELECT 
    status,
    COUNT(*) as count,
    MIN(window_hours_remaining) as min_whr,
    MAX(window_hours_remaining) as max_whr,
    AVG(window_hours_remaining)::INT as avg_whr
FROM trends
WHERE status IN ('rising', 'peaked', 'emerging')
GROUP BY status
ORDER BY status;
