-- Migration 006: Seed Keyword Monitors
-- Apply via Supabase SQL Editor
-- Date: Aug 28, 2026
--
-- This expands our keyword monitoring pool across all 8 niches, plus regional tags.
-- The python script `keyword_monitor.py` picks these up to drive the Camoufox scraper.

INSERT INTO keyword_monitors (keyword, niche_category, region, priority, is_active, created_by) VALUES
-- FITNESS
('gym motivation', 'fitness', 'IN', 9, true, 'system'),
('workout transformation', 'fitness', 'IN', 9, true, 'system'),
('fitness journey', 'fitness', 'IN', 8, true, 'system'),
('body transformation', 'fitness', 'IN', 8, true, 'system'),
('gym aesthetic', 'fitness', 'IN', 7, true, 'system'),
-- FOOD
('food recipe viral', 'food', 'IN', 9, true, 'system'),
('street food india', 'food', 'IN', 9, true, 'system'),
('homecooking reels', 'food', 'IN', 8, true, 'system'),
('indian recipes', 'food', 'IN', 8, true, 'system'),
('restaurant review india', 'food', 'IN', 7, true, 'system'),
-- TRAVEL
('hidden places india', 'travel', 'IN', 9, true, 'system'),
('travel vlog india', 'travel', 'IN', 8, true, 'system'),
('road trip india', 'travel', 'IN', 8, true, 'system'),
('solo travel india', 'travel', 'IN', 7, true, 'system'),
-- FASHION
('outfit of the day india', 'fashion', 'IN', 9, true, 'system'),
('ethnic wear outfits', 'fashion', 'IN', 9, true, 'system'),
('street style india', 'fashion', 'IN', 8, true, 'system'),
('fashion haul india', 'fashion', 'IN', 7, true, 'system'),
-- BEAUTY
('makeup tutorial india', 'beauty', 'IN', 9, true, 'system'),
('skincare routine india', 'beauty', 'IN', 8, true, 'system'),
('bridal makeup', 'beauty', 'IN', 8, true, 'system'),
-- COMEDY
('comedy sketch india', 'comedy', 'IN', 9, true, 'system'),
('desi comedy', 'comedy', 'IN', 9, true, 'system'),
('stand up comedy india', 'comedy', 'IN', 8, true, 'system'),
-- DANCE
('dance challenge india', 'dance', 'IN', 9, true, 'system'),
('classical dance reel', 'dance', 'IN', 8, true, 'system'),
('garba dance', 'dance', 'IN', 8, true, 'system'),
-- CURRENT AFFAIRS (New Niche)
('current affairs india', 'current_affairs', 'IN', 10, true, 'system'),
('news explained india', 'current_affairs', 'IN', 10, true, 'system'),
('geopolitics india', 'current_affairs', 'IN', 9, true, 'system'),
('india explained', 'current_affairs', 'IN', 9, true, 'system'),
-- MUSIC / AUDIO DISCOVERY
('trending bollywood songs', 'music', 'IN', 10, true, 'system'),
('new hindi song 2026', 'music', 'IN', 9, true, 'system'),
('viral audio reels', 'music', 'IN', 9, true, 'system'),
('indie music india', 'music', 'IN', 7, true, 'system'),
-- REGIONAL (High ROI)
('onam vibes', 'regional', 'KL', 10, true, 'system'),
('ganesh chaturthi reels', 'regional', 'MH', 9, true, 'system'),
('durga puja vibes', 'regional', 'WB', 9, true, 'system'),
('navratri garba', 'regional', 'GJ', 9, true, 'system'),
('pongal celebration', 'regional', 'TN', 9, true, 'system'),
('bihu dance', 'regional', 'AS', 9, true, 'system'),
-- SPORTS
('cricket highlights', 'sports', 'IN', 10, true, 'system'),
('ipl moments', 'sports', 'IN', 10, true, 'system'),
('india vs pakistan', 'sports', 'IN', 10, true, 'system'),
('kabaddi highlights', 'sports', 'IN', 7, true, 'system'),
-- MOTIVATION
('morning motivation india', 'motivation', 'IN', 8, true, 'system'),
('success mindset', 'motivation', 'IN', 7, true, 'system')
ON CONFLICT DO NOTHING;
