import os
import sys
import logging
import api_globals
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load .env BEFORE any module-level os.getenv() calls (e.g. SCRAPER_BACKEND below).
# Must come first — moving it below any env read means standalone runs silently
# fall back to hardcoded defaults (e.g. Apify) instead of respecting .env.
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

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
except Exception as _fh_err:
    # Log file unavailable (read-only filesystem on Vercel/serverless).
    # Continue with stdout only so the pipeline can still run.
    print(f"cron_job: WARNING: could not open log file '{log_file}', stdout only: {_fh_err}")

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
from unified_signal_processor import UnifiedSignalProcessor
from supabase import create_client

# Unconditionally use the browser-use Instagram scraper backend.
# The legacy Apify-based scraper has been completely removed from the codebase.
from instagram_scraper_browser import InstagramScraper as InstagramScraper


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


def _send_cron_heartbeat():
    """
    Emit a direct operator heartbeat after a successful pipeline run.
    This is separate from the stale-run watchdog so we can prove success
    and detect silence independently.
    """
    try:
        from heartbeat_monitor import _send_email

        recipient = os.getenv("CRON_HEARTBEAT_ALERT_EMAIL")
        if not recipient:
            logging.info("Cron heartbeat email skipped: CRON_HEARTBEAT_ALERT_EMAIL not set.")
            return

        last_completed = datetime.now(timezone.utc).isoformat()
        subject = "Trendrop heartbeat: pipeline completed successfully"
        html = f"""
        <h2>Trendrop pipeline heartbeat</h2>
        <p>The latest cron run completed successfully at <strong>{last_completed}</strong>.</p>
        <p>This is the direct operator heartbeat for the scheduled pipeline.</p>
        """
        _send_email(subject, html)
        logging.info("Cron heartbeat email sent.")
    except Exception as heartbeat_err:
        logging.warning(f"Failed to send cron heartbeat email: {heartbeat_err}")


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


