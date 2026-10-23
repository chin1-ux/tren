"""
Instagram Session Sliding & Health Manager
==========================================
Manages dynamic, self-renewing Instagram session cookies via Supabase:
1. Loads active cookies from Supabase `scraper_sessions` (or seeds from INSTAGRAM_COOKIES_B64 / cookies.json).
2. Captures refreshed/rotated cookies from live Camoufox browser context after scraping.
3. Persists slid cookies back to Supabase to continuously roll the session forward without manual intervention.
4. Performs pre-flight health & expiry checks.
"""

import os
import json
import base64
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv("backend/.env")
load_dotenv(".env")

logger = logging.getLogger("session_sliding_manager")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")

_SESSION_ID_KEY = "instagram_primary"


def _get_supabase_client() -> Optional[Client]:
    """Returns an authenticated Supabase client using service role key."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        logger.warning("[SESSION_MANAGER] SUPABASE_URL or key missing.")
        return None
    try:
        return create_client(url, key)
    except Exception as e:
        logger.error(f"[SESSION_MANAGER] Failed to create Supabase client: {e}")
        return None


def _parse_cookie_expiry(cookies: List[Dict[str, Any]]) -> Tuple[Optional[float], Optional[str]]:
    """Finds the sessionid cookie and returns (timestamp, isoformat)."""
    for c in cookies:
        if c.get("name") == "sessionid":
            exp = c.get("expires") or c.get("expiration")
            if exp:
                try:
                    exp_ts = float(exp)
                    exp_iso = datetime.fromtimestamp(exp_ts, tz=timezone.utc).isoformat()
                    return exp_ts, exp_iso
                except Exception:
                    pass
    return None, None


def load_active_session_cookies() -> Optional[List[Dict[str, Any]]]:
    """
    Retrieves active Instagram cookies:
    1. Checks Supabase `scraper_sessions` table first.
    2. Falls back to INSTAGRAM_COOKIES_B64 or backend/cookies.json.
    3. Auto-seeds Supabase if loaded from fallback.
    """
    sb = _get_supabase_client()
    now_ts = datetime.now(timezone.utc).timestamp()

    # 1. Try Supabase
    if sb:
        try:
            res = sb.table("scraper_sessions").select("*").eq("id", _SESSION_ID_KEY).execute()
            if res.data and len(res.data) > 0:
                row = res.data[0]
                cookies = row.get("cookies")
                status = row.get("session_status", "active")
                if isinstance(cookies, list) and len(cookies) > 0 and status != "expired":
                    exp_ts, _ = _parse_cookie_expiry(cookies)
                    # If cookie has not already passed hard expiry
                    if not exp_ts or (exp_ts - now_ts) > 0:
                        logger.info(f"[SESSION_MANAGER] Loaded active session from Supabase (last slid: {row.get('last_slid_at')}).")
                        return cookies
                    else:
                        logger.warning(f"[SESSION_MANAGER] Supabase session expired at {row.get('expires_at')}.")
        except Exception as e:
            logger.warning(f"[SESSION_MANAGER] Could not read from Supabase: {e}")

    # 2. Fallback: INSTAGRAM_COOKIES_B64
    b64_val = os.getenv("INSTAGRAM_COOKIES_B64")
    if b64_val:
        try:
            decoded = base64.b64decode(b64_val.strip()).decode("utf-8")
            cookies = json.loads(decoded)
            logger.info("[SESSION_MANAGER] Loaded session from INSTAGRAM_COOKIES_B64 env variable.")
            # Auto-seed to Supabase
            if sb:
                save_slid_cookies(cookies, reels_scraped=0, run_id="seed_from_env")
            return cookies
        except Exception as e:
            logger.error(f"[SESSION_MANAGER] Failed to decode INSTAGRAM_COOKIES_B64: {e}")

    # 3. Fallback: backend/cookies.json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "cookies.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            logger.info("[SESSION_MANAGER] Loaded session from backend/cookies.json.")
            if sb:
                save_slid_cookies(cookies, reels_scraped=0, run_id="seed_from_json")
            return cookies
        except Exception as e:
            logger.error(f"[SESSION_MANAGER] Failed to read backend/cookies.json: {e}")

    logger.critical("[SESSION_MANAGER] No valid Instagram cookies found in Supabase, env, or disk!")
    return None


def save_slid_cookies(
    new_cookies: List[Dict[str, Any]],
    reels_scraped: int = 0,
    run_id: str = "manual"
) -> bool:
    """
    Persists refreshed browser cookies back to Supabase `scraper_sessions`.
    Only saves if a valid `sessionid` cookie is present.
    """
    if not new_cookies or not isinstance(new_cookies, list):
        logger.warning("[SESSION_MANAGER] save_slid_cookies received empty cookie list.")
        return False

    exp_ts, exp_iso = _parse_cookie_expiry(new_cookies)
    session_cookie = next((c for c in new_cookies if c.get("name") == "sessionid"), None)
    if not session_cookie or not session_cookie.get("value"):
        logger.warning("[SESSION_MANAGER] Cannot slide cookies: missing 'sessionid'.")
        return False

    # Extract username / ds_user_id if present
    ds_user_id = next((c.get("value") for c in new_cookies if c.get("name") == "ds_user_id"), None)

    sb = _get_supabase_client()
    if not sb:
        logger.warning("[SESSION_MANAGER] Supabase unavailable — skipping slide persistence.")
        return False

    now_iso = datetime.now(timezone.utc).isoformat()
    payload = {
        "id": _SESSION_ID_KEY,
        "cookies": new_cookies,
        "session_status": "active",
        "account_username": ds_user_id,
        "last_slid_at": now_iso,
        "last_verified_at": now_iso if reels_scraped > 0 else now_iso,
        "expires_at": exp_iso,
        "metadata": {
            "last_run_id": str(run_id),
            "reels_scraped": reels_scraped,
            "cookie_count": len(new_cookies),
            "updated_at": now_iso,
        }
    }

    try:
        sb.table("scraper_sessions").upsert(payload).execute()
        hours_msg = f" (expires: {exp_iso})" if exp_iso else ""
        logger.info(f"✅ [SESSION_MANAGER] Cookie sliding successful! Saved {len(new_cookies)} cookies to Supabase{hours_msg}.")
        return True
    except Exception as e:
        logger.error(f"[SESSION_MANAGER] Failed to upsert slid cookies to Supabase: {e}")
        return False


def mark_session_status(status: str, reason: str = "") -> bool:
    """Updates the status of the session in Supabase (e.g., 'expired', 'warning', 'checkpoint')."""
    sb = _get_supabase_client()
    if not sb:
        return False
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        sb.table("scraper_sessions").update({
            "session_status": status,
            "metadata": {
                "status_reason": reason,
                "status_changed_at": now_iso
            }
        }).eq("id", _SESSION_ID_KEY).execute()
        logger.info(f"[SESSION_MANAGER] Marked session '{_SESSION_ID_KEY}' as {status}: {reason}")
        return True
    except Exception as e:
        logger.error(f"[SESSION_MANAGER] Failed to update session status: {e}")
        return False


def get_session_health() -> Dict[str, Any]:
    """Returns a health summary of the current session."""
    now_ts = datetime.now(timezone.utc).timestamp()
    sb = _get_supabase_client()
    if sb:
        try:
            res = sb.table("scraper_sessions").select("*").eq("id", _SESSION_ID_KEY).execute()
            if res.data:
                row = res.data[0]
                cookies = row.get("cookies") or []
                exp_ts, exp_iso = _parse_cookie_expiry(cookies)
                hours_remaining = round((exp_ts - now_ts) / 3600.0, 1) if exp_ts else None
                return {
                    "exists": True,
                    "status": row.get("session_status"),
                    "hours_remaining": hours_remaining,
                    "expires_at": exp_iso,
                    "last_slid_at": row.get("last_slid_at"),
                    "cookie_count": len(cookies),
                }
        except Exception as e:
            logger.warning(f"[SESSION_MANAGER] Health query failed: {e}")

    # Fallback offline check
    cookies = load_active_session_cookies()
    if not cookies:
        return {"exists": False, "status": "missing", "hours_remaining": 0}
    exp_ts, exp_iso = _parse_cookie_expiry(cookies)
    hours_remaining = round((exp_ts - now_ts) / 3600.0, 1) if exp_ts else None
    return {
        "exists": True,
        "status": "active" if (hours_remaining is None or hours_remaining > 0) else "expired",
        "hours_remaining": hours_remaining,
        "expires_at": exp_iso,
        "last_slid_at": None,
        "cookie_count": len(cookies),
    }


if __name__ == "__main__":
    health = get_session_health()
    print("\n=== INSTAGRAM SESSION HEALTH ===")
    print(json.dumps(health, indent=2))
    
    # Test loading and auto-seeding
    print("\nTesting load_active_session_cookies()...")
    loaded = load_active_session_cookies()
    print(f"Loaded: {len(loaded) if loaded else 0} cookies.")
    
    # Re-check health after seeding
    health2 = get_session_health()
    print("\nUpdated Health:")
    print(json.dumps(health2, indent=2))
