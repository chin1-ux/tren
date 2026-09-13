-- Migration 005: Add release_date and release_year to content_trends and trends tables
-- Safe, additive migration following project pattern (ALTER TABLE ... ADD COLUMN IF NOT EXISTS)

ALTER TABLE content_trends ADD COLUMN IF NOT EXISTS release_date TEXT;
ALTER TABLE content_trends ADD COLUMN IF NOT EXISTS release_year INTEGER;

ALTER TABLE trends ADD COLUMN IF NOT EXISTS release_date TEXT;
ALTER TABLE trends ADD COLUMN IF NOT EXISTS release_year INTEGER;
