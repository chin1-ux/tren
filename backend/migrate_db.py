"""
migrate_db.py
Run once to add all new columns required by the Trendrop v2 features.
Safe to run multiple times – uses IF NOT EXISTS.
"""
import os
import sys
import logging

try:
    import psycopg2
except ImportError:
    print("psycopg2 is not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

from dotenv import load_dotenv

load_dotenv()
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, ".env"))

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
if not SUPABASE_DB_URL:
    print("SUPABASE_DB_URL not set. Cannot run migration.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("migrate_db")

# ─── All ALTER statements ────────────────────────────────────────────────────
MIGRATIONS = [
    "ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;",
    "ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS duration_seconds NUMERIC;",
    "ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS scrape_mode TEXT;",
    "ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS groq_keys_detected INTEGER;",
    "ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS gemini_keys_detected INTEGER;",
    "ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS reels_scraped INTEGER;",
    "ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS reels_skipped_low_engagement INTEGER;",
    "ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS classification_success INTEGER;",
    "ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS classification_failed_429 INTEGER;",
    "ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS uploads_skipped_oversized INTEGER;",
    "ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS pending_backfilled INTEGER;",
    "ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS stage TEXT;",
    "ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS cutoff_reason TEXT;",
    "ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS trend_detection_skipped BOOLEAN DEFAULT false;",

    # reels table – new columns
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS audio_id TEXT;",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS audio_use_count INTEGER DEFAULT 0;",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS window_hours_remaining INTEGER DEFAULT 24;",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS avg_reel_length_seconds INTEGER DEFAULT 0;",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS source_hashtag_pool TEXT;",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS india_saturation_pct FLOAT DEFAULT 0;",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS global_saturation_pct FLOAT DEFAULT 0;",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS niche_tag TEXT DEFAULT 'general';",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS hook_brief JSONB DEFAULT '[]';",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS format_patterns JSONB DEFAULT '[]';",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS scraped_at TIMESTAMP DEFAULT now();",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS is_cross_cultural BOOLEAN DEFAULT false;",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS caption_language TEXT;",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS audio_language TEXT;",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS trend_origin TEXT;",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS creator_country TEXT;",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS language_confidence FLOAT DEFAULT 0.0;",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS preview_url TEXT;",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS video_stored_at TIMESTAMPTZ;",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS video_storage_status TEXT DEFAULT 'pending';",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS is_original_audio BOOLEAN DEFAULT false;",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS is_sponsored BOOLEAN DEFAULT false;",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS ad_confidence FLOAT DEFAULT 0.0;",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS ad_signals JSONB DEFAULT '[]';",

    # trends table – new columns mirrored for API enrichment
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS audio_id TEXT;",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS audio_use_count INTEGER DEFAULT 0;",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS india_saturation_pct FLOAT DEFAULT 0;",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS global_saturation_pct FLOAT DEFAULT 0;",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS niche_tag TEXT DEFAULT 'general';",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS hook_brief JSONB DEFAULT '[]';",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS format_patterns JSONB DEFAULT '[]';",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS avg_reel_length_seconds INTEGER DEFAULT 0;",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS is_cross_cultural BOOLEAN DEFAULT false;",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS trend_origin TEXT;",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS has_creator_outlier BOOLEAN DEFAULT false;",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS high_confidence BOOLEAN DEFAULT false;",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS promotion_reason TEXT;",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS raw_llm_response JSONB;",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS llm_classified_at TIMESTAMPTZ;",
    "CREATE TABLE IF NOT EXISTS trend_snapshots (id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY, trend_id bigint REFERENCES trends(id) ON DELETE CASCADE, velocity_avg FLOAT, creator_count INTEGER, captured_at TIMESTAMP DEFAULT now());",
    "CREATE INDEX IF NOT EXISTS idx_trend_snapshots_trend_captured ON trend_snapshots (trend_id, captured_at DESC);",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_trend_snapshots_trend_captured ON trend_snapshots (trend_id, captured_at);",

    # Indexes for new columns used in filtering/ordering
    "CREATE INDEX IF NOT EXISTS idx_reels_audio_id ON reels (audio_id);",
    "CREATE INDEX IF NOT EXISTS idx_reels_niche_tag ON reels (niche_tag);",
    "CREATE INDEX IF NOT EXISTS idx_reels_is_cross_cultural ON reels (is_cross_cultural);",
    "CREATE INDEX IF NOT EXISTS idx_reels_india_saturation ON reels (india_saturation_pct);",
    "CREATE INDEX IF NOT EXISTS idx_trends_niche_tag ON trends (niche_tag);",

    # Tracked audio & official counts tables
    "CREATE TABLE IF NOT EXISTS tracked_audio (audio_id TEXT PRIMARY KEY, audio_title TEXT, audio_artist TEXT, first_seen_at TIMESTAMP DEFAULT now());",
    "CREATE TABLE IF NOT EXISTS audio_official_counts (id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY, audio_id TEXT REFERENCES tracked_audio(audio_id) ON DELETE CASCADE, official_use_count INTEGER, checked_at TIMESTAMP DEFAULT now(), official_count_velocity FLOAT);",
    "ALTER TABLE audio_official_counts ADD COLUMN IF NOT EXISTS precision_bucket VARCHAR(50) DEFAULT 'exact';"
]



def run():
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        logger.info("Connected to database. Running %d migration statements...", len(MIGRATIONS))

        ok = 0
        failed = 0
        for stmt in MIGRATIONS:
            try:
                cursor.execute(stmt)
                logger.info("OK  ▸ %s", stmt[:80])
                ok += 1
            except Exception as e:
                logger.warning("SKIP ▸ %s  [%s]", stmt[:80], e)
                failed += 1

        logger.info("Migration complete. %d succeeded, %d skipped/failed.", ok, failed)
    except Exception as e:
        logger.error("Connection error: %s", e)
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    run()
