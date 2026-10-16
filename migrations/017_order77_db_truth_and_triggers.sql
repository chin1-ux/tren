-- Migration 017: Order 77 DB Truth Functions & first_detected_at Protection
-- Purpose:
-- 1. Create RPC functions get_db_size_bytes() and get_table_sizes()
-- 2. Add last_seen_at column and protect first_detected_at trigger on trends
-- 3. Create audio_page_cache table for Item 8
-- Apply via: Supabase Dashboard -> SQL Editor -> Run

-- ============================================================================
-- 1. DB TRUTH RPC FUNCTIONS
-- ============================================================================

-- Function 1: Total database size in bytes
CREATE OR REPLACE FUNCTION get_db_size_bytes()
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN pg_database_size(current_database());
END;
$$;

GRANT EXECUTE ON FUNCTION get_db_size_bytes() TO authenticated, anon, service_role;

-- Function 2: Per-table size breakdown (bytes & row counts)
CREATE OR REPLACE FUNCTION get_table_sizes()
RETURNS TABLE (
    table_name TEXT,
    total_bytes BIGINT,
    table_bytes BIGINT,
    index_bytes BIGINT,
    row_estimate BIGINT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.relname::TEXT AS table_name,
        pg_total_relation_size(c.oid) AS total_bytes,
        pg_relation_size(c.oid) AS table_bytes,
        pg_indexes_size(c.oid) AS index_bytes,
        c.reltuples::BIGINT AS row_estimate
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND c.relkind = 'r'
    ORDER BY pg_total_relation_size(c.oid) DESC;
END;
$$;

GRANT EXECUTE ON FUNCTION get_table_sizes() TO authenticated, anon, service_role;

-- ============================================================================
-- 2. ITEM 3: FIRST_DETECTED_AT PROTECTION & LAST_SEEN_AT
-- ============================================================================

-- Add last_seen_at column to trends if not exists
ALTER TABLE trends ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;

-- Trigger to make first_detected_at immutable once set
CREATE OR REPLACE FUNCTION protect_first_detected_at()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.first_detected_at IS NOT NULL THEN
        NEW.first_detected_at := OLD.first_detected_at;
    END IF;
    IF NEW.last_seen_at IS NULL THEN
        NEW.last_seen_at := NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS no_overwrite_first_detected ON trends;
CREATE TRIGGER no_overwrite_first_detected
    BEFORE UPDATE ON trends
    FOR EACH ROW
    EXECUTE FUNCTION protect_first_detected_at();

-- ============================================================================
-- 3. ITEM 8: AUDIO PAGE CACHE TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS audio_page_cache (
    audio_id TEXT PRIMARY KEY,
    trend_id BIGINT REFERENCES trends(id) ON DELETE CASCADE,
    reel_count INTEGER NOT NULL DEFAULT 0,
    reels JSONB NOT NULL DEFAULT '[]'::jsonb,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audio_page_cache_trend_id ON audio_page_cache(trend_id);
GRANT ALL ON audio_page_cache TO authenticated, anon, service_role;
