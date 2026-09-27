-- ORDER 31 Migration: Add preferred_languages array to users & user_preferences tables
ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_languages text[];
ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS preferred_languages text[];
