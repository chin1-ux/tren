-- Migration: Add is_sponsored column to reels table
-- To be applied manually by Chinmay via Supabase SQL Editor

ALTER TABLE reels ADD COLUMN IF NOT EXISTS is_sponsored BOOLEAN DEFAULT false;
