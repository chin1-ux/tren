-- Clean Audio Trends and Reels SQL Migration
-- Execute this script in the Supabase SQL Editor to clear existing audio/trend records if desired.

-- Option A: Clear mock/seed or expired trends
DELETE FROM trends WHERE is_seed_data = true OR status = 'expired';

-- Option B: Reset all trend tables (Run in Supabase UI SQL Editor if you want a complete reset)
-- DELETE FROM reels;
-- DELETE FROM trends;
-- DELETE FROM audio_library;
