-- Migration 010: Order 60 run_id and status telemetry columns
-- Delivered as .sql migration file per standing rules for manual application via Supabase UI.

ALTER TABLE audio_count_history ADD COLUMN IF NOT EXISTS status TEXT;
ALTER TABLE audio_count_history ADD COLUMN IF NOT EXISTS run_id TEXT;
ALTER TABLE proof_log ADD COLUMN IF NOT EXISTS run_id TEXT;
ALTER TABLE watchlist ADD COLUMN IF NOT EXISTS run_id TEXT;

CREATE INDEX IF NOT EXISTS idx_audio_count_history_run_id ON audio_count_history (run_id);
CREATE INDEX IF NOT EXISTS idx_proof_log_run_id ON proof_log (run_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_run_id ON watchlist (run_id);
