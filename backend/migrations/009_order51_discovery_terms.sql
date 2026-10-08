-- Migration 009: Discovery Terms Table & RLS Hardening (Order 51 & 52 Fix)
-- Table to manage discovery terms (keywords and hashtags) with yield telemetry, allocation, and cooldown.
-- RLS hardened per Order 52 Part 5: no anon write access; service_role write only.

CREATE TABLE IF NOT EXISTS discovery_terms (
    term TEXT PRIMARY KEY,
    kind TEXT NOT NULL DEFAULT 'keyword',
    lang TEXT,
    region TEXT,
    queries INTEGER NOT NULL DEFAULT 0,
    new_audios INTEGER NOT NULL DEFAULT 0,
    last_used TIMESTAMPTZ,
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Ensure columns exist even if table was created previously without them
ALTER TABLE discovery_terms ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'keyword';
ALTER TABLE discovery_terms ADD COLUMN IF NOT EXISTS lang TEXT;
ALTER TABLE discovery_terms ADD COLUMN IF NOT EXISTS region TEXT;
ALTER TABLE discovery_terms ADD COLUMN IF NOT EXISTS queries INTEGER NOT NULL DEFAULT 0;
ALTER TABLE discovery_terms ADD COLUMN IF NOT EXISTS new_audios INTEGER NOT NULL DEFAULT 0;
ALTER TABLE discovery_terms ADD COLUMN IF NOT EXISTS last_used TIMESTAMPTZ;
ALTER TABLE discovery_terms ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE discovery_terms ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_discovery_terms_active_last_used ON discovery_terms (active, last_used);
CREATE INDEX IF NOT EXISTS idx_discovery_terms_yield ON discovery_terms (new_audios DESC, queries ASC);

-- 1. Discovery terms RLS
ALTER TABLE discovery_terms ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public read discovery_terms" ON discovery_terms;
DROP POLICY IF EXISTS "Allow service role all discovery_terms" ON discovery_terms;
DROP POLICY IF EXISTS "Allow service role write discovery_terms" ON discovery_terms;

CREATE POLICY "Allow public read discovery_terms" ON discovery_terms
    FOR SELECT USING (true);

CREATE POLICY "Allow service role write discovery_terms" ON discovery_terms
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- 2. Seed audios RLS
ALTER TABLE seed_audios ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public read seed_audios" ON seed_audios;
DROP POLICY IF EXISTS "Allow service role all seed_audios" ON seed_audios;
DROP POLICY IF EXISTS "Allow service role write seed_audios" ON seed_audios;

CREATE POLICY "Allow public read seed_audios" ON seed_audios
    FOR SELECT USING (true);

CREATE POLICY "Allow service role write seed_audios" ON seed_audios
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- 3. Audio sightings RLS
ALTER TABLE audio_sightings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public read audio_sightings" ON audio_sightings;
DROP POLICY IF EXISTS "Allow service role all audio_sightings" ON audio_sightings;
DROP POLICY IF EXISTS "Allow service role write audio_sightings" ON audio_sightings;

CREATE POLICY "Allow public read audio_sightings" ON audio_sightings
    FOR SELECT USING (true);

CREATE POLICY "Allow service role write audio_sightings" ON audio_sightings
    FOR ALL TO service_role USING (true) WITH CHECK (true);
