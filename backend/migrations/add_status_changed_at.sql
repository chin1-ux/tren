-- Migration: Add status_changed_at timestamp column to trends table
-- Allows UI and API queries to filter and display exact stage duration

ALTER TABLE trends ADD COLUMN IF NOT EXISTS status_changed_at TIMESTAMPTZ DEFAULT NOW();

-- Add index for status_changed_at stage filtering
CREATE INDEX IF NOT EXISTS idx_trends_status_changed_at ON trends(status_changed_at);
