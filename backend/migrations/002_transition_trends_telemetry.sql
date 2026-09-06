-- Migration 002: Transition Trends & Commercial Song Fingerprinting Columns for trends
-- Rule: Never rely on CREATE TABLE IF NOT EXISTS to add new columns to existing tables.
-- Always use ALTER TABLE <table> ADD COLUMN IF NOT EXISTS <col> <type>.

ALTER TABLE trends ADD COLUMN IF NOT EXISTS commercial_song_alias TEXT;
ALTER TABLE trends ADD COLUMN IF NOT EXISTS is_transition_trend BOOLEAN DEFAULT FALSE;
ALTER TABLE trends ADD COLUMN IF NOT EXISTS transition_type TEXT;
ALTER TABLE trends ADD COLUMN IF NOT EXISTS display_title TEXT;
