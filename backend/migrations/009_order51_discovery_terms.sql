-- Migration 009: Discovery Terms Table (Order 51)
-- Table to manage discovery terms (keywords and hashtags) with yield telemetry, allocation, and cooldown.

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

ALTER TABLE discovery_terms ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public read discovery_terms" ON discovery_terms FOR SELECT USING (true);
CREATE POLICY "Allow service role all discovery_terms" ON discovery_terms FOR ALL USING (true);
