-- Migration: Add ad_signals column to reels table
-- To be applied manually by Chinmay via Supabase SQL Editor

ALTER TABLE reels ADD COLUMN IF NOT EXISTS ad_signals JSONB DEFAULT '[]'::jsonb;
