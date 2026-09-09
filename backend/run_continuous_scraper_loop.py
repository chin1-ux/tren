import os
import sys
import time
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("backend/.env")
load_dotenv(".env")
sys.path.insert(0, "backend")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("continuous_scraper_loop")

from instagram_scraper_browser import InstagramScraper
from trend_engine import TrendEngine
from trend_refresher import TrendRefresher

def _log_cron_telemetry(sb, run_at, completed_at, duration_sec, reels_scraped, trends_promoted, status_msg="success"):
    if not sb:
        return
    try:
        payload = {
            "run_at": run_at,
            "completed_at": completed_at,
            "duration_seconds": round(duration_sec, 2),
            "scrape_mode": "continuous_daemon",
            "reels_scraped_count": reels_scraped,
            "trends_promoted_count": trends_promoted,
            "status": status_msg,
            "stage": "complete",
            "groq_keys_detected": 1 if os.getenv("GROQ_API_KEY") else 0,
            "gemini_keys_detected": 1 if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") else 0
        }
        sb.table("cron_runs").insert(payload).execute()
        logger.info(f"Logged telemetry to cron_runs: {payload}")
    except Exception as err:
        logger.warning(f"Failed to write cron_runs telemetry: {err}")

async def run_single_scrape_cycle():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    sb = create_client(url, key) if (url and key) else None

    run_at = datetime.now(timezone.utc).isoformat()
    start_time = time.time()
    reels_saved = 0
    detected_count = 0

    logger.info("==================================================")
    logger.info(f"STARTING SCRAPER CYCLE AT {run_at}")
    logger.info("==================================================")

    # 1. Instagram Scraper via Camoufox + Scraper Account
    scraper = InstagramScraper()
    ok = await scraper._init_browser_async()
    if ok:
        try:
            logger.info("--- Scraping Trending Reels across Hashtag Pools ---")
            reels_saved = await scraper.scrape_trending_reels_async()
            logger.info(f"Scraped & saved {reels_saved} fresh reels from Instagram.")

            try:
                w_reels, w_count = await scraper.scrape_creator_watchlist_async()
                logger.info(f"Scraped watchlist creators: {w_count}")
            except Exception as w_err:
                logger.warning(f"Watchlist scraping warning: {w_err}")
        except Exception as s_err:
            logger.error(f"Scraper error during cycle: {s_err}")
        finally:
            await scraper._close_browser_async()
    else:
        logger.error("Failed to initialize Instagram scraper browser session!")

    # 2. TrendEngine Detection
    try:
        logger.info("--- Running TrendEngine Detection ---")
        engine = TrendEngine()
        detected_ids = engine.detect_trends()
        detected_count = len(detected_ids) if detected_ids else 0
        logger.info(f"TrendEngine Detection complete. Fresh detected count: {detected_count}")
    except Exception as te_err:
        logger.error(f"TrendEngine error during cycle: {te_err}")

    # 3. TrendRefresher Sync
    try:
        logger.info("--- Running TrendRefresher Sync ---")
        refresher = TrendRefresher()
        summary = refresher.refresh_all()
        logger.info(f"TrendRefresher Sync complete: {summary}")
    except Exception as tr_err:
        logger.error(f"TrendRefresher error during cycle: {tr_err}")

    end_time = time.time()
    duration = end_time - start_time
    completed_at = datetime.now(timezone.utc).isoformat()

    _log_cron_telemetry(sb, run_at, completed_at, duration, reels_saved, detected_count, "success")
    logger.info(f"CYCLE COMPLETE in {duration:.1f}s. Reels={reels_saved}, Detected={detected_count}")

async def main_loop():
    logger.info("Starting Continuous Scraper Daemon Loop (20 min interval)...")
    while True:
        try:
            await run_single_scrape_cycle()
        except Exception as loop_err:
            logger.error(f"Unhandled error in scrape loop iteration: {loop_err}")
        
        logger.info("Sleeping 20 minutes until next scrape cycle...")
        await asyncio.sleep(1200) # 20 minutes

def main():
    asyncio.run(main_loop())

if __name__ == "__main__":
    main()
