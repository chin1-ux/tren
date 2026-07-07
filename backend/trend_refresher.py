import os
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

try:
    logging.basicConfig(
        filename="trend_refresher.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
except Exception:
    pass
logger = logging.getLogger(__name__)


class TrendRefresher:
    """
    Periodically refreshes the lifecycle status of all active trends in Supabase.
    
    Lifecycle:
      emerging  → velocity spike detected, <6h old, <5 creators adopted
      rising    → 5+ creators, high velocity, actively trending
      peaked    → velocity dropped >40% from its peak
      expired   → older than 72 hours OR velocity near zero
    
    Also decrements `window_hours_remaining` for all active trends.
    """

    def __init__(self):
        load_dotenv()
        if not os.getenv("SUPABASE_URL"):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            load_dotenv(os.path.join(script_dir, ".env"))

        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
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
        summary = {"emerged": 0, "risen": 0, "peaked": 0, "expired": 0, "errors": 0}

        try:
            # Fetch all trends that are not yet expired
            res = self.supabase.table("trends") \
                .select("*") \
                .in_("status", ["emerging", "rising"]) \
                .execute()
            trends = res.data or []
            logger.info(f"Found {len(trends)} active trends to refresh")
        except Exception as e:
            logger.error(f"Failed to fetch active trends: {e}", exc_info=True)
            return summary

        for trend in trends:
            try:
                trend_id = trend["id"]
                audio_title = trend.get("audio_title", "?")
                created_at_str = trend.get("created_at")
                current_status = trend.get("status", "rising")
                current_velocity = trend.get("velocity_avg", 0.0)
                peak_velocity = trend.get("peak_velocity") or current_velocity
                window_hours = trend.get("window_hours_remaining", 24)

                # Parse created_at
                if created_at_str:
                    if created_at_str.endswith("Z"):
                        created_at_str = created_at_str[:-1] + "+00:00"
                    created_at = datetime.fromisoformat(created_at_str)
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                else:
                    created_at = now - timedelta(hours=12)

                age_hours = (now - created_at).total_seconds() / 3600

                # ── EXPIRY: older than 72h OR window exhausted ──────────────────
                if age_hours >= 72 or window_hours <= 0:
                    self._update_status(trend_id, "expired", {"window_hours_remaining": 0})
                    logger.info(f"[EXPIRED] '{audio_title}' (age={age_hours:.1f}h)")
                    summary["expired"] += 1
                    continue

                # ── Recalculate current live velocity from reels table ──────────
                live_velocity = self._calc_live_velocity(
                    trend.get("audio_title"), trend.get("audio_artist"), now
                )

                # Decrement window_hours_remaining
                new_window = max(0, window_hours - 3)  # called every 3h

                # ── PEAKED: velocity dropped >40% from peak ─────────────────────
                velocity_for_check = live_velocity if live_velocity > 0 else current_velocity
                if velocity_for_check < peak_velocity * 0.60 and peak_velocity > 0:
                    self._update_status(trend_id, "peaked", {
                        "window_hours_remaining": new_window,
                        "velocity_avg": velocity_for_check
                    })
                    logger.info(f"[PEAKED] '{audio_title}' (was {peak_velocity:.2f}, now {velocity_for_check:.2f})")
                    summary["peaked"] += 1
                    continue

                # ── RISING: if emerging and now has 5+ creators ─────────────────
                if current_status == "emerging":
                    creator_count = self._count_unique_creators(
                        trend.get("audio_title"), trend.get("audio_artist"), now
                    )
                    if creator_count >= 5:
                        self._update_status(trend_id, "rising", {
                            "window_hours_remaining": new_window,
                            "velocity_avg": live_velocity or current_velocity,
                            "peak_velocity": max(live_velocity or 0, peak_velocity)
                        })
                        logger.info(f"[RISEN] '{audio_title}' ({creator_count} creators)")
                        summary["risen"] += 1
                    else:
                        # Still emerging — just update window
                        self._update_status(trend_id, "emerging", {
                            "window_hours_remaining": new_window,
                            "velocity_avg": live_velocity or current_velocity
                        })
                        summary["emerged"] += 1
                else:
                    # Still rising — update velocity and window
                    new_peak = max(live_velocity or 0, peak_velocity)
                    self._update_status(trend_id, "rising", {
                        "window_hours_remaining": new_window,
                        "velocity_avg": live_velocity or current_velocity,
                        "peak_velocity": new_peak
                    })

            except Exception as e:
                logger.error(f"Error refreshing trend_id={trend.get('id')}: {e}", exc_info=True)
                summary["errors"] += 1

        logger.info(f"=== TrendRefresher done: {summary} ===")
        return summary

    def _update_status(self, trend_id: int, status: str, extra: dict = None):
        payload = {"status": status}
        if extra:
            payload.update(extra)
        self.supabase.table("trends").update(payload).eq("id", trend_id).execute()

    def _calc_live_velocity(self, audio_title: str, audio_artist: str, now: datetime) -> float:
        """Recalculates avg velocity_score of reels matching this audio in last 24h."""
        try:
            threshold = (now - timedelta(hours=24)).isoformat()
            res = self.supabase.table("reels") \
                .select("velocity_score") \
                .eq("audio_title", audio_title) \
                .eq("audio_artist", audio_artist) \
                .gte("created_at", threshold) \
                .execute()
            scores = [r.get("velocity_score", 0.0) for r in (res.data or [])]
            return sum(scores) / len(scores) if scores else 0.0
        except Exception as e:
            logger.warning(f"Could not calc live velocity for '{audio_title}': {e}")
            return 0.0

    def _count_unique_creators(self, audio_title: str, audio_artist: str, now: datetime) -> int:
        """Counts distinct creator usernames using this audio in last 48h."""
        try:
            threshold = (now - timedelta(hours=48)).isoformat()
            res = self.supabase.table("reels") \
                .select("owner_username") \
                .eq("audio_title", audio_title) \
                .eq("audio_artist", audio_artist) \
                .gte("created_at", threshold) \
                .execute()
            usernames = {r.get("owner_username") for r in (res.data or []) if r.get("owner_username")}
            return len(usernames)
        except Exception as e:
            logger.warning(f"Could not count creators for '{audio_title}': {e}")
            return 0


if __name__ == "__main__":
    refresher = TrendRefresher()
    result = refresher.refresh_all()
    print(f"Refresh complete: {result}")
