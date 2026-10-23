"""
backend/cadence_governor.py
---------------------------
Cadence Governor & Clean 402 Quota Handler.
- Calculates dynamic guard min-gap minutes based on measured MB/run:
    >= 15 MB/run -> 360 minutes (6 hours)
    8 - 15 MB/run -> 240 minutes (4 hours)
    < 8 MB/run -> 165 minutes (2h 45m)
- Handles Supabase HTTP 402 / over-quota responses:
    Stops pipeline cleanly without retry loop, records cron_runs row,
    sends Telegram alert if secrets exist.
"""

import os
import sys
import logging
import urllib.request
import json
from datetime import datetime, timezone
from typing import Optional, Tuple, Any

logger = logging.getLogger("cadence_governor")

def calculate_cadence_gap(measured_mb_per_run: float) -> int:
    """
    Computes required gap threshold in minutes from measured MB per run.
    """
    if measured_mb_per_run >= 15.0:
        gap = 360
    elif measured_mb_per_run >= 8.0:
        gap = 240
    else:
        gap = 165
    logger.info(f"Cadence Governor: measured {measured_mb_per_run:.2f} MB/run -> setting SCRAPER_GUARD_MIN_GAP_MINUTES={gap}m")
    return gap


def send_telegram_alert_if_configured(message: str) -> bool:
    """Sends Telegram message if bot token and chat id exist in environment."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        logger.debug("Telegram credentials not configured; skipping alert.")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception as e:
        logger.warning(f"Failed to send Telegram alert: {e}")
        return False


def handle_supabase_402_over_quota(error: Exception, sb_client: Optional[Any] = None) -> bool:
    """
    Detects if exception represents HTTP 402 or Supabase quota exceeded.
    If so, records cron_runs row cleanly, alerts Telegram, and signals clean stop.
    Returns True if handled as 402 over-quota, False otherwise.
    """
    err_str = str(error).lower()
    is_402 = "402" in err_str or "payment required" in err_str or "quota exceeded" in err_str or "exceeded plan limits" in err_str
    
    if not is_402:
        return False

    logger.error("CRITICAL: Supabase HTTP 402 / Over-Quota detected. Halting pipeline cleanly.")
    now_iso = datetime.now(timezone.utc).isoformat()
    github_run_id = os.getenv("GITHUB_RUN_ID")

    # Write clean cron_runs row
    if sb_client:
        try:
            payload = {
                "created_at": now_iso,
                "run_at": now_iso,
                "status": "failure",
                "conclusion": "quota_exceeded",
                "cutoff_reason": "Supabase 402 Payment Required - Quota Exceeded (Clean Stop)",
                "github_run_id": str(github_run_id) if github_run_id else None
            }
            sb_client.table("cron_runs").insert(payload, returning="minimal").execute()
            logger.info("Successfully recorded quota_exceeded row in cron_runs.")
        except Exception as e:
            logger.warning(f"Could not record 402 in cron_runs via client: {e}")

    # Alert Telegram if configured
    alert_text = (
        f"🚨 *Trendrop Scraper Quota Alert*\n\n"
        f"Pipeline stopped cleanly due to Supabase HTTP 402 (Over Quota / Payment Required).\n"
        f"Run ID: `{github_run_id or 'manual'}`\n"
        f"Timestamp: `{now_iso}`"
    )
    send_telegram_alert_if_configured(alert_text)
    return True
