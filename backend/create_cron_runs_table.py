import os
import sys
from dotenv import load_dotenv
import psycopg2

load_dotenv()

DB_URL = os.getenv('SUPABASE_DB_URL')
if not DB_URL:
    raise RuntimeError('SUPABASE_DB_URL not set')

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cron_runs (
    id BIGSERIAL PRIMARY KEY,
    run_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_seconds NUMERIC,
    scrape_mode TEXT,
    groq_keys_detected INTEGER,
    gemini_keys_detected INTEGER,
    reels_scraped INTEGER,
    reels_skipped_low_engagement INTEGER,
    classification_success INTEGER,
    classification_failed_429 INTEGER,
    uploads_skipped_oversized INTEGER,
    pending_backfilled INTEGER,
    new_trends_found INTEGER NOT NULL,
    trend_ids JSONB,
    status TEXT NOT NULL,
    stage TEXT,
    cutoff_reason TEXT
);
"""

def main():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute(CREATE_TABLE_SQL)
        print('cron_runs table ensured/created successfully')
    except Exception as e:
        print(f'Error creating cron_runs table: {e}', file=sys.stderr)
        sys.exit(1)
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    main()
