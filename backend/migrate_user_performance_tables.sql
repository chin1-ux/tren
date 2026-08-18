-- P-DB-7: Create user_performance, user_insights, user_media_performance tables
-- These tables are referenced by user_performance_tracker.py but were never migrated.
-- Run this in Supabase SQL Editor. Safe to re-run (uses IF NOT EXISTS).

-- 1. User performance profile
CREATE TABLE IF NOT EXISTS user_performance (
  user_email TEXT PRIMARY KEY,
  instagram_id TEXT,
  username TEXT,
  followers_count INT DEFAULT 0,
  following_count INT DEFAULT 0,
  media_count INT DEFAULT 0,
  biography TEXT DEFAULT '',
  profile_picture_url TEXT DEFAULT '',
  last_updated TIMESTAMPTZ DEFAULT now()
);

-- 2. User insights time series (metric_name + recorded_at must be unique together)
CREATE TABLE IF NOT EXISTS user_insights (
  id BIGSERIAL PRIMARY KEY,
  user_email TEXT NOT NULL,
  metric_name TEXT NOT NULL,
  metric_value NUMERIC DEFAULT 0,
  recorded_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_email, metric_name, recorded_at)
);

-- 3. Individual media performance
CREATE TABLE IF NOT EXISTS user_media_performance (
  media_id TEXT PRIMARY KEY,
  user_email TEXT NOT NULL,
  media_type TEXT DEFAULT '',
  caption TEXT DEFAULT '',
  like_count INT DEFAULT 0,
  comments_count INT DEFAULT 0,
  timestamp TEXT DEFAULT '',
  permalink TEXT DEFAULT '',
  recorded_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_user_insights_email ON user_insights(user_email);
CREATE INDEX IF NOT EXISTS idx_user_insights_recorded ON user_insights(recorded_at);
CREATE INDEX IF NOT EXISTS idx_user_media_email ON user_media_performance(user_email);
CREATE INDEX IF NOT EXISTS idx_user_media_recorded ON user_media_performance(recorded_at);
