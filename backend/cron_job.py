import os
import sys
import logging
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Dual logging: file + stdout
import tempfile
is_vercel = os.getenv("VERCEL") is not None or os.getenv("VERCEL_TMP_DIR") is not None
if is_vercel:
    log_file = os.path.join(tempfile.gettempdir(), "pipeline.log")
else:
    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline.log")

log_handlers = [logging.StreamHandler(sys.stdout)]
try:
    log_handlers.append(logging.FileHandler(log_file))
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=log_handlers
)

# Imports for pipeline
import schedule
import time
try:
    from youtube_scraper import YouTubeScraper
except ImportError:
    YouTubeScraper = None
from trend_engine import TrendEngine
from trend_refresher import TrendRefresher
from alert_system import AlertSystem
from supabase import create_client
from dotenv import load_dotenv

# Determine which Instagram scraper backend to use
SCRAPER_BACKEND = os.getenv("SCRAPER_BACKEND", "apify")
if SCRAPER_BACKEND == "browser_use":
    try:
        from instagram_scraper_browser import InstagramScraper as InstagramScraper
        logging.info("Using browser-use Instagram scraper backend.")
    except Exception as e:
        logging.error(f"Failed to import InstagramScraperBrowser: {e}. Falling back to Apify scraper.")
        from instagram_scraper import InstagramScraper as InstagramScraper
else:
    from instagram_scraper import InstagramScraper as InstagramScraper


def _get_supabase():
    load_dotenv()
    if not os.getenv("SUPABASE_URL"):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        load_dotenv(os.path.join(script_dir, ".env"))
    url = os.getenv("SUPABASE_URL")
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    return create_client(url, key)


def run_full_pipeline():
    start = datetime.now()
    run_label = f"PIPELINE RUN @ {start.strftime('%Y-%m-%d %H:%M IST')}"
    logging.info(f"=== {run_label} STARTING ===")

    # ── 1. Instagram Scraper ───────────────────────────────────────────────────
    new_reels_count = 0
    try:
        logging.info("Step 1/5: Scraping Instagram trending reels...")
        insta = InstagramScraper()
        new_reels_count = insta.scrape_trending_reels()
        logging.info(f"Step 1/5: Instagram scraping complete. {new_reels_count} new reels saved.")
    except Exception as e:
        logging.error(f"Step 1/5 FAILED (Instagram): {e}", exc_info=True)

    # ── 2. YouTube Scraper (Bypassed) ─────────────────────────────────────────
    logging.info("Step 2/5: YouTube scraping bypassed (temporarily disabled).")

    # ── 3. Trend Engine: detect new trends ───────────────────────────────────
    trend_ids = []
    if new_reels_count >= 5:
        # Data-quality warning: check proportion of null audio titles in recent scrape
        try:
            sb = _get_supabase()
            from datetime import timedelta
            recent_time = (datetime.utcnow() - timedelta(minutes=30)).isoformat()
            recent_reels = sb.table("reels").select("audio_title").gte("scraped_at", recent_time).execute().data or []
            if recent_reels:
                null_titles = sum(1 for r in recent_reels if not r.get("audio_title"))
                pct_null = null_titles / len(recent_reels)
                if pct_null > 0.5:
                    logging.warning(
                        f"DATA QUALITY WARNING: {pct_null*100:.1f}% of reels ({null_titles}/{len(recent_reels)}) "
                        f"scraped in the last 30 minutes have a NULL audio_title. "
                        f"This suggests a potential scraper parsing failure."
                    )
        except Exception as dq_err:
            logging.warning(f"Failed to perform data-quality check: {dq_err}")

        try:
            logging.info("Step 3/5: Running TrendEngine to detect new trends...")
            engine = TrendEngine()
            trend_ids = engine.detect_trends()
            logging.info(f"Step 3/5: Trend detection complete. New trend IDs: {trend_ids}")
        except Exception as e:
            logging.error(f"Step 3/5 FAILED (TrendEngine): {e}", exc_info=True)
    else:
        logging.warning(f"Skipping trend detection — only {new_reels_count} new reels scraped this cycle, likely scraper failure.")

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
            "new_reels_count": new_reels_count,
            "new_trends_found": len(trend_ids),
            "trend_ids": trend_ids,
            "status": "success"
        }).execute()
    except Exception as e:
        logging.warning(f"Could not log cron run to Supabase: {e}")

    elapsed = (datetime.now() - start).seconds
    logging.info(f"=== {run_label} COMPLETE — {len(trend_ids)} new trends in {elapsed}s ===")


