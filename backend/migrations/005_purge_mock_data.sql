-- Migration 005: Purge Mock / Test Data from Production
-- Apply via Supabase SQL Editor
-- Date: Aug 28, 2026
-- 
-- WHAT THIS PURGES:
-- 1. Fake test usernames inserted Aug 19, 2026 (velocity scores 10M-16M — impossible)
-- 2. Simulated celebrity reels inserted June 2026 via Apify fallback mechanism
-- 3. Any reel with impossible velocity from the exact mock scrape window

-- Step 1: Purge known fake test account reels
DELETE FROM reels WHERE owner_username IN (
  'fitness_guru',
  'bollywood_dance',
  'comedian_king',
  'uk_fashion',
  'delhi_vibes',
  'creator_two',
  'new_creator',
  'mumbai_comedy',
  'anon_creator',
  'trend_rider',
  'lifestyle_pro'
);

-- Step 2: Purge simulated Tauba Tauba / Alibi / Pedro / Espresso reels
-- (Inserted via "Forcing simulated reels fallback to save Apify credits" mechanism)
DELETE FROM reels WHERE reel_id IN (
  'C9X83lDJu2B','C9Y21hKPq4C','C9Z14mLOv8F',
  'C9P34lDJu9Z','C9Q22hKPm1X','C9R15mLOy3W',
  'C9K12lDJa4B','C9L23hKPn6M','C9F32lDJe2A','C9G43hKPo4K'
);

-- Step 3: Purge reels with impossible velocity from mock scrape window (Aug 19 03:00-04:00 UTC)
-- Normal reels have velocity < 500K. The mocks had 6M-16M.
DELETE FROM reels
WHERE velocity_score > 500000
  AND scraped_at BETWEEN '2026-08-19 02:00:00+00' AND '2026-08-19 04:30:00+00';

-- Step 4: Verify the purge (run this SELECT to confirm 0 rows remain)
-- SELECT count(*) FROM reels WHERE owner_username IN (
--   'fitness_guru','bollywood_dance','comedian_king','uk_fashion',
--   'delhi_vibes','creator_two','new_creator','mumbai_comedy',
--   'anon_creator','trend_rider','lifestyle_pro'
-- );
