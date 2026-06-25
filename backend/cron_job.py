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

    logging.info("Daily Data Retention Cleanup Job Complete.")


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

    # Schedule every 3 hours
    logging.info("Scheduling pipeline to run every 3 hours...")
    schedule.every(3).hours.do(run_full_pipeline)

    # Schedule daily at 2:00 AM IST
    logging.info("Scheduling daily data retention cleanup at 02:00 AM IST...")
    schedule.every().day.at("02:00").do(run_data_retention_job)

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logging.info("Cron job stopped by user (KeyboardInterrupt).")
