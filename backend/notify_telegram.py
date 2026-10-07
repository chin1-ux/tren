import os
import sys
import logging
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("notify_telegram")

def send_telegram_message(text: str, parse_mode: str = "HTML") -> bool:
    load_dotenv("backend/.env")
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.warning("Telegram notification skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info("Telegram notification sent successfully.")
            return True
        else:
            logger.warning(f"Telegram API returned status {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to deliver Telegram notification: {e}")
        return False

def notify_watchdog_dispatch(last_started_at: str = None, gha_url: str = None) -> bool:
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    last_str = last_started_at or "No runs recorded in >195 mins"
    url_str = f"\n• <b>Action Run</b>: <a href='{gha_url}'>View Workflow</a>" if gha_url else ""

    text = (
        "⚠️ <b>[TRENDROP WATCHDOG] Missed Scraper Run Recovered</b>\n\n"
        f"• <b>Timestamp</b>: {now_utc}\n"
        f"• <b>Reason</b>: Scheduled cron missed slot. Last active run: {last_str}\n"
        "• <b>Action</b>: Automated workflow_dispatch initiated on <code>chin1-ux/tren</code>."
        f"{url_str}"
    )
    return send_telegram_message(text)

def notify_login_wall(targets: list[str] = None, run_id: str = None) -> bool:
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    targets_str = ", ".join(targets) if targets else "Hashtag/Keyword Feed"
    run_str = f"Run #{run_id}" if run_id else "GitHub Actions Runner"

    text = (
        "🚨 <b>[TRENDROP ALERT] Instagram Login Wall Detected</b> 🚨\n\n"
        f"• <b>Time</b>: {now_utc}\n"
        f"• <b>Context</b>: {run_str}\n"
        f"• <b>Affected Targets</b>: <code>{targets_str}</code>\n"
        "• <b>Impact</b>: Instagram session expired / redirected to /accounts/login/.\n"
        "• <b>Action Required</b>: Export fresh Chrome cookies and update <code>INSTAGRAM_COOKIES_B64</code> in GitHub Secrets."
    )
    return send_telegram_message(text)

def notify_run_failure(stage: str = None, error_msg: str = None, run_id: str = None) -> bool:
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    stage_str = stage or "Pipeline Execution"
    err_str = (error_msg or "Unknown error")[:300]
    run_str = f"Run #{run_id}" if run_id else "Scraper Runner"

    text = (
        "❌ <b>[TRENDROP ALERT] Scraper Pipeline Run Failure</b>\n\n"
        f"• <b>Time</b>: {now_utc}\n"
        f"• <b>Context</b>: {run_str}\n"
        f"• <b>Stage</b>: <code>{stage_str}</code>\n"
        f"• <b>Error</b>: <code>{err_str}</code>\n"
        "• <b>Action</b>: Inspect GitHub Actions run logs."
    )
    return send_telegram_message(text)

if __name__ == "__main__":
    if "--test" in sys.argv:
        print("Sending test Telegram alert...")
        res = send_telegram_message("🔔 <b>Trendrop Telegram Alert System Test</b>\nSystem is configured and operational.")
        print(f"Result: {'SUCCESS' if res else 'FAILED / MISSING CREDENTIALS'}")
    else:
        print("Usage: python backend/notify_telegram.py --test")
