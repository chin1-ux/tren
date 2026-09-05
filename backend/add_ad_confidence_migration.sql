-- Migration: Add ad_confidence column to reels table
-- To be applied manually by Chinmay via Supabase SQL Editor

ALTER TABLE reels ADD COLUMN IF NOT EXISTS ad_confidence FLOAT DEFAULT 0.0;
