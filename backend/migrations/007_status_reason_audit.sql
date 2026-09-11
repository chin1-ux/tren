-- ============================================================
-- Migration: Add status_reason audit column to trends table
-- Apply via Supabase UI > SQL Editor
-- Date: 2026-09-12
-- ============================================================

ALTER TABLE trends ADD COLUMN IF NOT EXISTS status_reason jsonb;
