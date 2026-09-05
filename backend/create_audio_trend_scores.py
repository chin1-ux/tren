"""
create_audio_trend_scores.py
Run once to create the audio_trend_scores table.
"""
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
logger = logging.getLogger("create_audio_trend_scores")

SQL = """
CREATE TABLE IF NOT EXISTS audio_trend_scores (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    audio_id text NOT NULL,
    scrape_cycle_at timestamp DEFAULT now(),
    reel_count int DEFAULT 0,
    unique_creator_count int DEFAULT 0,
    creator_velocity float DEFAULT 0.0,
    reel_velocity float DEFAULT 0.0,
    lifecycle_stage text NOT NULL,
    top_reels jsonb DEFAULT '[]'::jsonb,
    created_at timestamp DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audio_trend_scores_audio_id ON audio_trend_scores (audio_id);
CREATE INDEX IF NOT EXISTS idx_audio_trend_scores_scrape_cycle ON audio_trend_scores (scrape_cycle_at);

-- Disable RLS on audio_trend_scores to allow scraper to write to it
ALTER TABLE IF EXISTS audio_trend_scores DISABLE ROW LEVEL SECURITY;
"""

def run():
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        logger.info("Connected to database. Creating audio_trend_scores table...")
        cursor.execute(SQL)
        logger.info("Table audio_trend_scores checked/created successfully.")
    except Exception as e:
        logger.error("Error creating table: %s", e)
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    run()
