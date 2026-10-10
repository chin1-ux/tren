-- 013_tag_registry.sql: Tag registry and per-run tag statistics
CREATE TABLE IF NOT EXISTS tag_registry (
    tag TEXT NOT NULL,
    mode TEXT NOT NULL, -- 'india' or 'global'
    kind TEXT NOT NULL, -- 'core', 'rotating', 'trial', 'event', 'mined', 'probation', 'cross_lag'
    lang TEXT,
    region TEXT,
    status TEXT NOT NULL DEFAULT 'active', -- 'active', 'probation', 'demoted', 'inactive'
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    window_start TIMESTAMPTZ,
    window_end TIMESTAMPTZ,
    runs INTEGER NOT NULL DEFAULT 0,
    last_run_at TIMESTAMPTZ,
    notes TEXT,
    PRIMARY KEY (tag, mode)
);

CREATE TABLE IF NOT EXISTS tag_run_stats (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    mode TEXT NOT NULL,
    saved_reels INTEGER NOT NULL DEFAULT 0,
    distinct_audios INTEGER NOT NULL DEFAULT 0,
    new_audios INTEGER NOT NULL DEFAULT 0,
    orig_share DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    median_age_h DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    creators INTEGER NOT NULL DEFAULT 0,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enable RLS with zero policies (public table inaccessible without service role)
ALTER TABLE tag_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE tag_run_stats ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_tag_run_stats_run_id ON tag_run_stats(run_id);
CREATE INDEX IF NOT EXISTS idx_tag_run_stats_tag_mode ON tag_run_stats(tag, mode);
CREATE INDEX IF NOT EXISTS idx_tag_registry_mode_status ON tag_registry(mode, status);
