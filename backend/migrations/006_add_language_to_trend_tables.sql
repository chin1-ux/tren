-- Migration 006: Add language columns to audio_trend_scores and format_trends
-- Pattern Rule: Use ALTER TABLE ... ADD COLUMN IF NOT EXISTS

ALTER TABLE audio_trend_scores ADD COLUMN IF NOT EXISTS language TEXT;
ALTER TABLE format_trends ADD COLUMN IF NOT EXISTS language TEXT;

-- Create indexes for fast multi-language filtering
CREATE INDEX IF NOT EXISTS idx_audio_trend_scores_language ON audio_trend_scores(language);
CREATE INDEX IF NOT EXISTS idx_format_trends_language ON format_trends(language);
