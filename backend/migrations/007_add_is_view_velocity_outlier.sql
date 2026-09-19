-- Migration 007: Add is_view_velocity_outlier column to reels table
-- Follows DB Migration Pattern: Uses ALTER TABLE ... ADD COLUMN IF NOT EXISTS

ALTER TABLE reels ADD COLUMN IF NOT EXISTS is_view_velocity_outlier boolean DEFAULT false;
ALTER TABLE reels ADD COLUMN IF NOT EXISTS view_velocity_outlier_tier text;

-- Index for fast queries on view-velocity outliers
CREATE INDEX IF NOT EXISTS idx_reels_view_velocity_outlier ON reels (is_view_velocity_outlier) WHERE is_view_velocity_outlier = true;
