"""
backend/retention.py
Standalone database data retention pruning script (Order 57 Phase 1.4).
- audio_trend_scores: pruned to 7 days relative to the newest scrape_cycle_at
- reel_snapshots: pruned to 7 days relative to now()
- news_api_cache: pruned to 1 day relative to now()
- audio_count_history: pruned to 30 days relative to now()
- Strictly touches NOTHING on reels, trends, or trend_snapshots.
- Supports direct Postgres (psycopg2) with seamless REST fallback for runners without direct IPv6 routing.
"""

import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("retention")

def run_retention():
    load_dotenv("backend/.env")
    db_url = os.getenv("SUPABASE_DB_URL")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

    now_utc = datetime.now(timezone.utc)
    d7_ago = (now_utc - timedelta(days=7)).isoformat()
    d1_ago = (now_utc - timedelta(days=1)).isoformat()
    d30_ago = (now_utc - timedelta(days=30)).isoformat()

    # Try psycopg2 first if db_url is provided
    if db_url:
        try:
            import psycopg2
            logger.info("Attempting retention pruning via direct database connection...")
            conn = psycopg2.connect(db_url, connect_timeout=10)
            conn.autocommit = True
            cur = conn.cursor()

            # 1. reel_snapshots (7 days)
            cur.execute("DELETE FROM reel_snapshots WHERE snapshotted_at < NOW() - INTERVAL '7 days';")
            n_rs = cur.rowcount

            # 2. news_api_cache (1 day)
            cur.execute("DELETE FROM news_api_cache WHERE created_at < NOW() - INTERVAL '1 day';")
            n_news = cur.rowcount

            # 3. audio_trend_scores (7 days relative to newest cycle)
            cur.execute("""
                DELETE FROM audio_trend_scores 
                WHERE scrape_cycle_at < (SELECT MAX(scrape_cycle_at) FROM audio_trend_scores) - INTERVAL '7 days';
            """)
            n_ats = cur.rowcount

            # 4. audio_count_history (30 days)
            cur.execute("DELETE FROM audio_count_history WHERE captured_at < NOW() - INTERVAL '30 days';")
            n_ach = cur.rowcount

            # 5. probe_reels (21 days)
            cur.execute("DELETE FROM probe_reels WHERE first_seen_at < NOW() - INTERVAL '21 days';")
            n_pr = cur.rowcount

            # 6. probe_log (14 days)
            cur.execute("DELETE FROM probe_log WHERE ts < NOW() - INTERVAL '14 days';")
            n_pl = cur.rowcount

            # 7. watchlist (status != 'active' older than 30 days; proof_log is NEVER deleted)
            cur.execute("DELETE FROM watchlist WHERE status != 'active' AND flagged_at < NOW() - INTERVAL '30 days';")
            n_wl = cur.rowcount

            cur.close()
            conn.close()

            print(f"RETENTION SUMMARY (psycopg2): reel_snapshots={n_rs}, news_api_cache={n_news}, audio_trend_scores={n_ats}, audio_count_history={n_ach}, probe_reels={n_pr}, probe_log={n_pl}, watchlist={n_wl}")
            return
        except Exception as pg_err:
            logger.warning(f"Direct connection pruning failed or unreachable ({pg_err}). Falling back to Supabase REST client...")

    # Fallback to Supabase REST client
    if not url or not key:
        logger.error("Neither working direct DB connection nor Supabase REST credentials available. Exiting.")
        sys.exit(1)

    from supabase import create_client
    sb = create_client(url, key)

    d21_ago = (now_utc - timedelta(days=21)).isoformat()
    d14_ago = (now_utc - timedelta(days=14)).isoformat()

    # 1. reel_snapshots
    res_rs = sb.table("reel_snapshots").delete().lt("snapshotted_at", d7_ago).execute()
    n_rs = len(res_rs.data or [])

    # 2. news_api_cache
    res_news = sb.table("news_api_cache").delete().lt("created_at", d1_ago).execute()
    n_news = len(res_news.data or [])

    # 3. audio_trend_scores
    max_res = sb.table("audio_trend_scores").select("scrape_cycle_at").order("scrape_cycle_at", desc=True).limit(1).execute()
    n_ats = 0
    if max_res.data:
        newest_cycle_str = max_res.data[0]["scrape_cycle_at"]
        newest_cycle_dt = datetime.fromisoformat(newest_cycle_str.replace("Z", "+00:00"))
        ats_cutoff = (newest_cycle_dt - timedelta(days=7)).isoformat()
        res_ats = sb.table("audio_trend_scores").delete().lt("scrape_cycle_at", ats_cutoff).execute()
        n_ats = len(res_ats.data or [])

    # 4. audio_count_history
    res_ach = sb.table("audio_count_history").delete().lt("captured_at", d30_ago).execute()
    n_ach = len(res_ach.data or [])

    # 5. probe_reels
    res_pr = sb.table("probe_reels").delete().lt("first_seen_at", d21_ago).execute()
    n_pr = len(res_pr.data or [])

    # 6. probe_log
    res_pl = sb.table("probe_log").delete().lt("ts", d14_ago).execute()
    n_pl = len(res_pl.data or [])

    # 7. watchlist (status != 'active' older than 30 days; proof_log is NEVER deleted)
    res_wl = sb.table("watchlist").delete().neq("status", "active").lt("flagged_at", d30_ago).execute()
    n_wl = len(res_wl.data or [])

    print(f"RETENTION SUMMARY (REST): reel_snapshots={n_rs}, news_api_cache={n_news}, audio_trend_scores={n_ats}, audio_count_history={n_ach}, probe_reels={n_pr}, probe_log={n_pl}, watchlist={n_wl}")

if __name__ == "__main__":
    run_retention()
