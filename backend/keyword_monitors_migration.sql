-- Migration: Create keyword_monitors table for Orbit Search keyword discovery
-- To be applied manually by Chinmay via Supabase SQL Editor

CREATE TABLE IF NOT EXISTS keyword_monitors (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    keyword TEXT NOT NULL UNIQUE,
    source TEXT DEFAULT 'system',           -- 'system' | 'user'
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL, -- link to user if user-submitted
    niche_category TEXT DEFAULT 'general',  -- gym, food, travel, fashion, etc.
    last_checked_at TIMESTAMPTZ,
    velocity_baseline FLOAT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Enable Row Level Security (RLS)
ALTER TABLE keyword_monitors ENABLE ROW LEVEL SECURITY;

-- Create RLS Policies
DROP POLICY IF EXISTS "Allow public read access to keyword_monitors" ON keyword_monitors;
CREATE POLICY "Allow public read access to keyword_monitors" 
ON keyword_monitors FOR SELECT 
TO anon, authenticated 
USING (true);

DROP POLICY IF EXISTS "Allow write access for authenticated users to keyword_monitors" ON keyword_monitors;
CREATE POLICY "Allow write access for authenticated users to keyword_monitors" 
ON keyword_monitors FOR ALL 
TO authenticated 
USING (true)
WITH CHECK (true);

DROP POLICY IF EXISTS "Allow service role full access" ON keyword_monitors;
CREATE POLICY "Allow service role full access" 
ON keyword_monitors FOR ALL 
TO service_role 
USING (true)
WITH CHECK (true);
