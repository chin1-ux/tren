-- ORDER 27 Migration: Add used_for format classification columns to trends table
ALTER TABLE trends ADD COLUMN IF NOT EXISTS used_for text;
ALTER TABLE trends ADD COLUMN IF NOT EXISTS used_for_note text;
ALTER TABLE trends ADD COLUMN IF NOT EXISTS used_for_classified_at timestamptz;
