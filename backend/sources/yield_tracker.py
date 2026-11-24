"""
Daily Yield Tracker & Ingestion Health Observability (Order 95 Phase 3.2)
Tracks reels ingested per source per day and alerts when today's yield is < 50% of 7-day median.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger("yield_tracker")

_LAST_YIELD_ALERT_TS: dict = {}

def track_and_check_daily_yield(supabase_client, current_run_source_counts: dict[str, int]) -> dict[str, Any]:
    """
    Computes today's ingested yield per source, checks against 7-day median,
    and triggers an alert if yield dropped below 50% of the 7-day median.
    """
    if not supabase_client:
        return {"status": "skipped", "reason": "no_db"}

    now = datetime.now(timezone.utc)
    today_date = now.date().isoformat()
    seven_days_ago = (now - timedelta(days=7)).isoformat()

    results = {}

    for source, count in current_run_source_counts.items():
        try:
            # Query count of reels for this source in last 7 days
            res = supabase_client.table("reels") \
                .select("id, scraped_at") \
                .gte("scraped_at", seven_days_ago) \
                .execute()

            reels_data = res.data or []
            # Group by day
            daily_counts = {}
            for r in reels_data:
                s_at = r.get("scraped_at", "")[:10]
                if s_at:
                    daily_counts[s_at] = daily_counts.get(s_at, 0) + 1

            history_counts = list(daily_counts.values())
            if len(history_counts) >= 3:
                history_counts.sort()
                mid = len(history_counts) // 2
                median_yield = history_counts[mid]
            else:
                median_yield = 100  # Default baseline if history not populated

            today_yield = daily_counts.get(today_date, count)
            threshold = median_yield * 0.5

            is_depleted = (today_yield < threshold)
            results[source] = {
                "today_yield": today_yield,
                "median_yield": median_yield,
                "threshold": threshold,
                "is_depleted": is_depleted
            }

            if is_depleted and median_yield > 20:
                _dispatch_yield_alert(source, today_yield, median_yield)

        except Exception as e:
            logger.debug(f"[YIELD_TRACKER] Error tracking yield for {source}: {e}")

    return results

def _dispatch_yield_alert(source: str, today: int, median: float):
    now_ts = datetime.now(timezone.utc).timestamp()
    last_alert = _LAST_YIELD_ALERT_TS.get(source, 0)
    if now_ts - last_alert < (12 * 3600):
        logger.info(f"[YIELD_ALERT] Throttled for {source} (alerted in last 12h).")
        return

    _LAST_YIELD_ALERT_TS[source] = now_ts
    logger.warning(
        f"[ALERT:YIELD_DROP] Source '{source}' today yield ({today}) is < 50% of 7-day median ({median:.0f})!"
    )
