-- Migration: protect first_detected_at from being overwritten on re-scrape
-- Issue: when audio is scraped again, first_detected_at gets reset to current timestamp.
-- Fix: BEFORE UPDATE trigger freezes first_detected_at once it is set.
-- Apply via: Supabase Dashboard -> SQL Editor -> Run

-- Step 1: Function
CREATE OR REPLACE FUNCTION protect_first_detected_at()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.first_detected_at IS NOT NULL THEN
    NEW.first_detected_at := OLD.first_detected_at;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 2: Trigger (idempotent)
DROP TRIGGER IF EXISTS no_overwrite_first_detected ON trends;
CREATE TRIGGER no_overwrite_first_detected
  BEFORE UPDATE ON trends
  FOR EACH ROW
  EXECUTE FUNCTION protect_first_detected_at();

-- Step 3: Backfill - set first_detected_at = created_at for rows where it is NULL
UPDATE trends
SET first_detected_at = created_at
WHERE first_detected_at IS NULL
  AND created_at IS NOT NULL;

-- Verify
SELECT
  COUNT(*) AS total,
  COUNT(first_detected_at) AS with_first_detected,
  COUNT(*) - COUNT(first_detected_at) AS still_null
FROM trends;
