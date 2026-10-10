-- Migration 015: Add first_noticed column and default source to ground_truth
ALTER TABLE ground_truth ADD COLUMN IF NOT EXISTS first_noticed DATE;
ALTER TABLE ground_truth ALTER COLUMN source SET DEFAULT 'user_list';
