import logging
import os
import statistics
import time
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
from supabase import create_client, Client
from trend_scoring import calculate_opportunity_score, calculate_realistic_peaking_score, calculate_trend_state
from audio_title_normalize import normalize_audio_title

try:
    logging.basicConfig(
        filename="trend_refresher.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
except Exception as _log_cfg_err:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logging.warning(f"trend_refresher: could not open log file, falling back to stdout: {_log_cfg_err}")

logger = logging.getLogger(__name__)


class TrendRefresher:
    """
    Periodically refreshes the lifecycle status of all active trends in Supabase.

    Lifecycle:
      emerging  -> velocity spike detected, <5 creators adopted, not yet promoted
      rising    -> creator OR velocity gate passes with persistence filters
      peaked    -> velocity dropped >40% from its peak
      expired   -> older than 72 hours OR velocity near zero

    Also decrements `window_hours_remaining` for all active trends.
    """

    def __init__(self):
        load_dotenv()
        if not os.getenv("SUPABASE_URL"):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            load_dotenv(os.path.join(script_dir, ".env"))

        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase credentials missing from .env")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self.failed_trend_ids = set()

    def _retry_supabase_call(self, fn, max_retries: int = 3, delay: float = 0.5):
        """
        Executes a Supabase query function with exponential backoff on HTTP/2 network or connection drops.
        """
        for attempt in range(1, max_retries + 1):
            try:
                return fn()
            except Exception as e:
                err_str = str(e).lower()
                is_network_err = any(kw in err_str for kw in [
                    "server disconnected", "remoteprotocolerror", "connection closed",
                    "connection reset", "timeout"
                ])
                if is_network_err and attempt < max_retries:
                    sleep_time = delay * (2 ** (attempt - 1))
                    logger.warning(
                        f"[SUPABASE_RETRY] Attempt {attempt}/{max_retries} failed: {e}. "
                        f"Retrying in {sleep_time:.1f}s..."
                    )
                    time.sleep(sleep_time)
                else:
                    raise

    def _check_outage_guard(self, now: datetime, force_outage_guard: bool | None = None) -> bool:
        """
        Computes last successful Instagram ingest time (newest reels.scraped_at,
        or the latest cron_runs row with reels_scraped > 0). If older than 12h,
        returns True to prevent degrading trends during upstream outages.
        """
        if force_outage_guard is True:
            logger.warning("outage_guard_active: Forced via parameter override.")
            return True
        if force_outage_guard is False:
            return False

        force_env = os.getenv("FORCE_OUTAGE_GUARD")
        if force_env in ("1", "true", "True"):
            logger.warning("outage_guard_active: Forced via FORCE_OUTAGE_GUARD environment variable.")
            return True
        if force_env in ("0", "false", "False"):
            return False

        try:
            latest_reel_ts = None
            res_reels = self._retry_supabase_call(
                lambda: self.supabase.table("reels")
                .select("scraped_at")
                .order("scraped_at", desc=True)
                .limit(1)
                .execute()
            )
            if res_reels.data and res_reels.data[0].get("scraped_at"):
                ts_str = str(res_reels.data[0]["scraped_at"]).replace("Z", "+00:00")
                dt = datetime.fromisoformat(ts_str)
                latest_reel_ts = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

            latest_cron_ts = None
            res_cron = self._retry_supabase_call(
                lambda: self.supabase.table("cron_runs")
                .select("created_at")
                .gt("reels_scraped", 0)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if res_cron.data and res_cron.data[0].get("created_at"):
                ts_str = str(res_cron.data[0]["created_at"]).replace("Z", "+00:00")
                dt = datetime.fromisoformat(ts_str)
                latest_cron_ts = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

            candidates = [ts for ts in (latest_reel_ts, latest_cron_ts) if ts is not None]
            if not candidates:
                logger.warning("outage_guard_active: No previous successful ingest timestamps found in reels or cron_runs.")
                return True

            last_success = max(candidates)
            age_hours = (now - last_success).total_seconds() / 3600.0

            if age_hours > 12.0:
                logger.warning(
                    f"outage_guard_active: Last successful Instagram ingest was {age_hours:.1f}h ago (>12h threshold). "
                    f"Preserving active trend window_hours, preventing demotions to peaked/expired, and holding velocities."
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Error checking outage guard: {e}")
            return False

    def refresh_all(self, dry_run: bool = False, force_outage_guard: bool | None = None) -> dict:
        """
        Main entry point. Fetches all non-expired trends and refreshes their status.
        Returns summary counts.
        """
        self.dry_run = dry_run
        logger.info(f"=== TrendRefresher starting refresh_all (dry_run={dry_run}) ===")
        now = datetime.now(timezone.utc)
        outage_guard = self._check_outage_guard(now, force_outage_guard=force_outage_guard)
        if outage_guard:
            logger.warning("outage_guard_active: Outage guard enabled for this refresher run.")

        summary = {
            "total_processed": 0,
            "emerged": 0,
            "risen": 0,
            "peaked": 0,
            "expired": 0,
            "unqualified": 0,
            "errors": 0,
            "audio_use_count_refreshed": 0,
            "audio_page_count_refreshed": 0,
            "throttled": 0,
            "outage_guard_active": outage_guard,
        }
        self.failed_trend_ids = set()
        rising_baseline = self._get_rising_baseline()

        trends = []
        page_size = 1000
        offset = 0
        try:
            while True:
                res = self._retry_supabase_call(
                    lambda: self.supabase.table("trends")
                    .select("*")
                    .eq("is_seed_data", False)
                    .range(offset, offset + page_size - 1)
                    .execute()
                )
                batch = res.data or []
                trends.extend(batch)
                if len(batch) < page_size:
                    break
                offset += page_size
            logger.info(f"Found {len(trends)} total trends to refresh (paginated across {offset // page_size + 1} pages)")
        except Exception as e:
            logger.error(f"Failed to fetch trends: {e}", exc_info=True)
            return summary

        import concurrent.futures
        import threading
        
        summary_lock = threading.Lock()
        
        def process_trend(trend):
            local_summary = {"emerged": 0, "risen": 0, "peaked": 0, "expired": 0, "errors": 0, "audio_use_count_refreshed": 0, "audio_page_count_refreshed": 0, "throttled": 0}
            try:
                trend_id = trend["id"]
                audio_title = trend.get("audio_title", "?")
                created_at_str = trend.get("first_detected_at") or trend.get("created_at")
                current_status = trend.get("status", "rising")
                current_velocity = trend.get("velocity_avg", 0.0)
                peak_velocity = trend.get("peak_velocity") or current_velocity
                window_hours = trend.get("window_hours_remaining", 24)

                # Always refresh audio use count first, regardless of status (skip DB write on dry_run)
                if not dry_run:
                    if self._refresh_audio_use_count(trend):
                        local_summary["audio_use_count_refreshed"] += 1

                # Note: Official Instagram audio page counts are now harvested with cookies
                # by the authenticated Human-Mimic Harvester in cron_job.py / instagram_scraper_browser.py.
                # Unauthenticated raw requests here are bypassed to prevent 429 blocks and useless sleep delays.

                # Refresh peaking score for active trends
                if not dry_run and current_status in ["emerging", "rising"]:
                    self._refresh_peaking_score(trend)

                # Only run state transitions and velocity calculations for active status.
                # Allow "peaked" and "expired" through so they can recover to "emerging" if momentum returns.
                if current_status not in ["emerging", "rising", "peaked", "expired"]:
                    return local_summary

                if created_at_str:
                    if created_at_str.endswith("Z"):
                        created_at_str = created_at_str[:-1] + "+00:00"
                    created_at = datetime.fromisoformat(created_at_str)
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                else:
                    created_at = now

                age_hours = (now - created_at).total_seconds() / 3600

                try:
                    norm_title = normalize_audio_title(trend.get("audio_title", ""))
                    # 30-day window: unbounded artist queries are unsafe for
                    # "Unknown Artist" fallback bucket (every unknown-artist reel).
                    reel_window = (now - timedelta(days=30)).isoformat()
                    res_total = self.supabase.table("reels") \
                        .select("reel_id, audio_title") \
                        .eq("audio_artist", trend.get("audio_artist")) \
                        .gte("created_at", reel_window) \
                        .execute()
                    live_reels_count = sum(
                        1 for r in (res_total.data or [])
                        if normalize_audio_title(r.get("audio_title", "") or "") == norm_title
                    )
                except Exception as e:
                    logger.warning(f"Failed to check total reels count for '{audio_title}': {e}")
                    live_reels_count = 0

                # Never allow reel_count to decrease: the reels table may be pruned/deduped,
                # but the trend's peak reel count is a fact that should be preserved.
                stored_reel_count = trend.get("reel_count") or 0
                total_reels_count = max(live_reels_count, stored_reel_count)

                # Unqualify orphan/single-reel tracks with 0 usage count only after 72h age gate
                # (gives scraper sampling and audio page harvester 3 days to acquire adoption evidence)
                clean_use_cnt = int(trend.get("audio_use_count") or 0)
                if clean_use_cnt == 0 and total_reels_count <= 1 and age_hours > 72.0:
                    if outage_guard:
                        logger.info(f"outage_guard_active: Skipping unqualify demotion for '{audio_title}' (id={trend_id}).")
                    else:
                        self._update_status(trend_id, "unqualified", {
                            "window_hours_remaining": 0,
                            "reel_count": total_reels_count,
                            "high_confidence": False,
                            "promotion_reason": "unqualified_single_reel_zero_count",
                        })
                        logger.info(f"[UNQUALIFY_SINGLE_REEL] '{audio_title}' (id={trend_id}) has 0 use_count and {total_reels_count} reels (age={age_hours:.1f}h).")
                        local_summary["unqualified"] = local_summary.get("unqualified", 0) + 1
                        return local_summary

                # Real short-form trends last 1 to 3 weeks (14 days = 336h).
                min_visible_hours = float(os.getenv("TREND_VISIBILITY_MIN_HOURS", str(14 * 24)))

                live_velocity = self._calc_live_velocity(
                    trend.get("audio_title"), trend.get("audio_artist"), now
                )

                try:
                    threshold_6h = (now - timedelta(hours=6)).isoformat()
                    res_count = self.supabase.table("reels") \
                        .select("reel_id, audio_title, scraped_at") \
                        .eq("audio_artist", trend.get("audio_artist")) \
                        .gte("scraped_at", threshold_6h) \
                        .execute()
                    new_reels_count = sum(
                        1 for r in (res_count.data or [])
                        if normalize_audio_title(r.get("audio_title", "") or "") == norm_title
                    )
                except Exception as e:
                    logger.warning(f"Failed to check new reels count for '{audio_title}': {e}")
                    new_reels_count = 0

                clean_use_cnt = int(trend.get("audio_use_count") or 0)
                if outage_guard:
                    if window_hours <= 0:
                        new_window = 0
                        logger.info(f"outage_guard_active: Trend '{audio_title}' already at window_hours_remaining<=0; allowing expiration.")
                    else:
                        new_window = window_hours
                        logger.info(f"outage_guard_active: Preserving window_hours_remaining={new_window}h for '{audio_title}' (no decrement).")
                elif new_reels_count > 0:
                    new_window = min(48, window_hours + 12)
                    logger.info(f"[EXTENDED] '{audio_title}' window extended to {new_window}h due to {new_reels_count} new reels.")
                elif age_hours < 168.0:
                    # Protect new trends (first 7 days) from premature expiration due to scraper sampling gaps
                    new_window = max(24, window_hours - 1)
                elif clean_use_cnt >= 50000 or total_reels_count >= 2:
                    # Protect active/popular tracks with established adoption
                    new_window = max(24, window_hours - 1)
                else:
                    new_window = max(0, window_hours - 1)

                # 14-day ceiling for peaked trends (force to expired)
                if not outage_guard and current_status == "peaked" and age_hours >= (14 * 24.0):
                    self._update_status(trend_id, "expired", {
                        "window_hours_remaining": 0,
                        "reel_count": total_reels_count,
                        "high_confidence": bool(trend.get("high_confidence", False)),
                        "promotion_reason": "peaked_14d_age_out",
                    }, previous_status=current_status)
                    logger.info(f"[EXPIRED_PEAKED_14D] '{audio_title}' aged out of peaked after {age_hours:.1f}h")
                    local_summary["expired"] += 1
                    return local_summary

                # Trends with window <= 0 must expire even during outage guard.
                # Age ceiling check applies when outage guard is not active.
                if new_window <= 0 or (not outage_guard and age_hours >= min_visible_hours):
                    self._update_status(trend_id, "expired", {
                        "window_hours_remaining": 0,
                        "reel_count": total_reels_count,
                        "high_confidence": bool(trend.get("high_confidence", False)),
                        "promotion_reason": trend.get("promotion_reason"),
                    }, previous_status=current_status)
                    logger.info(f"[EXPIRED] '{audio_title}' (age={age_hours:.1f}h, window={new_window}h)")
                    local_summary["expired"] += 1
                    return local_summary

                # Hold measured velocity steady if scraper did not sample this artist in the last 24h.
                # Never artificially decay velocity via synthetic multipliers (e.g. * 0.85) which causes false peaking.
                velocity_for_check = live_velocity if live_velocity > 0 else current_velocity
                self._refresh_opportunity_score(trend, confidence=trend.get("confidence"), window_hours_remaining=new_window)

                # Peaked/Expired recovery MUST pass the Resurgence Gate
                # (Sustained signal across 2+ snapshots with velocity >= 3,000 and unique_creators >= 3).
                if current_status in ["peaked", "expired"]:
                    unique_creators = self._count_unique_creators(
                        trend.get("audio_title"), trend.get("audio_artist"), datetime.now(timezone.utc)
                    )
                    
                    snaps_res = self.supabase.table("trend_snapshots") \
                        .select("velocity_avg, creator_count, captured_at") \
                        .eq("trend_id", trend_id) \
                        .order("captured_at", desc=True) \
                        .limit(2) \
                        .execute()
                    snapshots = snaps_res.data or []
                    
                    from trend_constants import RESURGENCE_VELOCITY_THRESHOLD
                    clean_use_cnt = int(trend.get("audio_use_count") or 0)
                    is_valid_breakout_resurgence = (
                        unique_creators >= 1 and (velocity_for_check >= RESURGENCE_VELOCITY_THRESHOLD * 2 or clean_use_cnt >= 10000)
                    )
                    creator_gate_passed = (unique_creators >= 3 or is_valid_breakout_resurgence)

                    has_sustained_signal = (
                        len(snapshots) >= 2 and
                        creator_gate_passed and
                        all((s.get("velocity_avg") or 0) >= RESURGENCE_VELOCITY_THRESHOLD for s in snapshots) and
                        velocity_for_check >= RESURGENCE_VELOCITY_THRESHOLD
                    )
                    
                    if has_sustained_signal:
                        self._update_status(trend_id, "resurging", {
                            "window_hours_remaining": new_window,
                            "velocity_avg": velocity_for_check,
                            "reel_count": total_reels_count,
                            "high_confidence": bool(trend.get("high_confidence", False)),
                            "promotion_reason": "resurgence_gate",
                        }, previous_status=current_status)
                        logger.info(f"[RESURGING] '{audio_title}' {current_status}→resurging (velocity={velocity_for_check:.2f}, creators={unique_creators})")
                        local_summary["recovered"] = local_summary.get("recovered", 0) + 1
                        return local_summary
                    else:
                        # Resurgence gate denied: remain peaked/expired, log decision
                        if not dry_run:
                            self.supabase.table("trends").update({
                                "velocity_avg": velocity_for_check,
                                "reel_count": total_reels_count,
                                "status_reason": {
                                    "new_status": current_status,
                                    "previous_status": current_status,
                                    "trigger_source": "refresher_resurgence_gate_denied",
                                    "snapshots_evaluated": len(snapshots),
                                    "decision_metrics": {
                                        "velocity_avg": velocity_for_check,
                                        "unique_creators": unique_creators
                                    }
                                }
                            }).eq("id", trend_id).execute()
                        return local_summary

                if not outage_guard and velocity_for_check < peak_velocity * 0.60 and peak_velocity > 0:
                    # Anti-flicker: require 2 consecutive low-velocity snapshots before demoting.
                    # Fail-safe: Require explicit snapshot history before demoting to peaked.
                    try:
                        snaps_res = self.supabase.table("trend_snapshots") \
                            .select("velocity_avg") \
                            .eq("trend_id", trend_id) \
                            .order("captured_at", desc=True) \
                            .limit(2) \
                            .execute()
                        snap_vels = [float(s.get("velocity_avg") or 0.0) for s in (snaps_res.data or [])]
                        # Need at least 2 historical snapshots both below the threshold
                        two_dip_confirmed = (
                            len(snap_vels) >= 2
                            and all(v < peak_velocity * 0.60 for v in snap_vels)
                        )
                    except Exception as _snap_err:
                        logger.debug(f"Anti-flicker snapshot check failed for trend_id={trend_id}: {_snap_err}")
                        two_dip_confirmed = False  # Fail-safe: Hold current status if snapshots unavailable

                    if two_dip_confirmed:
                        self._update_status(trend_id, "peaked", {
                            "window_hours_remaining": new_window,
                            "velocity_avg": velocity_for_check,
                            "reel_count": total_reels_count,
                            "high_confidence": bool(trend.get("high_confidence", False)),
                            "promotion_reason": trend.get("promotion_reason"),
                        }, previous_status=current_status)
                        logger.info(f"[PEAKED] '{audio_title}' (was {peak_velocity:.2f}, now {velocity_for_check:.2f}, 2-dip confirmed)")
                        local_summary["peaked"] += 1
                        return local_summary
                    else:
                        logger.info(f"[ANTI-FLICKER] '{audio_title}' low velocity but held — protecting active feed ({current_status})")

                creator_count = self._count_unique_creators(
                    trend.get("audio_title"), trend.get("audio_artist"), now
                )
                high_confidence = creator_count >= 5

                # 24-hour Hold Window: Give newly created emerging trends a 24h immunity window in "emerging" status
                # before allowing lifecycle re-evaluation to prevent premature eviction from Emerging tab.
                if current_status == "emerging" and age_hours < 24.0:
                    logger.info(f"[EMERGING_HOLD] '{audio_title}' (id={trend_id}, age={age_hours:.2f}h < 24.0h) — holding in emerging for 24h window")
                    self._update_status(trend_id, "emerging", {
                        "window_hours_remaining": new_window,
                        "velocity_avg": velocity_for_check,
                        "peak_velocity": max(velocity_for_check, peak_velocity),
                        "reel_count": total_reels_count,
                        "high_confidence": high_confidence,
                    }, previous_status=current_status)
                    local_summary["emerged"] = local_summary.get("emerged", 0) + 1
                    return local_summary

                trend_state = calculate_trend_state(
                    velocity_avg=velocity_for_check,
                    global_saturation_pct=trend.get("global_saturation_pct", 0.0),
                    india_saturation_pct=trend.get("india_saturation_pct", 0.0),
                    window_hours_remaining=new_window,
                    audio_use_count=clean_use_cnt,
                    confidence=trend.get("confidence", 0.8),
                    max_velocity=max(velocity_for_check, peak_velocity),
                    discovery_source=trend.get("discovery_source", "regional"),
                    unique_creators=creator_count,
                )
                new_status = trend_state.lifecycle.value

                # Outage guard protection: Prevent demoting active trends to peaked/expired/unqualified
                if outage_guard and current_status in ["emerging", "rising", "resurging"] and new_status in ["peaked", "expired", "unqualified"]:
                    logger.info(f"outage_guard_active: Holding '{audio_title}' in '{current_status}' (prevented demotion to '{new_status}').")
                    new_status = current_status

                # Outage guard & creator floor protection:
                # No promotions (rising/emerging) during an outage blackout, or if creator count is 0
                if outage_guard and new_status in ["rising", "emerging"] and new_status != current_status:
                    logger.info(f"outage_guard_active: Blocking promotion of '{audio_title}' to '{new_status}' during outage (holding in '{current_status}').")
                    new_status = current_status
                elif new_status in ["rising", "emerging"] and new_status != current_status and creator_count == 0:
                    logger.info(f"creator_floor_active: Blocking promotion of '{audio_title}' to '{new_status}' because creators=0 (holding in '{current_status}').")
                    new_status = current_status

                self._update_status(trend_id, new_status, {
                    "window_hours_remaining": new_window,
                    "velocity_avg": velocity_for_check,
                    "peak_velocity": max(velocity_for_check, peak_velocity),
                    "reel_count": total_reels_count,
                    "high_confidence": high_confidence,
                }, previous_status=current_status, decision_metrics={
                    "velocity_avg": velocity_for_check,
                    "peak_velocity": max(velocity_for_check, peak_velocity),
                    "reel_count": total_reels_count,
                    "unique_creators": creator_count,
                    "audio_use_count": clean_use_cnt,
                })
                logger.info(f"[{new_status.upper()}] '{audio_title}' (id={trend_id}, creators={creator_count}, velocity={velocity_for_check:.2f})")
                local_summary[new_status] = local_summary.get(new_status, 0) + 1
                    
            except Exception as e:
                logger.error(f"Error refreshing trend_id={trend.get('id')}: {e}", exc_info=True)
                if trend.get("id"):
                    self.failed_trend_ids.add(trend["id"])
                local_summary["errors"] += 1
                
            return local_summary

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            for local_summary in executor.map(process_trend, trends):
                with summary_lock:
                    for k, v in local_summary.items():
                        summary[k] = summary.get(k, 0) + v

        logger.info(f"=== TrendRefresher done: {summary} ===")
        return summary

    def _update_status(self, trend_id: int, status: str, extra: dict = None, previous_status: str = None, decision_metrics: dict = None):
        if getattr(self, "dry_run", False):
            logger.info(f"[DRY_RUN] Would update trend_id={trend_id} to status='{status}' extra={extra}")
            return
        payload = {"status": status}
        if extra:
            payload.update(extra)
        status_reason = {
            "previous_status": previous_status,
            "new_status": status,
            "transition_timestamp": datetime.now(timezone.utc).isoformat(),
            "trigger_source": "refresher",
            "decision_metrics": decision_metrics or extra or {}
        }
        payload["status_reason"] = status_reason
        self._retry_supabase_call(lambda: self.supabase.table("trends").update(payload).eq("id", trend_id).execute())

    def _refresh_opportunity_score(self, trend: dict, *, confidence: float | None = None, window_hours_remaining: float | None = None) -> float:
        score = calculate_opportunity_score(
            india_saturation_pct=trend.get("india_saturation_pct") or 0.0,
            window_hours_remaining=window_hours_remaining if window_hours_remaining is not None else trend.get("window_hours_remaining") or 0.0,
            confidence=confidence if confidence is not None else trend.get("confidence") or 0.0,
        )
        try:
            if not getattr(self, "dry_run", False):
                self._retry_supabase_call(lambda: self.supabase.table("trends").update({"opportunity_score": score}).eq("id", trend["id"]).execute())
        except Exception as e:
            logger.warning(f"Could not refresh opportunity_score for trend_id={trend.get('id')}: {e}")
        return score

    def _refresh_peaking_score(self, trend: dict) -> float:
        """
        Refresh peaking score for a trend based on recent snapshots.
        """
        trend_id = trend["id"]
        
        try:
            # Get snapshots for this trend
            snapshots_res = self._retry_supabase_call(
                lambda: self.supabase.table('trend_snapshots')
                .select('velocity_avg, captured_at')
                .eq('trend_id', trend_id)
                .order('captured_at', desc=True)
                .limit(10)
                .execute()
            )
            
            snapshots = snapshots_res.data or []
            peaking_score = calculate_realistic_peaking_score(trend, snapshots)
            
            # Update the peaking score in database
            if not getattr(self, "dry_run", False):
                self._retry_supabase_call(lambda: self.supabase.table("trends").update({"peaking_score": peaking_score}).eq("id", trend_id).execute())
            
            return peaking_score
        except Exception as e:
            logger.warning(f"Could not refresh peaking_score for trend_id={trend.get('id')}: {e}")
            return 0.0

    def _refresh_audio_page_count(self, trend_id: int, audio_id: str) -> bool:
        """
        Bypassed: Audio page reel counts are now harvested with valid session cookies
        by the authenticated Human-Mimic Camoufox Harvester in instagram_scraper_browser.py.
        Unauthenticated requests here are no-oped to prevent 429 rate-limiting.
        """
        return False

    def _refresh_audio_use_count(self, trend: dict) -> bool:
        """
        Re-reads max(audio_use_count) from the reels table for this trend's audio
        and updates trends.audio_use_count if the reels table has a fresher/higher value.

        Uses audio_id match first (exact), then falls back to audio_title+audio_artist.
        Returns True if an update was written.
        """
        trend_id = trend["id"]
        stored_count = trend.get("audio_use_count") or 0
        audio_id = trend.get("audio_id")
        audio_title = trend.get("audio_title")
        audio_artist = trend.get("audio_artist")

        try:
            if audio_id:
                res = self._retry_supabase_call(
                    lambda: self.supabase.table("reels")
                    .select("audio_use_count")
                    .eq("audio_id", audio_id)
                    .execute()
                )
            elif audio_title and audio_artist:
                normalized_title = normalize_audio_title(audio_title)
                res = self._retry_supabase_call(
                    lambda: self.supabase.table("reels")
                    .select("audio_use_count, audio_title")
                    .eq("audio_artist", audio_artist)
                    .execute()
                )
                matching = [
                    r for r in (res.data or [])
                    if normalize_audio_title(r.get("audio_title", "") or "") == normalized_title
                ]
            else:
                return False

            counts = [
                r["audio_use_count"]
                for r in (matching if audio_title and audio_artist and not audio_id else (res.data or []))
                if r.get("audio_use_count") is not None
                and r["audio_use_count"] > 0
            ]
            if not counts:
                return False

            live_max = max(counts)
            if live_max > stored_count:
                self._retry_supabase_call(
                    lambda: self.supabase.table("trends")
                    .update({"audio_use_count": live_max})
                    .eq("id", trend_id)
                    .execute()
                )
                logger.info(
                    f"[AUDIO_USE_COUNT] trend_id={trend_id} '{audio_title}': "
                    f"{stored_count} -> {live_max} (delta={live_max - stored_count:+,})"
                )
                return True
            return False
        except Exception as e:
            logger.warning(f"Could not refresh audio_use_count for trend_id={trend_id}: {e}")
            return False

    def _calc_live_velocity(self, audio_title: str, audio_artist: str, now: datetime) -> float:
        """Recalculates avg velocity_score of reels matching this audio in last 24h."""
        try:
            normalized_title = normalize_audio_title(audio_title)
            threshold = (now - timedelta(hours=24)).isoformat()
            res = self._retry_supabase_call(
                lambda: self.supabase.table("reels")
                .select("velocity_score, audio_title")
                .eq("audio_artist", audio_artist)
                .gte("created_at", threshold)
                .execute()
            )
            matching = [
                r for r in (res.data or [])
                if normalize_audio_title(r.get("audio_title", "") or "") == normalized_title
            ]
            scores = [r.get("velocity_score", 0.0) for r in matching]
            return sum(scores) / len(scores) if scores else 0.0
        except Exception as e:
            logger.warning(f"Could not calc live velocity for '{audio_title}': {e}")
            return 0.0

    def _count_unique_creators(self, audio_title: str, audio_artist: str, now: datetime) -> int:
        """Counts distinct creator usernames using this audio in last 48h."""
        try:
            normalized_title = normalize_audio_title(audio_title)
            threshold = (now - timedelta(hours=48)).isoformat()
            res = self._retry_supabase_call(
                lambda: self.supabase.table("reels")
                .select("owner_username, audio_title")
                .eq("audio_artist", audio_artist)
                .gte("created_at", threshold)
                .execute()
            )
            matching = [
                r for r in (res.data or [])
                if normalize_audio_title(r.get("audio_title", "") or "") == normalized_title
            ]
            usernames = {r.get("owner_username") for r in matching if r.get("owner_username")}
            return len(usernames)
        except Exception as e:
            logger.warning(f"Could not count creators for '{audio_title}': {e}")
            return 0

    def _get_rising_baseline(self) -> float:
        """
        7-day rolling median over all trends detected in the last 7 days.
        This is broader than the active-only median and less sensitive to tiny samples.
        """
        try:
            res = self._retry_supabase_call(
                lambda: self.supabase.table("trends")
                .select("velocity_avg")
                .eq("is_seed_data", False)
                .gte("first_detected_at", (datetime.now(timezone.utc) - timedelta(days=7)).isoformat())
                .execute()
            )
            velocities = [
                float(r.get("velocity_avg"))
                for r in (res.data or [])
                if isinstance(r.get("velocity_avg"), (int, float))
            ]
            return float(statistics.median(velocities)) if velocities else 0.0
        except Exception as e:
            logger.warning(f"Could not compute rising baseline: {e}")
            return 0.0

    def _velocity_promotion_allowed(self, trend_id: int, current_velocity: float, baseline: float):
        """
        Velocity-only promotion requires three real snapshot rows with non-decreasing
        velocity across the window, plus the latest snapshot above threshold.
        A tiny 3% tolerance absorbs measurement noise.
        """
        try:
            res = self.supabase.table("trend_snapshots") \
                .select("velocity_avg,captured_at") \
                .eq("trend_id", trend_id) \
                .order("captured_at", desc=True) \
                .limit(3) \
                .execute()
            snaps = list(reversed(res.data or []))
            if len(snaps) < 3:
                return False, f"insufficient_history({len(snaps)})"
            velocities = [float(s.get("velocity_avg") or 0.0) for s in snaps]
            tolerance = 0.03
            nondecreasing = True
            for prev, nxt in zip(velocities, velocities[1:]):
                if nxt + (abs(prev) * tolerance) < prev:
                    nondecreasing = False
                    break
            if not nondecreasing:
                return False, "decreasing_history"
            threshold = baseline * 1.5 if baseline > 0 else 0.0
            if velocities[-1] < threshold:
                return False, "below_threshold"
            return True, "ok"
        except Exception as e:
            logger.warning(f"Could not evaluate velocity promotion for trend_id={trend_id}: {e}")
            return False, f"error:{type(e).__name__}"

    def get_snapshot_rows(self, trend_ids=None, captured_at=None):
        """
        Build append-only snapshot rows for the current run.
        The pipeline should call this once per run after trend refresh completes.
        Paginates trends and skips any trends that errored during refresh.
        """
        try:
            trends = []
            page_size = 1000
            offset = 0
            while True:
                query = self.supabase.table("trends").select("id,audio_title,audio_artist,velocity_avg").eq("is_seed_data", False)
                if trend_ids:
                    query = query.in_("id", list(trend_ids))
                batch = query.range(offset, offset + page_size - 1).execute().data or []
                trends.extend(batch)
                if len(batch) < page_size or trend_ids:
                    break
                offset += page_size

            failed_ids = getattr(self, "failed_trend_ids", set())
            valid_trends = [t for t in trends if t.get("id") not in failed_ids]
            if failed_ids:
                logger.warning(f"get_snapshot_rows: Skipped {len(failed_ids)} errored trends from snapshot write.")

            rows = []
            now_iso = (captured_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
            
            def process_snapshot(trend):
                creator_count = self._count_unique_creators(
                    trend.get("audio_title"), trend.get("audio_artist"), datetime.now(timezone.utc)
                )
                return {
                    "trend_id": trend["id"],
                    "velocity_avg": trend.get("velocity_avg"),
                    "creator_count": creator_count,
                    "captured_at": now_iso,
                }
            
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                rows = list(executor.map(process_snapshot, valid_trends))
                
            return rows
        except Exception as e:
            logger.warning(f"Could not build trend snapshot rows: {e}")
            return []


if __name__ == "__main__":
    refresher = TrendRefresher()
    result = refresher.refresh_all()
    print(f"Refresh complete: {result}")
