import logging
import logging
import os
import statistics
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
from supabase import create_client, Client
from trend_scoring import calculate_opportunity_score, calculate_realistic_peaking_score
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

    def refresh_all(self) -> dict:
        """
        Main entry point. Fetches all non-expired trends and refreshes their status.
        Returns summary counts.
        """
        logger.info("=== TrendRefresher starting refresh_all ===")
        now = datetime.now(timezone.utc)
        summary = {
            "total_processed": 0,
            "emerged": 0,
            "risen": 0,
            "peaked": 0,
            "expired": 0,
            "errors": 0,
            "audio_use_count_refreshed": 0,
            "audio_page_count_refreshed": 0,
            "throttled": 0,
        }
        rising_baseline = self._get_rising_baseline()

        try:
            res = self.supabase.table("trends") \
                .select("*") \
                .eq("is_seed_data", False) \
                .execute()
            trends = res.data or []
            logger.info(f"Found {len(trends)} total trends to refresh")
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
                created_at_str = trend.get("first_detected_at")
                current_status = trend.get("status", "rising")
                current_velocity = trend.get("velocity_avg", 0.0)
                peak_velocity = trend.get("peak_velocity") or current_velocity
                window_hours = trend.get("window_hours_remaining", 24)

                # Always refresh audio use count first, regardless of status
                if self._refresh_audio_use_count(trend):
                    local_summary["audio_use_count_refreshed"] += 1

                # Refresh official Instagram audio page count every other run (rate limit safe)
                audio_id = trend.get("audio_id")
                if audio_id and current_status in ["emerging", "rising"]:
                    refresh_result = self._refresh_audio_page_count(trend_id, audio_id)
                    if refresh_result == "THROTTLED":
                        local_summary["throttled"] += 1
                    elif refresh_result is True:
                        local_summary["audio_page_count_refreshed"] += 1

                # Refresh peaking score for active trends
                if current_status in ["emerging", "rising"]:
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
                    # Defensive fallback: If first_detected_at is ever NULL, treat the trend
                    # as newly born (now) rather than pre-decayed (12 hours ago).
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

                min_visible_hours = float(os.getenv("TREND_VISIBILITY_MIN_HOURS", str(3 * 24)))

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

                if new_reels_count > 0:
                    new_window = min(48, window_hours + 12)
                    logger.info(f"[EXTENDED] '{audio_title}' window extended to {new_window}h due to {new_reels_count} new reels.")
                else:
                    new_window = max(0, window_hours - 3)

                # 14-day ceiling for peaked trends (force to expired)
                if current_status == "peaked" and age_hours >= (14 * 24.0):
                    self._update_status(trend_id, "expired", {
                        "window_hours_remaining": 0,
                        "reel_count": total_reels_count,
                        "high_confidence": bool(trend.get("high_confidence", False)),
                        "promotion_reason": "peaked_14d_age_out",
                    })
                    logger.info(f"[EXPIRED_PEAKED_14D] '{audio_title}' aged out of peaked after {age_hours:.1f}h")
                    local_summary["expired"] += 1
                    return local_summary

                if age_hours >= min_visible_hours or new_window <= 0:
                    self._update_status(trend_id, "expired", {
                        "window_hours_remaining": 0,
                        "reel_count": total_reels_count,
                        "high_confidence": bool(trend.get("high_confidence", False)),
                        "promotion_reason": trend.get("promotion_reason"),
                    })
                    logger.info(f"[EXPIRED] '{audio_title}' (age={age_hours:.1f}h)")
                    local_summary["expired"] += 1
                    return local_summary

                velocity_for_check = live_velocity if live_velocity > 0 else current_velocity
                self._refresh_opportunity_score(trend, confidence=trend.get("confidence"), window_hours_remaining=new_window)

                # Peaked→emerging recovery: if velocity climbed back above baseline
                # AND new reels appeared recently, treat as renewed momentum.
                # UNCALIBRATED — thresholds are educated guesses, not data-derived.
                # Re-tune after real peaked→emerging trajectory data exists.
                if current_status == "peaked" and velocity_for_check > 0 and rising_baseline > 0:
                    if velocity_for_check >= rising_baseline and new_reels_count > 0:
                        self._update_status(trend_id, "rising", {
                            "window_hours_remaining": new_window,
                            "velocity_avg": velocity_for_check,
                            "reel_count": total_reels_count,
                            "high_confidence": bool(trend.get("high_confidence", False)),
                            "promotion_reason": "recovery",
                        })
                        logger.info(f"[RECOVERED] '{audio_title}' peaked→rising (velocity={velocity_for_check:.2f}, baseline={rising_baseline:.2f}, new_reels={new_reels_count})")
                        local_summary["recovered"] = local_summary.get("recovered", 0) + 1
                        return local_summary

                # Expired→rising recovery: same logic as peaked, but with an age cap.
                # Expired trends can be arbitrarily old (weeks/months), so we only allow
                # recovery if first_detected_at is within the last 30 days.
                # Uses first_detected_at because no status_changed_at field exists.
                EXPIRED_RECOVERY_MAX_AGE_DAYS = 30
                if current_status == "expired" and velocity_for_check > 0 and rising_baseline > 0:
                    age_days = age_hours / 24.0
                    if age_days <= EXPIRED_RECOVERY_MAX_AGE_DAYS and velocity_for_check >= rising_baseline and new_reels_count > 0:
                        self._update_status(trend_id, "rising", {
                            "window_hours_remaining": new_window,
                            "velocity_avg": velocity_for_check,
                            "reel_count": total_reels_count,
                            "high_confidence": bool(trend.get("high_confidence", False)),
                            "promotion_reason": "recovery",
                        })
                        logger.info(f"[RECOVERED] '{audio_title}' expired→rising (velocity={velocity_for_check:.2f}, baseline={rising_baseline:.2f}, new_reels={new_reels_count}, age={age_days:.1f}d)")
                        local_summary["recovered"] = local_summary.get("recovered", 0) + 1
                        return local_summary

                if velocity_for_check < peak_velocity * 0.60 and peak_velocity > 0:
                    self._update_status(trend_id, "peaked", {
                        "window_hours_remaining": new_window,
                        "velocity_avg": velocity_for_check,
                        "reel_count": total_reels_count,
                        "high_confidence": bool(trend.get("high_confidence", False)),
                        "promotion_reason": trend.get("promotion_reason"),
                    })
                    logger.info(f"[PEAKED] '{audio_title}' (was {peak_velocity:.2f}, now {velocity_for_check:.2f})")
                    local_summary["peaked"] += 1
                    return local_summary

                if current_status == "emerging":
                    creator_count = self._count_unique_creators(
                        trend.get("audio_title"), trend.get("audio_artist"), now
                    )
                    high_confidence = creator_count >= 5

                    # UNCALIBRATED — thresholds are educated guesses, not data-derived.
                    # Re-tune after first real beta trajectory data exists.
                    qualifies_by_creator = creator_count >= 2
                    qualifies_by_volume = total_reels_count >= 3
                    velocity_ok_simple = (
                        rising_baseline > 0
                        and velocity_for_check > rising_baseline * 1.2
                    )

                    persisted_enough = age_hours >= 6
                    volume_enough = age_hours >= 8
                    should_rise = False
                    promotion_reason = trend.get("promotion_reason")

                    if persisted_enough and qualifies_by_creator:
                        should_rise = True
                        promotion_reason = "creator_adoption"
                    elif volume_enough and qualifies_by_volume:
                        should_rise = True
                        promotion_reason = "volume_signal"
                    elif volume_enough and velocity_ok_simple:
                        should_rise = True
                        promotion_reason = "velocity_outlier"

                    if should_rise:
                        self._update_status(trend_id, "rising", {
                            "window_hours_remaining": new_window,
                            "velocity_avg": velocity_for_check,
                            "peak_velocity": max(velocity_for_check, peak_velocity),
                            "reel_count": total_reels_count,
                            "high_confidence": high_confidence,
                            "promotion_reason": promotion_reason,
                        })
                        logger.info(
                            f"[RISEN] '{audio_title}' ({creator_count} creators, "
                            f"velocity={velocity_for_check:.2f}, baseline={rising_baseline:.2f}, "
                            f"reason={promotion_reason})"
                        )
                        local_summary["risen"] += 1
                    else:
                        self._update_status(trend_id, "emerging", {
                            "window_hours_remaining": new_window,
                            "velocity_avg": velocity_for_check,
                            "reel_count": total_reels_count,
                            "high_confidence": high_confidence,
                            "promotion_reason": trend.get("promotion_reason"),
                        })
                        local_summary["emerged"] += 1
                else:
                    creator_count = self._count_unique_creators(
                        trend.get("audio_title"), trend.get("audio_artist"), now
                    )
                    velocity_snapshot_ok, _ = self._velocity_promotion_allowed(
                        trend_id=trend_id,
                        current_velocity=velocity_for_check,
                        baseline=rising_baseline,
                    )
                    promotion_reason = "both" if (creator_count >= 3 and velocity_snapshot_ok) else (
                        "creator_adoption" if creator_count >= 3 else "velocity_outlier"
                    )
                    self._update_status(trend_id, "rising", {
                        "window_hours_remaining": new_window,
                        "velocity_avg": velocity_for_check,
                        "peak_velocity": max(velocity_for_check, peak_velocity),
                        "reel_count": total_reels_count,
                        "high_confidence": creator_count >= 5,
                        "promotion_reason": promotion_reason,
                    })
                    
            except Exception as e:
                logger.error(f"Error refreshing trend_id={trend.get('id')}: {e}", exc_info=True)
                local_summary["errors"] += 1
                
            return local_summary

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            for local_summary in executor.map(process_trend, trends):
                with summary_lock:
                    for k, v in local_summary.items():
                        summary[k] += v

        logger.info(f"=== TrendRefresher done: {summary} ===")
        return summary

    def _update_status(self, trend_id: int, status: str, extra: dict = None):
        payload = {"status": status}
        if extra:
            payload.update(extra)
        self.supabase.table("trends").update(payload).eq("id", trend_id).execute()

    def _refresh_opportunity_score(self, trend: dict, *, confidence: float | None = None, window_hours_remaining: float | None = None) -> float:
        score = calculate_opportunity_score(
            india_saturation_pct=trend.get("india_saturation_pct") or 0.0,
            window_hours_remaining=window_hours_remaining if window_hours_remaining is not None else trend.get("window_hours_remaining") or 0.0,
            confidence=confidence if confidence is not None else trend.get("confidence") or 0.0,
        )
        try:
            self.supabase.table("trends").update({"opportunity_score": score}).eq("id", trend["id"]).execute()
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
            snapshots_res = self.supabase.table('trend_snapshots') \
                .select('velocity_avg, captured_at') \
                .eq('trend_id', trend_id) \
                .order('captured_at', desc=True) \
                .limit(10) \
                .execute()
            
            snapshots = snapshots_res.data or []
            peaking_score = calculate_realistic_peaking_score(trend, snapshots)
            
            # Update the peaking score in database
            self.supabase.table("trends").update({"peaking_score": peaking_score}).eq("id", trend_id).execute()
            
            return peaking_score
        except Exception as e:
            logger.warning(f"Could not refresh peaking_score for trend_id={trend.get('id')}: {e}")
            return 0.0

    def _refresh_audio_page_count(self, trend_id: int, audio_id: str) -> bool:
        """
        Fetches the official reel count from the Instagram Audio page for this audio_id.
        Uses a lightweight requests-based fetch (no browser needed for meta tags).
        Updates trends.audio_use_count if the scraped value is higher than stored.
        Returns True if an update was written.
        """
        import re as _re
        import requests as _requests
        import time
        import random
        try:
            # Random sleep to avoid simultaneous connection rate limits
            time.sleep(random.uniform(1.0, 3.0))
            
            url = f"https://www.instagram.com/reels/audio/{audio_id}/"
            headers = {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
                "Accept-Language": "en-US,en;q=0.9",
            }
            resp = _requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                logger.warning(f"Audio page fetch failed for {audio_id}: HTTP {resp.status_code}")
                return False

            text = resp.text
            # Extract count from text like "1.2M reels" / "45.2K reels" / "520 reels"
            match = _re.search(r'([\d,.]+)([KkMmBb]?)\s*(?:reels|Reels)', text)
            if not match:
                if 'Please wait a few minutes before you try again' in text or 'login' in text.lower():
                    logger.warning(f"Audio page fetch throttled/login-walled for {audio_id}")
                    return "THROTTLED"
                logger.debug(f"No reel count found on audio page for {audio_id}")
                return False

            raw, suffix = match.group(1).replace(',', ''), match.group(2).upper()
            multiplier = {'K': 1_000, 'M': 1_000_000, 'B': 1_000_000_000}.get(suffix, 1)
            live_count = int(float(raw) * multiplier)

            # Read current value before updating
            res = self.supabase.table("trends").select("audio_use_count").eq("id", trend_id).limit(1).execute()
            stored = (res.data or [{}])[0].get("audio_use_count") or 0

            if live_count > stored:
                self.supabase.table("trends").update({"audio_use_count": live_count}).eq("id", trend_id).execute()
                logger.info(f"[AUDIO_PAGE] trend_id={trend_id} audio_id={audio_id}: {stored} -> {live_count}")
                return True
            return False
        except Exception as e:
            logger.warning(f"_refresh_audio_page_count failed for trend_id={trend_id}: {e}")
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
                res = self.supabase.table("reels") \
                    .select("audio_use_count") \
                    .eq("audio_id", audio_id) \
                    .execute()
            elif audio_title and audio_artist:
                normalized_title = normalize_audio_title(audio_title)
                res = self.supabase.table("reels") \
                    .select("audio_use_count, audio_title") \
                    .eq("audio_artist", audio_artist) \
                    .execute()
                matching = [
                    r for r in (res.data or [])
                    if normalize_audio_title(r.get("audio_title", "") or "") == normalized_title
                ]
            else:
                return False

            counts = [
                r["audio_use_count"]
                for r in (matching if audio_title and audio_artist and not audio_id else (res.data or []))
                if r.get("audio_use_count") and r["audio_use_count"] > 0
            ]
            if not counts:
                return False

            live_max = max(counts)
            if live_max > stored_count:
                self.supabase.table("trends") \
                    .update({"audio_use_count": live_max}) \
                    .eq("id", trend_id) \
                    .execute()
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
            res = self.supabase.table("reels") \
                .select("velocity_score, audio_title") \
                .eq("audio_artist", audio_artist) \
                .gte("created_at", threshold) \
                .execute()
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
            res = self.supabase.table("reels") \
                .select("owner_username, audio_title") \
                .eq("audio_artist", audio_artist) \
                .gte("created_at", threshold) \
                .execute()
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
            res = self.supabase.table("trends") \
                .select("velocity_avg") \
                .eq("is_seed_data", False) \
                .gte("first_detected_at", (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()) \
                .execute()
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
        """
        try:
            query = self.supabase.table("trends").select("id,audio_title,audio_artist,velocity_avg").eq("is_seed_data", False)
            if trend_ids:
                query = query.in_("id", list(trend_ids))
            trends = query.execute().data or []
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
                rows = list(executor.map(process_snapshot, trends))
                
            return rows
        except Exception as e:
            logger.warning(f"Could not build trend snapshot rows: {e}")
            return []


if __name__ == "__main__":
    refresher = TrendRefresher()
    result = refresher.refresh_all()
    print(f"Refresh complete: {result}")