from datetime import timedelta
import shutil

def run_data_retention_job():
    logging.info("Starting Daily Data Retention Cleanup Job (2 AM IST)...")
    try:
        sb = _get_supabase()
    except Exception as sb_err:
        logging.error(f"Cannot initialize Supabase client for data retention: {sb_err}")
        return
        
    now_ts = datetime.utcnow()

    # 1. Delete local uploads and outputs older than 24 hours
    for folder in ["uploads", "outputs"]:
        if os.path.exists(folder):
            for item in os.listdir(folder):
                item_path = os.path.join(folder, item)
                try:
                    mtime = datetime.utcfromtimestamp(os.path.getmtime(item_path))
                    age_hours = (now_ts - mtime).total_seconds() / 3600.0
                    if age_hours > 24:
                        if os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                        else:
                            os.remove(item_path)
                        logging.info(f"Deleted local file/folder: {item_path} (mtime: {mtime})")
                except Exception as e:
                    logging.error(f"Error deleting local path {item_path}: {e}")

    # 2. Clean up Supabase Storage files older than 24 hours
    try:
        past_24h = (now_ts - timedelta(days=1)).isoformat()
        old_jobs = sb.table("jobs").select("id, user_email").lt("created_at", past_24h).execute()
        for job in old_jobs.data:
            job_id = job.get("id")
            email = job.get("user_email")
            if email and job_id:
                try:
                    files = sb.storage.from_("uploads").list(path=f"{email}/{job_id}")
                    if files:
                        file_paths = [f"{email}/{job_id}/{f['name']}" for f in files]
                        sb.storage.from_("uploads").remove(file_paths)
                        logging.info(f"Deleted Supabase Storage uploads: {email}/{job_id}")
                except Exception as e:
                    logging.warning(f"Error clearing uploads storage folder for job {job_id}: {e}")

                try:
                    files = sb.storage.from_("outputs").list(path=f"outputs/{job_id}")
                    if files:
                        file_paths = [f"outputs/{job_id}/{f['name']}" for f in files]
                        sb.storage.from_("outputs").remove(file_paths)
                        logging.info(f"Deleted Supabase Storage outputs: outputs/{job_id}")
                except Exception as e:
                    logging.warning(f"Error clearing outputs storage folder for job {job_id}: {e}")
    except Exception as e:
        logging.error(f"Error cleaning up Supabase storage: {e}")

    # 3. Delete jobs older than 30 days
    try:
        past_30d = (now_ts - timedelta(days=30)).isoformat()
        deleted_jobs = sb.table("jobs").delete().lt("created_at", past_30d).execute()
        logging.info(f"Deleted old jobs from DB (older than 30 days). count: {len(deleted_jobs.data) if deleted_jobs.data else 0}")
    except Exception as e:
        logging.error(f"Error deleting old jobs: {e}")

    # 4. Delete inactive users after 2 years of no login (or no job activity)
    try:
        past_2y = (now_ts - timedelta(days=365*2)).isoformat()
        old_users = sb.table("users").select("email").lt("created_at", past_2y).execute()
        for u in old_users.data:
            email = u.get("email")
            if email:
                recent_jobs = sb.table("jobs").select("id").eq("user_email", email).gt("created_at", past_2y).execute()
                if not recent_jobs.data:
                    sb.table("users").delete().eq("email", email).execute()
                    logging.info(f"Deleted inactive user from DB: {email}")
    except Exception as e:
        logging.error(f"Error cleaning up inactive users: {e}")

    # 5. Retain consent records for 7 years (delete older than 7 years)
    try:
        past_7y = (now_ts - timedelta(days=365*7)).isoformat()
        deleted_consent = sb.table("consent_records").delete().lt("created_at", past_7y).execute()
        logging.info(f"Deleted consent records older than 7 years. count: {len(deleted_consent.data) if deleted_consent.data else 0}")
    except Exception as e:
        logging.error(f"Error deleting old consent records: {e}")

    # 6. Cleanup stale reels preview videos (older than 30 days and not in top 50 by velocity)
    try:
        logging.info("Cleaning up stale reels preview videos (older than 30 days and not in top 50)...")
        import psycopg2
        SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
        if SUPABASE_DB_URL:
            conn = psycopg2.connect(SUPABASE_DB_URL)
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Fetch stale reels
            cursor.execute("""
                SELECT id, reel_id, preview_url, audio_id FROM reels
                WHERE video_stored_at < NOW() - INTERVAL '30 days'
                AND id NOT IN (
                    SELECT id FROM reels
                    ORDER BY (velocity_score) DESC
                    LIMIT 50
                )
                AND video_storage_status = 'stored';
            """)
            stale_reels = cursor.fetchall()
            
            for rid, reel_id, preview_url, audio_id in stale_reels:
                # Delete from Supabase Storage
                safe_audio_id = audio_id or "no_audio"
                path = f"reels/{safe_audio_id}/{reel_id}.mp4"
                try:
                    sb.storage.from_("reels-preview").remove([path])
                    logging.info(f"Deleted stale video file from storage: {path}")
                except Exception as st_err:
                    logging.error(f"Error removing {path} from storage: {st_err}")
                
                # Update DB row status
                cursor.execute("""
                    UPDATE reels 
                    SET video_storage_status = 'expired', preview_url = null
                    WHERE id = %s;
                """, (rid,))
            
            cursor.close()
            conn.close()
            logging.info(f"Stale reels video cleanup complete. Processed {len(stale_reels)} video(s).")
    except Exception as e:
        logging.error(f"Error during reels video cleanup: {e}")

    logging.info("Daily Data Retention Cleanup Job Complete.")


