-- Migration: Add language classification columns to trends table and create audio_language_overrides table
ALTER TABLE trends ADD COLUMN IF NOT EXISTS language_final text;
ALTER TABLE trends ADD COLUMN IF NOT EXISTS language_confidence real;
ALTER TABLE trends ADD COLUMN IF NOT EXISTS language_source text;
ALTER TABLE trends ADD COLUMN IF NOT EXISTS language_classified_at timestamptz;

CREATE TABLE IF NOT EXISTS audio_language_overrides (
    audio_id text PRIMARY KEY,
    language text NOT NULL,
    note text,
    created_at timestamptz DEFAULT now()
);
