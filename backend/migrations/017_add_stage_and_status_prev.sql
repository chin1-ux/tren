-- Migration 017: Add stage, stage_computed_at, and status_prev to trends table
-- Approved in Order 79D Items 1 & 2

ALTER TABLE trends ADD COLUMN IF NOT EXISTS stage TEXT;
ALTER TABLE trends ADD COLUMN IF NOT EXISTS stage_computed_at TIMESTAMPTZ;
ALTER TABLE trends ADD COLUMN IF NOT EXISTS status_prev TEXT;

CREATE INDEX IF NOT EXISTS idx_trends_stage ON trends(stage);
