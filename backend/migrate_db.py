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
    # reels table – new columns
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS audio_id TEXT;",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS audio_use_count INTEGER DEFAULT 0;",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS window_hours_remaining INTEGER DEFAULT 24;",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS avg_reel_length_seconds INTEGER DEFAULT 0;",
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

    # Indexes for new columns used in filtering/ordering
    "CREATE INDEX IF NOT EXISTS idx_reels_audio_id ON reels (audio_id);",
    "CREATE INDEX IF NOT EXISTS idx_reels_niche_tag ON reels (niche_tag);",
    "CREATE INDEX IF NOT EXISTS idx_reels_is_cross_cultural ON reels (is_cross_cultural);",
    "CREATE INDEX IF NOT EXISTS idx_reels_india_saturation ON reels (india_saturation_pct);",
    "CREATE INDEX IF NOT EXISTS idx_trends_niche_tag ON trends (niche_tag);",
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
