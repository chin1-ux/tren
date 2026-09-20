-- Run via Supabase SQL Editor to confirm content_trends table exists and is ready.

-- 1. Does the table exist at all?
SELECT to_regclass('public.content_trends') AS table_exists;

-- 2. If it exists, what columns does it have?
SELECT column_name, data_type, column_default, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'content_trends'
ORDER BY ordinal_position;

-- 3. Does the unique constraint exist? (required for upsert to work)
SELECT conname, contype, pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid = 'public.content_trends'::regclass
ORDER BY conname;

-- Expected:
--   table_exists = 'content_trends'  (not NULL)
--   Columns: id, trend_type, trend_name, template_pattern, topic_keywords,
--            reel_count, velocity_avg, confidence, status, niche_relevance,
--            adaptation_briefs, window_hours_remaining, first_seen_at,
--            last_updated_at, created_at
--   Unique constraint on (trend_type, template_pattern)
--
-- If table_exists = NULL → run migrate_content_trends.sql first.
