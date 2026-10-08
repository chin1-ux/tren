"""
backend/retention.py
Standalone database data retention pruning script (Order 57 Phase 1.4).
- audio_trend_scores: pruned to 7 days relative to the newest scrape_cycle_at
- reel_snapshots: pruned to 7 days relative to now()
- news_api_cache: pruned to 1 day relative to now()
- audio_count_history: pruned to 30 days relative to now()
- Strictly touches NOTHING on reels, trends, or trend_snapshots.
"""

import os
import sys
import logging
import psycopg2

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("retention")

def run_retention():
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        logger.error("SUPABASE_DB_URL not set. Skipping retention.")
        sys.exit(1)

    logger.info("Connecting to database for scheduled data retention...")
    conn = psycopg2.connect(db_url, connect_timeout=15)
    conn.autocommit = True
    cur = conn.cursor()

    try:
        # 1. reel_snapshots (7 days)
        cur.execute("DELETE FROM reel_snapshots WHERE snapshotted_at < NOW() - INTERVAL '7 days';")
        n_rs = cur.rowcount
        logger.info(f"reel_snapshots pruned: {n_rs} rows deleted (>7d old)")

        # 2. news_api_cache (1 day)
        cur.execute("DELETE FROM news_api_cache WHERE created_at < NOW() - INTERVAL '1 day';")
        n_news = cur.rowcount
        logger.info(f"news_api_cache pruned: {n_news} rows deleted (>1d old)")

        # 3. audio_trend_scores (7 days relative to newest cycle)
        cur.execute("""
            DELETE FROM audio_trend_scores 
            WHERE scrape_cycle_at < (SELECT MAX(scrape_cycle_at) FROM audio_trend_scores) - INTERVAL '7 days';
        """)
        n_ats = cur.rowcount
        logger.info(f"audio_trend_scores pruned: {n_ats} rows deleted (>7d relative to newest cycle)")

        # 4. audio_count_history (30 days)
        cur.execute("DELETE FROM audio_count_history WHERE captured_at < NOW() - INTERVAL '30 days';")
        n_ach = cur.rowcount
        logger.info(f"audio_count_history pruned: {n_ach} rows deleted (>30d old)")

        print(f"RETENTION SUMMARY: reel_snapshots={n_rs}, news_api_cache={n_news}, audio_trend_scores={n_ats}, audio_count_history={n_ach}")

    except Exception as e:
        logger.error(f"Error during retention pruning: {e}", exc_info=True)
        sys.exit(1)
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    run_retention()
