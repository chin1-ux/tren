-- Migration: Order 49 Observability, Audio Sightings, and External Seeding
-- Delivered as .sql migration file per standing rules for manual application via Supabase UI.

-- 1. Add source_tag to reels
ALTER TABLE reels ADD COLUMN IF NOT EXISTS source_tag text;

-- 2. Lightweight audio_sightings table
CREATE TABLE IF NOT EXISTS audio_sightings (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    audio_id text NOT NULL,
    reel_id text NOT NULL,
    views int,
    likes int,
    taken_at timestamp,
    source_tag text,
    seen_at timestamp DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audio_sightings_audio_id ON audio_sightings (audio_id);
CREATE INDEX IF NOT EXISTS idx_audio_sightings_seen_at ON audio_sightings (seen_at);

-- 3. External Seed Audios table
CREATE TABLE IF NOT EXISTS seed_audios (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    source text NOT NULL,
    region text NOT NULL,
    rank int NOT NULL,
    title text NOT NULL,
    artist text NOT NULL,
    fetched_at timestamp DEFAULT now(),
    created_at timestamp DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_seed_audios_source_region ON seed_audios (source, region);
CREATE INDEX IF NOT EXISTS idx_seed_audios_fetched_at ON seed_audios (fetched_at);
