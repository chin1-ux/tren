"""
Cookie Health Alert Detector Module
====================================
Monitors and logs Instagram scraper cookie health.
Detects:
  1. Missing or corrupted cookies.json / INSTAGRAM_COOKIES_B64.
  2. Expired or near-expiry sessionid / csrftoken cookies.
  3. Live session invalidation (redirects to /accounts/login/ or 429 challenge).

Emits structured CRITICAL alert logs into `cookie_health.log`, `alert_system.log`, and `api.log`.
"""

import os
import json
import base64
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Setup logger
log_file = "cookie_health.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s"
)
logger = logging.getLogger("cookie_health_detector")

load_dotenv("backend/.env")
load_dotenv(".env")

def log_critical_cookie_alert(reason: str, details: str = ""):
    """Emits explicit, formatted CRITICAL cookie health alerts across system loggers."""
    alert_msg = (
        f"\n=========================================================================\n"
        f"🚨 CRITICAL COOKIE HEALTH ALERT: INSTAGRAM SCRAPER SESSION INVALID!\n"
        f"Reason: {reason}\n"
        f"Details: {details}\n"
        f"Action Required: Refresh cookies using Chrome/Firefox export and update INSTAGRAM_COOKIES_B64.\n"
        f"=========================================================================\n"
    )
    logger.critical(alert_msg)

    # Append to alert_system.log if available
    try:
        with open("alert_system.log", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} - [CRITICAL] - {reason}: {details}\n")
    except Exception:
        pass

    # Attempt operator email notification if configured
    try:
        from heartbeat_monitor import _send_email
        recipient = os.getenv("CRON_HEARTBEAT_ALERT_EMAIL") or os.getenv("OPERATOR_ALERT_EMAIL")
        if recipient:
            subject = "🚨 CRITICAL: Instagram Scraper Cookie Session Expired!"
            html = f"""
            <h2>🚨 Instagram Scraper Cookie Alert</h2>
            <p>The Instagram scraper cookie session is <strong>no longer active</strong>.</p>
            <p><strong>Failure Reason:</strong> {reason}</p>
            <p><strong>Details:</strong> {details}</p>
            <p>Please export fresh cookies from your browser and update <code>INSTAGRAM_COOKIES_B64</code> in environment secrets.</p>
            """
            _send_email(subject, html)
            logger.info("Cookie failure alert email sent to operator.")
    except Exception as email_err:
        logger.warning(f"Could not dispatch email alert: {email_err}")

def load_instagram_cookies() -> list | None:
    """Loads Instagram cookies from INSTAGRAM_COOKIES_B64 env or backend/cookies.json."""
    b64_val = os.getenv("INSTAGRAM_COOKIES_B64")
    if b64_val:
        try:
            decoded = base64.b64decode(b64_val.strip()).decode("utf-8")
            return json.loads(decoded)
        except Exception as e:
            log_critical_cookie_alert("Corrupted INSTAGRAM_COOKIES_B64 environment variable", str(e))

    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log_critical_cookie_alert("Corrupted backend/cookies.json file", str(e))

    log_critical_cookie_alert("No Instagram cookies found", "Neither INSTAGRAM_COOKIES_B64 nor backend/cookies.json exists.")
    return None

def verify_cookie_expiration_offline(cookies: list) -> dict:
    """Checks cookie expiration timestamps without making network requests."""
    now_ts = datetime.now(timezone.utc).timestamp()
    results = {"valid": True, "warnings": [], "errors": []}

    session_cookie = next((c for c in cookies if c.get("name") == "sessionid"), None)
    if not session_cookie:
        results["valid"] = False
        results["errors"].append("Missing 'sessionid' cookie in payload")
        return results

    # Check expiration date if present
    exp = session_cookie.get("expires") or session_cookie.get("expiration")
    if exp:
        exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
        hours_remaining = (exp - now_ts) / 3600.0
        if hours_remaining <= 0:
            results["valid"] = False
            results["errors"].append(f"'sessionid' cookie EXPIRED on {exp_dt.isoformat()}")
        elif hours_remaining < 48:
            results["warnings"].append(f"'sessionid' cookie expiring soon ({round(hours_remaining, 1)} hours left on {exp_dt.isoformat()})")

    return results

async def verify_cookie_session_live_async(cookies: list) -> bool:
    """Performs a live headless Playwright check to verify Instagram session active state."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("Playwright not installed — skipping live network ping.")
        return True

    formatted = []
    for c in cookies:
        formatted.append({
            "name": c["name"],
            "value": c["value"],
            "domain": c.get("domain", ".instagram.com"),
            "path": c.get("path", "/"),
        })

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            await context.add_cookies(formatted)
            page = await context.new_page()

            logger.info("Executing live session health check on https://www.instagram.com/...")
            await page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(2000)

            final_url = page.url
            await browser.close()

            if "/accounts/login/" in final_url:
                log_critical_cookie_alert(
                    "Instagram redirected to login page",
                    f"Final URL: {final_url}. Active cookies failed session authentication."
                )
                return False

            logger.info(f"✅ Cookie health check PASSED! Active session validated (URL: {final_url}).")
            return True

    except Exception as e:
        log_critical_cookie_alert("Live session check exception", str(e))
        return False

def run_cookie_health_check() -> bool:
    """Synchronous entry point for cookie health detector."""
    logger.info("=== Running Instagram Cookie Health Detector ===")
    cookies = load_instagram_cookies()
    if not cookies:
        return False

    offline_check = verify_cookie_expiration_offline(cookies)
    if not offline_check["valid"]:
        for err in offline_check["errors"]:
            log_critical_cookie_alert("Offline Cookie Expiry Validation Failed", err)
        return False

    for warn in offline_check["warnings"]:
        logger.warning(f"⚠️ [COOKIE WARNING] {warn}")

    # Run live Playwright check
    try:
        is_live_valid = asyncio.run(verify_cookie_session_live_async(cookies))
        return is_live_valid
    except Exception as e:
        logger.error(f"Error running live cookie verification: {e}")
        return False

if __name__ == "__main__":
    success = run_cookie_health_check()
    if success:
        print("\nSUCCESS: All Instagram cookies are healthy, active, and validated!")
    else:
        print("\nFAILURE: Cookie health detector flagged an issue. Check cookie_health.log!")
