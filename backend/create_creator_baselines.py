import os
import sys
import logging
import psycopg2
from dotenv import load_dotenv

load_dotenv()
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, ".env"))

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
if not SUPABASE_DB_URL:
    print("SUPABASE_DB_URL not set. Cannot run migration.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("create_creator_baselines")

SQL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS creator_baselines (
        username text PRIMARY KEY,
        follower_count integer,
        median_views float,
        median_likes float,
        median_comments float,
        last_scraped_at timestamp with time zone,
        created_at timestamp with time zone DEFAULT now()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_creator_baselines_username ON creator_baselines (username);",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS semantic_niches TEXT[];",
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS is_creator_outlier BOOLEAN DEFAULT NULL;",
    "CREATE INDEX IF NOT EXISTS idx_reels_semantic_niches ON reels USING gin(semantic_niches);",
    "CREATE INDEX IF NOT EXISTS idx_reels_is_creator_outlier ON reels (is_creator_outlier);",
    # Disable RLS to allow backend worker/cron to write/read
    "ALTER TABLE creator_baselines DISABLE ROW LEVEL SECURITY;"
]

def run():
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        logger.info("Connected to database. Executing creator_baselines schema migration...")
        for stmt in SQL_STATEMENTS:
            try:
                cursor.execute(stmt)
                logger.info("Executed successfully: %s", stmt.strip()[:80])
            except Exception as e:
                logger.warning("Statement skipped/failed: %s [%s]", stmt.strip()[:80], e)
        logger.info("Migration complete.")
    except Exception as e:
        logger.error("Error running database setup: %s", e)
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    run()
