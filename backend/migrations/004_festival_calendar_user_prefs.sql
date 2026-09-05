-- Migration 004: Festival Calendar + User Preferences + News Signals
-- Apply via Supabase SQL Editor
-- Date: Aug 28, 2026

-- ─── 1. Cultural Events Table ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cultural_events (
    id SERIAL PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    local_name TEXT,
    event_type TEXT NOT NULL CHECK (event_type IN ('festival', 'national_holiday', 'sports', 'cultural', 'religious')),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    duration_days INTEGER DEFAULT 1,
    primary_regions TEXT[] DEFAULT '{}',
    primary_languages TEXT[] DEFAULT '{}',
    pan_india BOOLEAN DEFAULT FALSE,
    feed_flood_intensity FLOAT DEFAULT 0.5,
    niche_opportunities JSONB DEFAULT '{}',
    content_windows JSONB DEFAULT '{}',
    hashtags TEXT[] DEFAULT '{}',
    content_ideas JSONB DEFAULT '{}',
    optimal_posting_offsets INTEGER[] DEFAULT '{-2,-1,0}',
    year INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE cultural_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "cultural_events_read" ON cultural_events;
CREATE POLICY "cultural_events_read" ON cultural_events FOR SELECT USING (true);
DROP POLICY IF EXISTS "cultural_events_write" ON cultural_events;
CREATE POLICY "cultural_events_write" ON cultural_events FOR ALL USING (auth.role() = 'service_role');

-- ─── 2. User Preferences Table ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_preferences (
    email TEXT PRIMARY KEY,
    niches TEXT[] DEFAULT '{}',
    languages TEXT[] DEFAULT '{"en"}',
    creator_language TEXT DEFAULT 'en',
    regions TEXT[] DEFAULT '{"IN"}',
    state TEXT,
    global_enabled BOOLEAN DEFAULT FALSE,
    notification_triggers JSONB DEFAULT '{}',
    creator_tier TEXT DEFAULT 'nano' CHECK (creator_tier IN ('nano', 'micro', 'macro', 'mega')),
    platform_focus TEXT[] DEFAULT '{"instagram"}',
    saved_trends TEXT[] DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "user_prefs_own_row" ON user_preferences;
CREATE POLICY "user_prefs_own_row" ON user_preferences
    FOR ALL USING (auth.email() = email);

-- ─── 3. News Signals Table ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS news_signals (
    id SERIAL PRIMARY KEY,
    headline TEXT NOT NULL,
    source TEXT,
    url TEXT UNIQUE,
    published_at TIMESTAMPTZ,
    viral_potential_score INTEGER DEFAULT 0,
    recommended_angle TEXT,
    niche_relevance JSONB DEFAULT '{}',
    creator_opportunity JSONB DEFAULT '{}',
    content_trend_id UUID REFERENCES content_trends(id) ON DELETE SET NULL,
    detected_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE news_signals ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "news_signals_read" ON news_signals;
CREATE POLICY "news_signals_read" ON news_signals FOR SELECT USING (true);
DROP POLICY IF EXISTS "news_signals_write" ON news_signals;
CREATE POLICY "news_signals_write" ON news_signals FOR ALL USING (auth.role() = 'service_role');

-- ─── 4. Keyword Monitors — Add Missing Columns ────────────────────────────────
ALTER TABLE keyword_monitors ADD COLUMN IF NOT EXISTS region TEXT DEFAULT 'IN';
ALTER TABLE keyword_monitors ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 5;
ALTER TABLE keyword_monitors ADD COLUMN IF NOT EXISTS created_by TEXT DEFAULT 'system';

-- ─── 5. Users Table — Add Niche Columns (if not done via migrate_content_trends.sql) ──
ALTER TABLE users ADD COLUMN IF NOT EXISTS creator_niches TEXT[] DEFAULT '{}';
ALTER TABLE users ADD COLUMN IF NOT EXISTS notification_niches TEXT[] DEFAULT '{}';
ALTER TABLE users ADD COLUMN IF NOT EXISTS creator_state TEXT;

-- ─── 6. Seed 2026-27 Festival Calendar ───────────────────────────────────────
INSERT INTO cultural_events (slug, name, local_name, event_type, start_date, end_date, duration_days, primary_regions, primary_languages, pan_india, feed_flood_intensity, niche_opportunities, hashtags, optimal_posting_offsets, year) VALUES

('pongal_2026', 'Pongal', 'பொங்கல்', 'festival',
 '2026-01-14', '2026-01-17', 4,
 '{"tamil_nadu","andhra_pradesh","telangana","puducherry"}', '{"ta","te"}', false, 0.95,
 '{"food":0.9,"dance":0.7,"culture":0.8,"travel":0.5,"fashion":0.6}',
 '{"#Pongal2026","#PongalVibes","#HappyPongal","#SakkaraiPongal"}',
 '{-4,-3,-2,-1,0,1}', 2026),

('republic_day_2026', 'Republic Day', 'गणतंत्र दिवस', 'national_holiday',
 '2026-01-26', '2026-01-26', 1,
 '{}', '{}', true, 0.7,
 '{"current_affairs":0.95,"education":0.85,"motivation":0.7,"fitness":0.4,"fashion":0.5}',
 '{"#RepublicDay2026","#26January","#JaiHind","#भारत"}',
 '{-2,-1,0}', 2026),

('holi_2026', 'Holi', 'होली', 'festival',
 '2026-03-17', '2026-03-18', 2,
 '{}', '{"hi","mr","gu"}', true, 0.92,
 '{"fashion":0.9,"food":0.8,"dance":0.95,"beauty":0.9,"fitness":0.55,"comedy":0.75}',
 '{"#Holi2026","#HoliVibes","#FestivalOfColors","#RangBarse","#HoliFestival"}',
 '{-4,-3,-2,-1,0,1}', 2026),

('eid_al_fitr_2026', 'Eid al-Fitr', 'ईद', 'religious',
 '2026-03-30', '2026-03-30', 1,
 '{}', '{"ur","hi"}', true, 0.8,
 '{"food":0.9,"fashion":0.9,"current_affairs":0.6,"beauty":0.7}',
 '{"#EidMubarak2026","#Eid2026","#EidAlFitr","#EidOutfit"}',
 '{-3,-2,-1,0,1}', 2026),

('baisakhi_2026', 'Baisakhi', 'ਬੈਸਾਖੀ', 'festival',
 '2026-04-14', '2026-04-14', 1,
 '{"punjab","haryana","himachal_pradesh","delhi_ncr"}', '{"pa","hi"}', false, 0.9,
 '{"dance":0.95,"food":0.8,"fitness":0.6,"music":0.85,"fashion":0.7}',
 '{"#Baisakhi2026","#Vaisakhi2026","#BaishakhiVibes","#BhangDaNasha"}',
 '{-2,-1,0,1}', 2026),

('bihu_2026', 'Bihu (Rongali)', 'বহাগ বিহু', 'festival',
 '2026-04-14', '2026-04-14', 1,
 '{"assam","arunachal_pradesh","nagaland","meghalaya"}', '{"as"}', false, 0.95,
 '{"dance":0.95,"food":0.8,"culture":0.9,"fashion":0.7}',
 '{"#Bihu2026","#RongaliBihu","#BihuVibes","#Assam"}',
 '{-2,-1,0,1}', 2026),

('eid_al_adha_2026', 'Eid al-Adha', 'बकरीद', 'religious',
 '2026-06-07', '2026-06-07', 1,
 '{}', '{"ur","hi"}', true, 0.75,
 '{"food":0.9,"fashion":0.75,"current_affairs":0.5}',
 '{"#EidAlAdha2026","#Bakrid2026","#EidMubarak"}',
 '{-2,-1,0,1}', 2026),

('independence_day_2026', 'Independence Day', 'स्वतंत्रता दिवस', 'national_holiday',
 '2026-08-15', '2026-08-15', 1,
 '{}', '{}', true, 0.85,
 '{"current_affairs":0.95,"education":0.9,"motivation":0.8,"fashion":0.55,"fitness":0.45}',
 '{"#IndependenceDay2026","#15August","#JaiHind","#HarGharTiranga","#AmritMahotsav"}',
 '{-3,-2,-1,0,1}', 2026),

('raksha_bandhan_2026', 'Raksha Bandhan', 'रक्षा बंधन', 'festival',
 '2026-08-09', '2026-08-09', 1,
 '{"north_india","west_india","maharashtra","rajasthan","up","mp"}', '{"hi","mr","gu"}', false, 0.85,
 '{"fashion":0.9,"food":0.8,"siblings_content":0.95,"comedy":0.65}',
 '{"#RakshaBandhan2026","#Rakhi2026","#BhaiBehen","#RakhiVibes"}',
 '{-3,-2,-1,0,1}', 2026),

('janmashtami_2026', 'Janmashtami', 'जन्माष्टमी', 'festival',
 '2026-08-16', '2026-08-16', 1,
 '{}', '{"hi","mr","gu"}', true, 0.8,
 '{"dance":0.85,"food":0.8,"spiritual":0.9,"fashion":0.6,"comedy":0.5}',
 '{"#Janmashtami2026","#KrishnaJanmashtami","#HappyJanmashtami","#JaiShriKrishna"}',
 '{-2,-1,0,1}', 2026),

('varamahalakshmi_2026', 'Varamahalakshmi Vrat', 'ವರಮಹಾಲಕ್ಷ್ಮಿ', 'festival',
 '2026-08-28', '2026-08-28', 1,
 '{"karnataka","andhra_pradesh","telangana","tamil_nadu"}', '{"kn","te","ta"}', false, 0.95,
 '{"food":0.9,"fashion":0.9,"decor":0.95,"spiritual":0.9,"beauty":0.8}',
 '{"#Varamahalakshmi2026","#VaramahalakshmiVrat","#Varalakshmi","#VaramahalakshmiDecorations"}',
 '{-3,-2,-1,0}', 2026),

('onam_2026', 'Onam', 'ഓണം', 'festival',
 '2026-08-26', '2026-09-04', 10,
 '{"kerala"}', '{"ml"}', false, 0.98,
 '{"food":0.95,"dance":0.9,"fashion":0.9,"travel":0.75,"decor":0.85,"culture":0.95}',
 '{"#Onam2026","#OnamVibes","#Thiruvonam","#OnamSadya","#OnamPookalam","#HappyOnam"}',
 '{-4,-3,-2,-1,0,1,2,3}', 2026),

('ganesh_chaturthi_2026', 'Ganesh Chaturthi', 'गणेश चतुर्थी', 'festival',
 '2026-09-14', '2026-09-23', 10,
 '{"maharashtra","goa","karnataka","andhra_pradesh","telangana"}', '{"mr","kn","te"}', false, 0.92,
 '{"food":0.85,"dance":0.8,"decor":0.92,"music":0.85,"comedy":0.65,"travel":0.5}',
 '{"#GaneshChaturthi2026","#GanpatiBappaMorya","#Ganeshotsav","#GaneshFestival","#Bappa"}',
 '{-4,-3,-2,-1,0,1,2}', 2026),

('navratri_2026', 'Navratri (Sharad)', 'नवरात्रि', 'festival',
 '2026-09-28', '2026-10-07', 9,
 '{"gujarat","rajasthan","pan_india"}', '{"gu","hi","mr"}', true, 0.88,
 '{"dance":0.95,"fashion":0.92,"food":0.7,"beauty":0.88,"music":0.85}',
 '{"#Navratri2026","#Garba","#GarbaVibes","#NavratriSpecial","#Dandiya"}',
 '{-4,-3,-2,-1,0,1,2,3}', 2026),

('durga_puja_2026', 'Durga Puja', 'দুর্গাপূজা', 'festival',
 '2026-10-17', '2026-10-21', 5,
 '{"west_bengal","assam","odisha","jharkhand","tripura"}', '{"bn","as","or"}', false, 0.98,
 '{"fashion":0.95,"food":0.88,"travel":0.82,"dance":0.85,"culture":0.95}',
 '{"#DurgaPuja2026","#Pujo2026","#DurgaMaa","#SharadPuja","#BengalPuja"}',
 '{-4,-3,-2,-1,0,1,2}', 2026),

('dussehra_2026', 'Dussehra / Vijayadashami', 'दशहरा', 'festival',
 '2026-10-12', '2026-10-12', 1,
 '{}', '{}', true, 0.75,
 '{"current_affairs":0.65,"comedy":0.75,"food":0.55,"fashion":0.65,"motivation":0.7}',
 '{"#Dussehra2026","#Vijayadashami2026","#DussehraVibes"}',
 '{-2,-1,0,1}', 2026),

('karva_chauth_2026', 'Karva Chauth', 'करवा चौथ', 'festival',
 '2026-10-29', '2026-10-29', 1,
 '{"punjab","haryana","delhi_ncr","uttar_pradesh","rajasthan","himachal_pradesh"}', '{"hi","pa"}', false, 0.92,
 '{"fashion":0.97,"beauty":0.95,"food":0.72,"couple_content":0.92}',
 '{"#KarvaChauth2026","#KarwaChauthVibes","#KarwaChauthLook","#FastingForLove"}',
 '{-3,-2,-1,0}', 2026),

('diwali_2026', 'Diwali', 'दिवाली', 'festival',
 '2026-11-14', '2026-11-18', 5,
 '{}', '{}', true, 0.98,
 '{"decor":0.95,"food":0.92,"fashion":0.95,"travel":0.72,"comedy":0.72,"beauty":0.85}',
 '{"#Diwali2026","#FestivalOfLights","#DiwaliVibes","#DiwaliDecor","#Deepavali2026"}',
 '{-5,-4,-3,-2,-1,0,1,2}', 2026),

('chhath_puja_2026', 'Chhath Puja', 'छठ पूजा', 'festival',
 '2026-11-15', '2026-11-18', 4,
 '{"bihar","jharkhand","uttar_pradesh","delhi_ncr","mumbai"}', '{"bh","mai","hi"}', false, 0.92,
 '{"spiritual":0.97,"food":0.82,"culture":0.92,"family":0.88}',
 '{"#ChhathPuja2026","#ChhathMaiya","#ChhathPujaVibes","#SuryaUparghya"}',
 '{-4,-3,-2,-1,0,1}', 2026),

('christmas_2026', 'Christmas', 'क्रिसमस', 'festival',
 '2026-12-25', '2026-12-27', 3,
 '{"goa","kerala","northeast","metro_cities"}', '{"en"}', true, 0.78,
 '{"food":0.85,"travel":0.88,"fashion":0.82,"decor":0.9,"comedy":0.6}',
 '{"#Christmas2026","#Xmas2026","#HolidaySeason","#ChristmasVibes","#ChristmasInIndia"}',
 '{-5,-4,-3,-2,-1,0,1,2}', 2026),

('new_year_eve_2026', 'New Year Eve', 'नया साल', 'cultural',
 '2026-12-31', '2027-01-01', 1,
 '{}', '{}', true, 0.88,
 '{"travel":0.92,"food":0.85,"fashion":0.88,"comedy":0.82,"motivation":0.75}',
 '{"#NewYear2027","#NYE2027","#HappyNewYear2027","#NewYearVibes","#CountdownTo2027"}',
 '{-4,-3,-2,-1,0,1}', 2026)

ON CONFLICT (slug) DO NOTHING;
