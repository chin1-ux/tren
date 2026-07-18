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


def _invalidate_trends_cache():
    """
    Invalidate Redis trend cache keys after a pipeline write so the next
    API request fetches fresh data from Supabase instead of serving stale
    cache for up to CACHE_TTL (300s) after new trends are written.
    
    Pipeline runs every 3h. Cache TTL is 5min. Without this, after a run
    completes, the frontend can still see the old list for up to 5 more
    minutes if the cache was warm when the pipeline started writing.
    """
    try:
        import redis as _redis
        upstash_url = os.getenv('UPSTASH_REDIS_URL')
        if not upstash_url:
            logging.info('Cache invalidation skipped: UPSTASH_REDIS_URL not set.')
            return
        rc = _redis.from_url(upstash_url)
        # Pattern: all keys matching trends:* (language/sort variants)
        # Use SCAN to avoid blocking on large keyspaces
        deleted = 0
        cursor = 0
        while True:
            cursor, keys = rc.scan(cursor, match='trends:*', count=50)
            if keys:
                rc.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break
        logging.info(f'Trends cache invalidated: {deleted} key(s) deleted from Redis.')
    except Exception as cache_err:
        logging.error(f'Cache invalidation failed (non-fatal): {cache_err}')


def _get_supabase():
    load_dotenv()
    if not os.getenv("SUPABASE_URL"):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        load_dotenv(os.path.join(script_dir, ".env"))
    url = os.getenv("SUPABASE_URL")
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    return create_client(url, key)


def verify_database_schema(sb):

    """
    Lightweight schema validation to verify that the required columns
    exist in the database tables before running the pipeline.
    Fails loudly and immediately on mismatch.
    """
    logging.info("Validating database schema...")
    try:
        # Check 'trends' table for 'discovery_source', 'semantic_niches', 'llm_classification_status', 'llm_retry_count'
        sb.table("trends").select("discovery_source, semantic_niches, llm_classification_status, llm_retry_count, has_creator_outlier").limit(0).execute()
        
        # Check 'reels' table for 'is_creator_outlier' and 'semantic_niches'
        sb.table("reels").select("is_creator_outlier, semantic_niches").limit(0).execute()
        
        # Check 'creator_baselines' table exists and has post_count
        sb.table("creator_baselines").select("username, post_count").limit(0).execute()
        
        logging.info("Database schema validation successful.")
    except Exception as e:
        error_msg = f"DATABASE SCHEMA VALIDATION FAILED: {e}. Please run migrations."
        logging.critical(error_msg)
        raise RuntimeError(error_msg)


def run_full_pipeline():
    start = datetime.now()
    run_label = f"PIPELINE RUN @ {start.strftime('%Y-%m-%d %H:%M IST')}"
    logging.info(f"=== {run_label} STARTING ===")

    # ── 0. Schema Validation ───────────────────────────────────────────────────
    try:
        sb = _get_supabase()
        verify_database_schema(sb)
    except Exception as e:
        logging.critical(f"Pipeline startup aborted due to schema mismatch: {e}")
        raise e

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
    if new_reels_count > 0:  # Run trend detection even for small batches; TrendEngine has its own guard
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
            
            # Retry pending/failed LLM classifications first
            try:
                retried_count = engine.retry_pending_classifications()
                logging.info(f"LLM Re-classification retry completed. Successfully re-classified {retried_count} trends.")
            except Exception as retry_err:
                logging.error(f"LLM Re-classification retry failed: {retry_err}", exc_info=True)
                
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

    # Append one snapshot per trend for this pipeline run so velocity persistence
    # can be evaluated against real historical data on future runs.
    try:
        sb = _get_supabase()
        snapshot_rows = refresher.get_snapshot_rows(captured_at=start)
        if snapshot_rows:
            sb.table("trend_snapshots").insert(snapshot_rows).execute()
            logging.info(f"Step 4/5: Recorded {len(snapshot_rows)} trend snapshot rows.")
        else:
            logging.info("Step 4/5: No trend snapshot rows to record.")
    except Exception as e:
        logging.error(f"Step 4/5 FAILED (trend snapshots): {e}", exc_info=True)

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
    # Immediately purge the Redis trends cache so the next API request
    # serves the freshly-written data, not a stale 5-minute window.
    _invalidate_trends_cache()


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


def run_creator_sync_job():
    logging.info("Starting Daily Creator Sync Job...")
    try:
        sb = _get_supabase()
    except Exception as e:
        logging.error(f"Cannot initialize Supabase for sync: {e}")
        return
        
    try:
        from instagram_oauth import InstagramOAuth
        # Fetch all instagram tokens
        tokens_res = sb.table("instagram_tokens").select("*").execute()
        for token in (tokens_res.data or []):
            email = token.get("user_email")
            access_token = token.get("access_token")
            ig_account_id = token.get("ig_account_id")
            if email and access_token and ig_account_id:
                logging.info(f"Syncing posts for creator {email}...")
                InstagramOAuth.sync_creator_posts(access_token, ig_account_id, email)
        logging.info("Daily Creator Sync Job completed.")
    except Exception as e:
        logging.error(f"Error during creator sync job: {e}")


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