def run_audio_count_check():
    logging.info("Starting Audio Official Counts Check Job...")
    try:
        if SCRAPER_BACKEND == "browser_use":
            insta = InstagramScraper()
            insta.scrape_official_audio_counts(limit=30)
            logging.info("Audio Official Counts Check Job complete.")
        else:
            logging.info("Audio check job skipped (only supported with browser_use backend).")
    except Exception as e:
        logging.error(f"Audio Official Counts Check Job FAILED: {e}", exc_info=True)


if __name__ == "__main__":
    logging.info("Trendrop cron job initialized. Running pipeline immediately on startup...")
    try:
        run_full_pipeline()
    except Exception as e:
        logging.error(f"Startup pipeline run failed: {e}", exc_info=True)

    # Run data retention clean up immediately once on startup to verify / process pending
    try:
        run_data_retention_job()
    except Exception as e:
        logging.error(f"Startup data retention cleanup failed: {e}", exc_info=True)

    # Run audio count check immediately on startup
    try:
        run_audio_count_check()
    except Exception as e:
        logging.error(f"Startup audio counts check failed: {e}", exc_info=True)

    # Schedule every 3 hours
    logging.info("Scheduling pipeline to run every 3 hours...")
    schedule.every(3).hours.do(run_full_pipeline)

    # Schedule every 6 hours for audio counts check
    logging.info("Scheduling audio counts check to run every 6 hours...")
    schedule.every(6).hours.do(run_audio_count_check)

    # Schedule daily at 2:00 AM IST
    logging.info("Scheduling daily data retention cleanup at 02:00 AM IST...")
    schedule.every().day.at("02:00").do(run_data_retention_job)

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logging.info("Cron job stopped by user (KeyboardInterrupt).")