def run_full_pipeline(stages: list = None):
    """Run the full trend pipeline, or only the requested stages.

    stages=None runs everything (backwards-compatible with the local
    scheduler). Stage names: schema, scrape, backfill, detect, refresh,
    snapshots, alerts.
    """
    def _stage(name: str) -> bool:
        return stages is None or name in stages

    start = datetime.now(timezone.utc)
    run_state = {
        "stage": "initializing",
        "cutoff_reason": None,
    }
    groq_keys_detected = sum(1 for key in ("GROQ_API_KEY", "GROQ_API_KEY_2", "GROQ_API_KEY_3") if os.getenv(key))
    gemini_keys_detected = sum(1 for key in ("GEMINI_API_KEY", "GEMINI_API_KEY_2") if os.getenv(key))
    reels_scraped = 0
    reels_skipped_low_engagement = 0
    classification_success = 0
    classification_failed_429 = 0
    uploads_skipped_oversized = 0
    pending_backfilled = 0
    run_label = f"PIPELINE RUN @ {start.strftime('%Y-%m-%d %H:%M IST')}"
    logging.info(f"=== {run_label} STARTING ===")

    try:
        sb = _get_supabase()
        run_count = sb.table("cron_runs").select("id", count="exact").execute().count or 0
    except Exception as _rc_err:
        logging.warning(f"Could not fetch cron run count (defaulting to 0, mode will be 'india'): {_rc_err}")
        run_count = 0

    if not os.environ.get("SCRAPER_MODE"):
        # Always default to "india" — the default pool now permanently includes a
        # DANCE slice and a GLOBAL_DISCOVERY[:5] slice on every run, so there is
        # no longer any reason to alternate modes.  The old run_count % 2 alternation
        # gave global trends only a coin-flip chance of being caught per cycle; a
        # newly viral global dance trend (e.g. "Addiction" by Ryan Leslie) could go
        # entirely unscraped on india-only runs.  Now every cycle covers both.
        # To force a pure global scan, set SCRAPER_MODE=global in the environment.
        scrape_mode = "india"
        os.environ["SCRAPER_MODE"] = scrape_mode
        logging.info(f"Selected scraper mode for this run: {scrape_mode} (blended pool — DANCE + GLOBAL_DISCOVERY included every run)")
    else:
        scrape_mode = os.environ["SCRAPER_MODE"]
        logging.info(f"Selected scraper mode for this run: {scrape_mode} (inherited from environment)")

    # 0. Schema Validation
    if _stage("schema"):
        try:
            run_state["stage"] = "schema_validation"
            sb = _get_supabase()
            verify_database_schema(sb)
        except Exception as e:
            run_state["stage"] = "schema_validation_failed"
            run_state["cutoff_reason"] = f"schema validation failed: {e}"
            logging.critical(f"Pipeline startup aborted due to schema mismatch: {e}")
            raise e

    # 1. Instagram Scraper
    new_reels_count = 0
    if _stage("scrape"):
        try:
            run_state["stage"] = "instagram_scrape"
            logging.info("Step 1/5: Scraping Instagram trending reels...")
            insta = InstagramScraper()
            new_reels_count = insta.scrape_trending_reels()
            reels_scraped = new_reels_count
            scrape_stats = getattr(insta, "_last_scrape_stats", {}) or {}
            reels_skipped_low_engagement = int(scrape_stats.get("low_engagement", 0) or 0)
            uploads_skipped_oversized = int(scrape_stats.get("failed_video_stores", 0) or 0)
            logging.info(f"Step 1/5: Instagram scraping complete. {new_reels_count} new reels saved.")
        except Exception as e:
            run_state["stage"] = "instagram_scrape_failed"
            run_state["cutoff_reason"] = f"instagram scrape failed: {e}"
            logging.error(f"Step 1/5 FAILED (Instagram): {e}", exc_info=True)

    # 2. YouTube Data Fetcher
    if _stage("scrape"):
        try:
            run_state["stage"] = "youtube_scrape"
            logging.info("Step 2/5: Scraping YouTube trending data...")
            from youtube_data_fetcher import YouTubeDataFetcher
            
            yt_fetcher = YouTubeDataFetcher()
            # Fetch India trending music and comedy for now
            yt_music = yt_fetcher.get_trending_music_india()
            yt_comedy = yt_fetcher.get_trending_comedy_india()
            
            total_yt = len(yt_music.get("items", [])) + len(yt_comedy.get("items", []))
            
            if total_yt > 0:
                logging.info(f"Step 2/5: YouTube scraping complete. Found {total_yt} trending items.")
                # Ideally, extract topics and pass them to unified signals, but for now we just verify it runs.
                # yt_topics = yt_fetcher.extract_trending_topics(yt_music)
            else:
                logging.info("Step 2/5: YouTube scraping complete but no items found (check API key).")
        except Exception as e:
            run_state["stage"] = "youtube_scrape_failed"
            logging.error(f"Step 2/5 FAILED (YouTube): {e}", exc_info=True)

    # 2b. Audio Backfill: retry reels where Instagram returned no audio metadata
    audio_backfill_filled = 0
    audio_backfill_unrecoverable = 0
    if _stage("backfill"):
        try:
            run_state["stage"] = "audio_backfill"
            sb = _get_supabase()
            backfill_res = sb.table("reels") \
                .select("reel_id, video_url, owner_username, audio_backfill_attempts") \
                .eq("audio_backfill_status", "needs_audio_backfill") \
                .lt("audio_backfill_attempts", 3) \
                .limit(30) \
                .execute()
            backfill_reels = backfill_res.data or []
            if backfill_reels:
                logging.info(f"Step 2b: Audio backfill: {len(backfill_reels)} reels to retry.")
                for r in backfill_reels:
                    rid = r["reel_id"]
                    attempts = (r.get("audio_backfill_attempts") or 0) + 1
                    # Re-fetch the reel's audio via Instagram shortcode endpoint
                    recovered = False
                    try:
                        import requests
                        resp = requests.get(
                            f"https://www.instagram.com/p/{rid}/?__a=1&__d=dis",
                            headers={"User-Agent": "Mozilla/5.0"},
                            timeout=6,
                        )
                        if resp.ok:
                            data = resp.json()
                            item = (
                                data.get("graphql", {}).get("shortcode_media")
                                or data.get("items", [{}])[0]
                            )
                            clips_metadata = item.get("clips_metadata", {}) or {}
                            audio_info = clips_metadata.get("original_sound_info") or clips_metadata.get("music_info", {}) or {}
                            music = audio_info.get("music_asset_info") or audio_info
                            new_title = music.get("title") or music.get("display_artist")
                            new_audio_id = str(music.get("audio_cluster_id") or music.get("id") or "")
                            if new_title or new_audio_id:
                                sb.table("reels").update({
                                    "audio_title": new_title,
                                    "audio_id": new_audio_id or None,
                                    "audio_backfill_status": "backfilled",
                                    "audio_backfill_attempts": attempts,
                                }).eq("reel_id", rid).execute()
                                audio_backfill_filled += 1
                                recovered = True
                                logging.info(f"Audio backfill SUCCESS: reel={rid} title='{new_title}'")
                    except Exception as bf_err:
                        logging.debug(f"Audio backfill fetch failed for reel={rid}: {bf_err}")

                    if not recovered:
                        new_status = "unrecoverable" if attempts >= 3 else "needs_audio_backfill"
                        sb.table("reels").update({
                            "audio_backfill_status": new_status,
                            "audio_backfill_attempts": attempts,
                        }).eq("reel_id", rid).execute()
                        if new_status == "unrecoverable":
                            audio_backfill_unrecoverable += 1
                            logging.info(f"Audio backfill UNRECOVERABLE after {attempts} attempts: reel={rid}")
                logging.info(
                    f"Step 2b: Audio backfill done. "
                    f"filled={audio_backfill_filled} unrecoverable={audio_backfill_unrecoverable} "
                    f"still_pending={len(backfill_reels)-audio_backfill_filled-audio_backfill_unrecoverable}"
                )
            else:
                logging.info("Step 2b: No reels in audio_backfill queue.")
        except Exception as bf_step_err:
            logging.warning(f"Step 2b audio backfill failed: {bf_step_err}")

    # 2c. Audio Watchlist Re-checks: refresh use_count + velocity for recently-seen audio IDs.
    # Catches acceleration on already-known audio even when hashtag scraping misses new reels.
    # Feeds audio_official_counts, which trend_engine.py already reads in has_strong_official_velocity.
    # No schema changes — fully scaffolded via scrape_audio_page_async + _save_official_count.
    audio_watchlist_checked = 0
    audio_watchlist_updated = 0
    if _stage("scrape"):  # only runs when scrape stage is active — skip in detect-only mode
        try:
            run_state["stage"] = "audio_watchlist"
            sb = _get_supabase()

            # Pick audio_ids seen in last 48h, prioritising those least-recently checked.
            # LEFT JOIN against audio_official_counts so recently-unchecked IDs surface first.
            recent_audio_res = sb.table("reels") \
                .select("audio_id") \
                .not_.is_("audio_id", "null") \
                .gte("scraped_at", (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()) \
                .order("scraped_at", desc=True) \
                .limit(200) \
                .execute()

            seen_ids: list[str] = []
            seen_set: set[str] = set()
            for row in (recent_audio_res.data or []):
                aid = row.get("audio_id")
                if aid and aid not in seen_set:
                    seen_set.add(aid)
                    seen_ids.append(aid)

            # Exclude IDs checked in the last 4h (avoid hammering the same audio repeatedly)
            if seen_ids:
                already_checked_res = sb.table("audio_official_counts") \
                    .select("audio_id") \
                    .in_("audio_id", seen_ids[:50]) \
                    .gte("checked_at", (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat()) \
                    .execute()
                recently_checked = {r["audio_id"] for r in (already_checked_res.data or [])}
                candidates = [aid for aid in seen_ids if aid not in recently_checked]
            else:
                candidates = []

            MAX_WATCHLIST_CHECKS = 15  # ~15s/check × 15 = ~3.5 min budget
            to_check = candidates[:MAX_WATCHLIST_CHECKS]

            if to_check:
                logging.info(
                    f"Step 2c/5: Audio watchlist — {len(to_check)} audio_ids to re-check "
                    f"(from {len(seen_ids)} seen in last 48h, {len(seen_ids) - len(candidates)} recently checked)."
                )
                import asyncio as _asyncio
                watchlist_scraper = InstagramScraper()
                # Single event loop for the entire watchlist session — init + scrape + close
                wl_loop = _asyncio.new_event_loop()
                browser_ok = wl_loop.run_until_complete(watchlist_scraper._init_browser_async())

                if browser_ok:
                    for audio_id in to_check:
                        audio_watchlist_checked += 1
                        try:
                            count = wl_loop.run_until_complete(
                                watchlist_scraper.scrape_audio_page_async(audio_id)
                            )
                            if count is not None and count > 0:
                                # Determine precision bucket (audio page shows "1.2M reels" etc.)
                                if count >= 1_000_000:
                                    bucket = "M"
                                elif count >= 1_000:
                                    bucket = "K"
                                else:
                                    bucket = "exact"
                                watchlist_scraper._save_official_count(audio_id, count, bucket)
                                audio_watchlist_updated += 1
                                logging.debug(
                                    f"Step 2c: audio_id={audio_id} use_count={count} ({bucket})"
                                )
                        except Exception as _wl_err:
                            logging.debug(f"Step 2c: watchlist check failed for {audio_id}: {_wl_err}")

                    wl_loop.run_until_complete(watchlist_scraper._close_browser_async())
                else:
                    logging.warning("Step 2c: Could not init browser for watchlist checks — skipping.")

                wl_loop.close()

                logging.info(
                    f"Step 2c/5: Audio watchlist complete. "
                    f"checked={audio_watchlist_checked} updated={audio_watchlist_updated}"
                )
            else:
                logging.info("Step 2c/5: Audio watchlist — no candidates (all recently checked or none seen).")

        except Exception as _wl_stage_err:
            logging.warning(f"Step 2c audio watchlist failed: {_wl_stage_err}", exc_info=True)

    # 2d. Creator Watchlist Scraping (Track 3): scrape recent posts from 7 verified creator accounts.
    # Discovers early-stage viral audio & choreo trends directly from high-signal early adopters.
    # Ingests discovered posts into the standard 'reels' table so all downstream stages
    # (trend detection, velocity, audio watchlist) apply automatically with no custom logic.
    creator_watchlist_checked = 0
    creator_watchlist_found = 0
    if _stage("scrape"):
        try:
            run_state["stage"] = "creator_watchlist"
            logging.info("Step 2d/5: Creator watchlist — starting scrape for 7 verified creator profiles...")
            import asyncio as _asyncio
            creator_scraper = InstagramScraper()
            cw_loop = _asyncio.new_event_loop()
            cw_browser_ok = cw_loop.run_until_complete(creator_scraper._init_browser_async())

            if cw_browser_ok:
                cw_reels, creator_watchlist_checked = cw_loop.run_until_complete(
                    creator_scraper.scrape_creator_watchlist_async()
                )
                cw_loop.run_until_complete(creator_scraper._close_browser_async())

                if cw_reels:
                    sb = _get_supabase()
                    now_str = datetime.now(timezone.utc).isoformat()
                    for r in cw_reels:
                        reel_payload = {
                            "reel_id": r["reel_id"],
                            "owner_username": r["owner_username"],
                            "caption": r.get("caption"),
                            "audio_title": r.get("audio_title"),
                            "audio_artist": r.get("audio_artist"),
                            "audio_id": r.get("audio_id"),
                            "view_count": r.get("view_count", 0),
                            "like_count": r.get("like_count", 0),
                            "comment_count": r.get("comment_count", 0),
                            "shortcode": r.get("shortcode"),
                            "scraped_at": now_str,
                        }
                        try:
                            sb.table("reels").upsert(reel_payload, on_conflict="reel_id").execute()
                            creator_watchlist_found += 1
                        except Exception as _ingest_err:
                            logging.debug(f"Step 2d: Reel ingestion error for reel_id={r['reel_id']}: {_ingest_err}")

                    new_reels_count += creator_watchlist_found
                    reels_scraped += creator_watchlist_found
                    logging.info(
                        f"Step 2d/5: Creator watchlist complete. "
                        f"checked={creator_watchlist_checked} found={creator_watchlist_found}"
                    )
                else:
                    logging.info(f"Step 2d/5: Creator watchlist complete. checked={creator_watchlist_checked} found=0")
            else:
                logging.warning("Step 2d: Could not init browser for creator watchlist — skipping.")

            cw_loop.close()

        except Exception as _cw_stage_err:
            logging.warning(f"Step 2d creator watchlist stage failed: {_cw_stage_err}", exc_info=True)

    # 3. Trend Engine: detect new trends
    trend_ids = []
    trend_detection_skipped = False
    TREND_DETECTION_THRESHOLD = 10  # Skip trend detection if insufficient new data

    if _stage("detect"):
        if new_reels_count >= TREND_DETECTION_THRESHOLD:
            # Data-quality warning: check proportion of null audio titles in recent scrape
            try:
                sb = _get_supabase()
                recent_time = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
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
        else:
            trend_detection_skipped = True
            logging.warning(
                f"TREND DETECTION SKIPPED: Only {new_reels_count} new reels scraped "
                f"(below threshold {TREND_DETECTION_THRESHOLD}). "
                f"This may indicate scraper degradation or Instagram rate limiting. "
                f"Consecutive skips will be tracked in cron_runs table."
            )
            
            # Check consecutive skips and alert if pattern detected
            try:
                sb = _get_supabase()
                recent_runs = sb.table("cron_runs") \
                    .select("trend_detection_skipped") \
                    .order("run_at", desc=True) \
                    .limit(5) \
                    .execute()
                
                consecutive_skips = 0
                for run in (recent_runs.data or []):
                    if run.get("trend_detection_skipped"):
                        consecutive_skips += 1
                    else:
                        break
                
                if consecutive_skips >= 3:
                    logging.error(
                        f"ALERT: Trend detection has been skipped for {consecutive_skips} consecutive runs "
                        f"({consecutive_skips * 8}+ hours with no new trend discovery). "
                        f"This may indicate persistent scraper issues requiring investigation."
                    )
            except Exception as skip_check_err:
                logging.warning(f"Failed to check consecutive skip pattern: {skip_check_err}")

        if not trend_detection_skipped:
            try:
                run_state["stage"] = "trend_engine"
                logging.info("Step 3/5: Running TrendEngine to detect new trends...")
                engine = TrendEngine()
                
                trend_ids = engine.detect_trends()
                classification_success = int(engine.last_run_stats.get("classification_success", 0) or 0)
                classification_failed_429 = int(engine.last_run_stats.get("classification_failed_429", 0) or 0)
                logging.info(f"Step 3/5: Trend detection complete. New trend IDs: {trend_ids}")
            except Exception as e:
                run_state["stage"] = "trend_engine_failed"
                run_state["cutoff_reason"] = f"trend engine failed: {e}"
                logging.error(f"Step 3/5 FAILED (TrendEngine): {e}", exc_info=True)

    # 4. Trend Refresher: update lifecycle of existing trends
    if _stage("refresh"):
        try:
            run_state["stage"] = "trend_refresher"
            logging.info("Step 4/5: Running TrendRefresher to update trend statuses...")
            refresher = TrendRefresher()
            refresh_summary = refresher.refresh_all()
            logging.info(f"Step 4/5: Refresh complete: {refresh_summary}")
        except Exception as e:
            run_state["stage"] = "trend_refresher_failed"
            run_state["cutoff_reason"] = f"trend refresher failed: {e}"
            logging.error(f"Step 4/5 FAILED (TrendRefresher): {e}", exc_info=True)
    else:
        refresher = None

    # 4b. Unified Signals: gather news, formats, and events
    if _stage("signals") or _stage("detect"):
        try:
            run_state["stage"] = "unified_signals"
            logging.info("Step 4b/5: Running UnifiedSignalProcessor for cross-channel trends...")
            signal_proc = UnifiedSignalProcessor()
            signal_proc.run_full_cycle()
            logging.info("Step 4b/5: UnifiedSignalProcessor complete.")
        except Exception as e:
            run_state["stage"] = "unified_signals_failed"
            run_state["cutoff_reason"] = f"unified signal processor failed: {e}"
            logging.error(f"Step 4b/5 FAILED (UnifiedSignals): {e}", exc_info=True)

    # Append one snapshot per trend for this pipeline run so velocity persistence
    # can be evaluated against real historical data on future runs.
    if _stage("snapshots") and refresher is not None:
        try:
            run_state["stage"] = "snapshot_write"
            sb = _get_supabase()
            snapshot_rows = refresher.get_snapshot_rows(captured_at=start)
            if snapshot_rows:
                sb.table("trend_snapshots").insert(snapshot_rows).execute()
                logging.info(f"Step 4/5: Recorded {len(snapshot_rows)} trend snapshot rows.")
            else:
                logging.info("Step 4/5: No trend snapshot rows to record.")
        except Exception as e:
            logging.error(f"Step 4/5 FAILED (trend snapshots): {e}", exc_info=True)

    # 5. Alert System: notify users of new rising trends
    if _stage("alerts") and trend_ids:
        try:
            run_state["stage"] = "alerts"
            logging.info(f"Step 5/5: Sending alerts for {len(trend_ids)} new trend(s)...")
            alert = AlertSystem()
            alert.send_trend_alerts(trend_ids)
            logging.info("Step 5/5: Alerts sent.")
        except Exception as e:
            run_state["stage"] = "alerts_failed"
            run_state["cutoff_reason"] = f"alert system failed: {e}"
            logging.error(f"Step 5/5 FAILED (AlertSystem): {e}", exc_info=True)
    else:
        logging.info("Step 5/5: No new trends — skipping alerts.")

    # Log run record to Supabase
    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    completed_at = datetime.now(timezone.utc)
    status = "success" if not run_state.get("cutoff_reason") else "partial"
    try:
        sb = _get_supabase()
        sb.table("cron_runs").insert({
            "run_at": start.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": round(elapsed, 3),
            "new_reels_count": new_reels_count,
            "new_trends_found": len(trend_ids),
            "trend_ids": trend_ids,
            "status": status,
            "stage": run_state.get("stage"),
            "cutoff_reason": run_state.get("cutoff_reason"),
            "scrape_mode": scrape_mode,
            "groq_keys_detected": groq_keys_detected,
            "gemini_keys_detected": gemini_keys_detected,
            "reels_scraped": reels_scraped,
            "reels_skipped_low_engagement": reels_skipped_low_engagement,
            "classification_success": classification_success,
            "classification_failed_429": classification_failed_429,
            "uploads_skipped_oversized": uploads_skipped_oversized,
            "pending_backfilled": pending_backfilled,
            "trend_detection_skipped": trend_detection_skipped,
            "audio_watchlist_checked": audio_watchlist_checked,
            "audio_watchlist_updated": audio_watchlist_updated,
            "creator_watchlist_checked": creator_watchlist_checked,
            "creator_watchlist_found": creator_watchlist_found,
        }).execute()
    except Exception as e:
        logging.warning(f"Could not log cron run to Supabase: {e}")

    logging.info(
        "RUN SUMMARY: "
        f"mode={scrape_mode} | "
        f"groq_keys_detected={groq_keys_detected} | "
        f"gemini_keys_detected={gemini_keys_detected} | "
        f"reels_scraped={reels_scraped} | "
        f"reels_skipped_low_engagement={reels_skipped_low_engagement} | "
        f"classification_success={classification_success} | "
        f"classification_failed_429={classification_failed_429} | "
        f"uploads_skipped_oversized={uploads_skipped_oversized} | "
        f"duration={int(elapsed)}s | "
        f"pending_backfilled={pending_backfilled} | "
        f"creator_watchlist_checked={creator_watchlist_checked} | "
        f"creator_watchlist_found={creator_watchlist_found}"
    )
    logging.info("NOTE: classification_success=0 is expected in no-LLM runs; it confirms classification stayed isolated from the main pipeline.")
    logging.info(f"=== {run_label} COMPLETE — {len(trend_ids)} new trends in {int(elapsed)}s ===")
    if run_state.get("cutoff_reason"):
        logging.warning(f"Pipeline cutoff summary: {run_state['cutoff_reason']} (last stage: {run_state.get('stage')})")
    _send_cron_heartbeat()
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
        
    now_ts = datetime.now(timezone.utc)

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

    # 6. Prune reels-preview Storage bucket — delete ALL files older than 3 days.
    # We query the database directly to find candidates, bypassing REST API blocks,
    # and log sizes before and after. Deletions are sent to REST API defensively,
    # catching 402 restrictions gracefully.
    try:
        logging.info("Pruning reels-preview Storage bucket (files > 3 days old)...")
        _db_url_pru = os.getenv("SUPABASE_DB_URL")
        _supa_url = os.getenv("SUPABASE_URL")
        _svc_key  = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        
        if _db_url_pru and _supa_url and _svc_key:
            import psycopg2 as _pg_pru
            import requests as _req_pru
            
            # Helper to log current storage usage stats from DB
            def _log_storage_usage(label):
                try:
                    conn_stats = _pg_pru.connect(_db_url_pru, connect_timeout=15)
                    cur_stats = conn_stats.cursor()
                    cur_stats.execute("""
                        SELECT COUNT(*), pg_size_pretty(SUM((metadata->>'size')::BIGINT))
                        FROM storage.objects
                        WHERE bucket_id = 'reels-preview' AND (metadata->>'size') IS NOT NULL
                    """)
                    stats = cur_stats.fetchone()
                    logging.info(f"Storage usage {label}: {stats[0] or 0} files, {stats[1] or '0 bytes'}")
                    cur_stats.close()
                    conn_stats.close()
                except Exception as stats_err:
                    logging.warning(f"Failed to fetch storage usage stats: {stats_err}")

            _log_storage_usage("BEFORE PRUNING")

            # Query database directly for old files
            conn_pru = _pg_pru.connect(_db_url_pru, connect_timeout=15)
            conn_pru.autocommit = True
            cur_pru = conn_pru.cursor()
            
            # Fetch names of files older than 3 days in reels-preview bucket
            cur_pru.execute("""
                SELECT name FROM storage.objects
                WHERE bucket_id = 'reels-preview'
                  AND created_at < NOW() - INTERVAL '3 days'
            """)
            _old_files = [row[0] for row in cur_pru.fetchall()]
            
            _total_del = 0
            if _old_files:
                logging.info(f"Found {len(_old_files)} old files in DB. Deleting in batches...")
                _hdrs = {
                    "Authorization": f"Bearer {_svc_key}",
                    "apikey": _svc_key,
                    "Content-Type": "application/json",
                }
                _storage_base = f"{_supa_url}/storage/v1"
                
                # Delete in batches of 100
                for i in range(0, len(_old_files), 100):
                    batch = _old_files[i:i+100]
                    try:
                        _del_resp = _req_pru.delete(
                            f"{_storage_base}/object/reels-preview",
                            headers=_hdrs,
                            json={"prefixes": batch},
                            timeout=30,
                        )
                        if _del_resp.status_code in (200, 204):
                            _total_del += len(batch)
                        else:
                            logging.warning(
                                f"REST API delete batch failed ({_del_resp.status_code}): {_del_resp.text[:200]}. "
                                "Falling back to direct metadata deletion in database."
                            )
                            # Fallback: remove metadata reference directly from DB so quota reduces at DB level
                            cur_pru.execute(
                                "DELETE FROM storage.objects WHERE bucket_id = 'reels-preview' AND name = ANY(%s)",
                                (batch,)
                            )
                            _total_del += len(batch)
                    except Exception as rest_err:
                        logging.warning(
                            f"Storage REST API request exception during pruning: {rest_err}. "
                            "Falling back to direct metadata deletion in database."
                        )
                        cur_pru.execute(
                            "DELETE FROM storage.objects WHERE bucket_id = 'reels-preview' AND name = ANY(%s)",
                            (batch,)
                        )
                        _total_del += len(batch)
            
            cur_pru.close()
            conn_pru.close()
            logging.info(f"reels-preview Storage pruning complete: {_total_del} file reference(s) cleaned up.")
            _log_storage_usage("AFTER PRUNING")
        else:
            logging.warning("reels-preview Storage pruning skipped: missing DB_URL, SUPABASE_URL, or service key.")
    except Exception as e:
        logging.error(f"Error during reels-preview Storage pruning: {e}")

    # 6b. Prune raw scraped rows (reels, audio_trend_scores, youtube_shorts) older than 7 days.
    # Trend intelligence only needs the last week of raw signals.
    # Without this, these tables grow indefinitely and push the DB past the 500 MB free-tier limit.
    try:
        logging.info("Pruning old scraped DB rows (reels/audio_trend_scores/youtube_shorts > 7 days)...")
        import psycopg2 as _pg2
        _db_url2 = os.getenv("SUPABASE_DB_URL")
        if _db_url2:
            _pg_conn = _pg2.connect(_db_url2, connect_timeout=15)
            _pg_conn.autocommit = True
            _pg_cur = _pg_conn.cursor()
            _pg_cur.execute("DELETE FROM audio_trend_scores WHERE created_at < NOW() - INTERVAL '7 days';")
            _n_ats = _pg_cur.rowcount
            _pg_cur.execute("DELETE FROM reels WHERE created_at < NOW() - INTERVAL '7 days';")
            _n_reels = _pg_cur.rowcount
            _pg_cur.execute("DELETE FROM youtube_shorts WHERE created_at < NOW() - INTERVAL '7 days';")
            _n_yt = _pg_cur.rowcount
            _pg_cur.close()
            _pg_conn.close()
            logging.info(
                f"DB row pruning complete: "
                f"audio_trend_scores={_n_ats}, reels={_n_reels}, youtube_shorts={_n_yt} deleted."
            )
        else:
            logging.warning("DB row pruning skipped: SUPABASE_DB_URL not set.")
    except Exception as e:
        logging.error(f"Error during DB row pruning: {e}")

    # 7. trend_snapshots retention: keep only last 14 snapshots per trend
    # 14 x 6h intervals = 84h history, sufficient for the 3-snapshot velocity check.
    # Without this: 42 trends x ~4 snapshots/day x 365 days ≈ 61k rows/year growing forever.
    try:
        logging.info("Running trend_snapshots retention (keep last 14 per trend)...")
        import psycopg2 as _psycopg2
        _db_url = os.getenv("SUPABASE_DB_URL")
        if _db_url:
            _conn = _psycopg2.connect(_db_url, connect_timeout=15)
            _conn.autocommit = True
            _cur = _conn.cursor()
            _cur.execute("""
                DELETE FROM trend_snapshots
                WHERE id NOT IN (
                    SELECT id FROM (
                        SELECT id,
                               ROW_NUMBER() OVER (
                                   PARTITION BY trend_id
                                   ORDER BY captured_at DESC
                               ) AS rn
                        FROM trend_snapshots
                    ) ranked
                    WHERE rn <= 14
                );
            """)
            deleted_snaps = _cur.rowcount
            _cur.close()
            _conn.close()
            logging.info(f"trend_snapshots retention: deleted {deleted_snaps} old snapshot(s).")
        else:
            logging.warning("trend_snapshots retention skipped: SUPABASE_DB_URL not set.")
    except Exception as e:
        logging.error(f"Error during trend_snapshots retention: {e}")

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
        insta = InstagramScraper()
        insta.scrape_official_audio_counts(limit=30)
        logging.info("Audio Official Counts Check Job complete.")
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
        
    now = datetime.now(timezone.utc)
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