def check_and_send_milestone_reminders() -> int:
    logging.info("Starting Brand Deal Milestone Payment Reminders Job...")
    try:
        import resend
    except ImportError:
        logging.error("Resend package is not imported.")
        return 0

    try:
        sb = _get_supabase()
    except Exception as e:
        logging.error(f"Cannot initialize Supabase for milestone reminders: {e}")
        return 0

    resend.api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("RESEND_FROM_EMAIL", "alerts@trendrop.ai")
    
    # 1. Fetch all unpaid milestones with parent brand deal details
    try:
        # In supabase-py, we can do joins using select("*, brand_deals(*)")
        res = sb.table("deal_payment_milestones").select("*, brand_deals(*)").eq("paid_status", "unpaid").execute()
        milestones = res.data or []
    except Exception as query_err:
        logging.error(f"Failed to query unpaid milestones: {query_err}")
        return 0
        
    now = datetime.utcnow()
    emails_sent = 0
    
    for m in milestones:
        due_date_str = m.get("due_date")
        if not due_date_str:
            continue
            
        try:
            # Parse ISO due date string
            due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception as parse_err:
            logging.warning(f"Error parsing due date '{due_date_str}': {parse_err}")
            continue
            
        time_diff = due_date - now
        # Check if approaching (within 2 days, i.e., 48 hours) or past due
        is_approaching = timedelta(days=0) <= time_diff <= timedelta(days=2)
        is_overdue = time_diff < timedelta(days=0)
        
        if not (is_approaching or is_overdue):
            continue
            
        # Throttling: Check if a reminder was already sent in the last 24 hours
        sent_at_str = m.get("reminder_sent_at")
        if sent_at_str:
            try:
                sent_at = datetime.fromisoformat(sent_at_str.replace("Z", "+00:00")).replace(tzinfo=None)
                if now - sent_at < timedelta(hours=24):
                    logging.info(f"Skipping reminder for milestone {m['id']} (already sent within 24 hours)")
                    continue
            except Exception as throttle_err:
                logging.warning(f"Error parsing reminder_sent_at: {throttle_err}")
                
        deal = m.get("brand_deals") or {}
        creator_email = deal.get("creator_id")
        brand_name = deal.get("brand_name", "the brand")
        currency = deal.get("currency", "INR").upper()
        amount = float(m.get("amount", 0))
        milestone_name = m.get("milestone_name", "Milestone")
        
        if not creator_email:
            logging.warning(f"No creator_email/creator_id found for deal ID {m.get('deal_id')}")
            continue
            
        status_label = "OVERDUE" if is_overdue else "UPCOMING"
        subject = f"[Trendrop Payment Alert] {status_label}: {currency} {amount:,.2f} milestone with {brand_name}"
        
        # Follow-up drafts for the creator
        hinglish_draft = (
            f"Hi team, humare campaign deliverables ke context mein ek chota reminder. "
            f"Humare agreement ke hisab se milestone payment of {currency} {amount:,.2f} ({milestone_name}) "
            f"{'due ho chuka hai' if is_overdue else 'due hone wala hai'} on {due_date.strftime('%d-%b-%Y')}. "
            f"Please share update on the status. Thanks!"
        )
        
        english_draft = (
            f"Hi team, a quick reminder regarding the milestone payment for our campaign. "
            f"The payment of {currency} {amount:,.2f} for '{milestone_name}' is "
            f"{'currently overdue' if is_overdue else 'due'} on {due_date.strftime('%d-%b-%Y')} under our agreement. "
            f"Could you please share a status update or remittance advice once processed? Thank you!"
        )
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
                <h2 style="color: {'#e63946' if is_overdue else '#3182ce'}; border-bottom: 2px solid {'#e63946' if is_overdue else '#3182ce'}; padding-bottom: 10px;">
                    Payment Milestone Reminder ({status_label})
                </h2>
                <p>Hello,</p>
                <p>This is an automated alert from your Trendrop Payment Milestone Tracker. You have a payment milestone with <strong>{brand_name}</strong> that is {'overdue' if is_overdue else 'due soon'}:</p>
                
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                    <tr style="background-color: #f7fafc;">
                        <td style="padding: 10px; border: 1px solid #edf2f7; font-weight: bold;">Brand Name</td>
                        <td style="padding: 10px; border: 1px solid #edf2f7;">{brand_name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #edf2f7; font-weight: bold;">Milestone</td>
                        <td style="padding: 10px; border: 1px solid #edf2f7;">{milestone_name}</td>
                    </tr>
                    <tr style="background-color: #f7fafc;">
                        <td style="padding: 10px; border: 1px solid #edf2f7; font-weight: bold;">Amount Due</td>
                        <td style="padding: 10px; border: 1px solid #edf2f7; font-weight: bold; color: #e63946;">{currency} {amount:,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #edf2f7; font-weight: bold;">Due Date</td>
                        <td style="padding: 10px; border: 1px solid #edf2f7;">{due_date.strftime('%B %d, %Y')}</td>
                    </tr>
                </table>
                
                <div style="background-color: #ebf8ff; border-left: 4px solid #3182ce; padding: 15px; margin: 20px 0; border-radius: 4px;">
                    <h3 style="margin-top: 0; color: #2b6cb0;">📋 Ready-to-Send Brand Follow-Up Drafts</h3>
                    <p style="font-size: 13px; color: #4a5568;">Copy and paste one of the messages below to follow up with the brand team:</p>
                    
                    <p><strong>English Option:</strong></p>
                    <blockquote style="background: #fff; padding: 10px; border: 1px solid #e2e8f0; border-radius: 4px; font-size: 13px; margin: 5px 0;">
                        {english_draft}
                    </blockquote>
                    
                    <p><strong>Hinglish Option:</strong></p>
                    <blockquote style="background: #fff; padding: 10px; border: 1px solid #e2e8f0; border-radius: 4px; font-size: 13px; margin: 5px 0;">
                        {hinglish_draft}
                    </blockquote>
                </div>
                
                <p style="font-size: 12px; color: #a0aec0; margin-top: 30px; border-top: 1px solid #edf2f7; padding-top: 10px; text-align: center;">
                    Powered by Trendrop • Keep track of your brand deal contracts and payments.
                </p>
            </div>
        </body>
        </html>
        """
        
        # Send via Resend
        try:
            if not resend.api_key:
                logging.warning(f"RESEND_API_KEY is missing. Skipping actual email to {creator_email}, logged details: {subject}")
            else:
                try:
                    resend.Emails.send({
                        "from": from_email,
                        "to": creator_email,
                        "subject": subject,
                        "html": html_body
                    })
                    logging.info(f"Sent payment reminder email to {creator_email} for brand {brand_name}")
                except Exception as resend_err:
                    if "domain is not verified" in str(resend_err).lower() and from_email != "onboarding@resend.dev":
                        logging.warning("Retrying email send with onboarding@resend.dev fallback due to unverified domain...")
                        resend.Emails.send({
                            "from": "onboarding@resend.dev",
                            "to": creator_email,
                            "subject": subject,
                            "html": html_body
                        })
                        logging.info(f"Sent fallback payment reminder email to {creator_email} for brand {brand_name}")
                    else:
                        raise resend_err
                
            # Update milestone row reminder_sent_at
            sb.table("deal_payment_milestones").update({"reminder_sent_at": now.isoformat()}).eq("id", m["id"]).execute()
            emails_sent += 1
        except Exception as resend_err:
            logging.error(f"Failed to send/log reminder for milestone {m['id']}: {resend_err}")
            
    logging.info(f"Payment milestone reminders check complete. Sent: {emails_sent}")
    return emails_sent


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

    # Run daily sync immediately once on startup
    try:
        run_creator_sync_job()
    except Exception as e:
        logging.error(f"Startup creator sync failed: {e}", exc_info=True)

    # Run audio count check immediately on startup
    try:
        run_audio_count_check()
    except Exception as e:
        logging.error(f"Startup audio counts check failed: {e}", exc_info=True)

    # Run milestone reminders check immediately on startup
    try:
        check_and_send_milestone_reminders()
    except Exception as e:
        logging.error(f"Startup milestone reminders check failed: {e}", exc_info=True)

    # Schedule every 3 hours
    logging.info("Scheduling pipeline to run every 3 hours...")
    schedule.every(3).hours.do(run_full_pipeline)

    # Schedule every 6 hours for audio counts check
    logging.info("Scheduling audio counts check to run every 6 hours...")
    schedule.every(6).hours.do(run_audio_count_check)

    # Schedule every 12 hours for milestone reminders check
    logging.info("Scheduling milestone reminders check to run every 12 hours...")
    schedule.every(12).hours.do(check_and_send_milestone_reminders)

    # Schedule daily creator sync job
    logging.info("Scheduling daily creator sync job...")
    schedule.every().day.at("01:00").do(run_creator_sync_job)

    # Schedule daily at 2:00 AM IST
    logging.info("Scheduling daily data retention cleanup at 02:00 AM IST...")
    schedule.every().day.at("02:00").do(run_data_retention_job)

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logging.info("Cron job stopped by user (KeyboardInterrupt).")

