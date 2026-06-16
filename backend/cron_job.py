import os
import sys
import logging
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Dual logging: file + stdout
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

try:
    import schedule
    import time
    from instagram_scraper import InstagramScraper
    from youtube_scraper import YouTubeScraper
    from trend_engine import TrendEngine
    from trend_refresher import TrendRefresher
    from alert_system import AlertSystem
    from supabase import create_client
    from dotenv import load_dotenv
except Exception as import_err:
    logging.critical(f"Failed to import modules: {import_err}", exc_info=True)
    raise


def _get_supabase():
    load_dotenv()
    if not os.getenv("SUPABASE_URL"):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        load_dotenv(os.path.join(script_dir, ".env"))
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)


def run_full_pipeline():
    start = datetime.now()
    run_label = f"PIPELINE RUN @ {start.strftime('%Y-%m-%d %H:%M IST')}"
    logging.info(f"=== {run_label} STARTING ===")

    # ── 1. Instagram Scraper ───────────────────────────────────────────────────
    try:
        logging.info("Step 1/5: Scraping Instagram trending reels...")
        insta = InstagramScraper()
        insta.scrape_trending_reels()
        logging.info("Step 1/5: Instagram scraping complete.")
    except Exception as e:
        logging.error(f"Step 1/5 FAILED (Instagram): {e}", exc_info=True)

    # ── 2. YouTube Scraper ────────────────────────────────────────────────────
    try:
        logging.info("Step 2/5: Scraping YouTube trending Shorts...")
        yt = YouTubeScraper()
        yt.scrape_trending_shorts()
        logging.info("Step 2/5: YouTube scraping complete.")
    except Exception as e:
        logging.error(f"Step 2/5 FAILED (YouTube): {e}", exc_info=True)

    # ── 3. Trend Engine: detect new trends ───────────────────────────────────
    trend_ids = []
    try:
        logging.info("Step 3/5: Running TrendEngine to detect new trends...")
        engine = TrendEngine()
        trend_ids = engine.detect_trends()
        logging.info(f"Step 3/5: Trend detection complete. New trend IDs: {trend_ids}")
    except Exception as e:
        logging.error(f"Step 3/5 FAILED (TrendEngine): {e}", exc_info=True)

    # ── 4. Trend Refresher: update lifecycle of existing trends ──────────────
    try:
        logging.info("Step 4/5: Running TrendRefresher to update trend statuses...")
        refresher = TrendRefresher()
        refresh_summary = refresher.refresh_all()
        logging.info(f"Step 4/5: Refresh complete: {refresh_summary}")
    except Exception as e:
        logging.error(f"Step 4/5 FAILED (TrendRefresher): {e}", exc_info=True)

    # ── 5. Alert System: notify users of new rising trends ───────────────────
    if trend_ids:
        try:
            logging.info(f"Step 5/5: Sending alerts for {len(trend_ids)} new trend(s)...")
            alert = AlertSystem()
            alert.send_trend_alerts(trend_ids)
            logging.info("Step 5/5: Alerts sent.")
        except Exception as e:
            logging.error(f"Step 5/5 FAILED (AlertSystem): {e}", exc_info=True)
    else:
        logging.info("Step 5/5: No new trends — skipping alerts.")

    # ── Log run record to Supabase ────────────────────────────────────────────
    try:
        sb = _get_supabase()
        sb.table("cron_runs").insert({
            "run_at": start.isoformat(),
            "new_trends_found": len(trend_ids),
            "trend_ids": trend_ids,
            "status": "success"
        }).execute()
    except Exception as e:
        logging.warning(f"Could not log cron run to Supabase: {e}")

    elapsed = (datetime.now() - start).seconds
    logging.info(f"=== {run_label} COMPLETE — {len(trend_ids)} new trends in {elapsed}s ===")


if __name__ == "__main__":
    logging.info("Trendrop cron job initialized. Running pipeline immediately on startup...")
    try:
        run_full_pipeline()
    except Exception as e:
        logging.error(f"Startup pipeline run failed: {e}", exc_info=True)

    # Schedule every 3 hours
    logging.info("Scheduling pipeline to run every 3 hours...")
    schedule.every(3).hours.do(run_full_pipeline)

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logging.info("Cron job stopped by user (KeyboardInterrupt).")
