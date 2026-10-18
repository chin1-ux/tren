-- ====================================================================
-- MIGRATION 022_ANALYSIS_SOURCE.SQL: Provenance Tracking for Trends Analysis
-- Review: Adds analysis_source column to record pipeline provenance
-- Allowed values: 'captions' | 'title_only' | 'unknown'
-- ====================================================================

-- 1. Add analysis_source column
ALTER TABLE trends ADD COLUMN IF NOT EXISTS analysis_source TEXT DEFAULT 'unknown';

-- 2. Create index on analysis_source for fast filtering
CREATE INDEX IF NOT EXISTS idx_trends_analysis_source ON trends (analysis_source);

-- ====================================================================
-- ROLLBACK SECTION
-- ====================================================================
/*
DROP INDEX IF EXISTS idx_trends_analysis_source;
ALTER TABLE trends DROP COLUMN IF EXISTS analysis_source;
*/
