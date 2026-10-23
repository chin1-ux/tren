"""
Trendrop 1-Tap Instagram Cookie Sync
====================================
Runs on your local PC (trusted residential IP).
1. Opens headful browser for Instagram login / 2FA.
2. Captures fresh session cookies.
3. Automatically updates:
   - Supabase `scraper_sessions` table (instant dynamic access for scrapers)
   - Local `backend/cookies.json` and `.env`
   - GitHub Actions Secret `INSTAGRAM_COOKIES_B64` on chin1-ux/tren & ch1n-may/trendrop
"""

import sys
import os
import json
import base64
import time
import subprocess
from datetime import datetime, timezone

# Add backend directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(os.path.dirname(script_dir), "backend")
sys.path.insert(0, backend_dir)

from cookie_sliding_manager import save_slid_cookies, _parse_cookie_expiry, get_session_health


def update_github_secret(repo: str, secret_name: str, secret_value: str) -> bool:
    """Updates a GitHub Actions secret using gh CLI."""
    try:
        proc = subprocess.run(
            ["gh", "secret", "set", secret_name, "--repo", repo],
            input=secret_value,
            text=True,
            capture_output=True,
            check=True
        )
        print(f"  ✓ Updated secret '{secret_name}' on {repo}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ⚠️ Could not update secret on {repo} (gh CLI error): {e.stderr.strip()}")
        return False
    except FileNotFoundError:
        print("  ⚠️ GitHub CLI (`gh`) not installed or not in PATH — skipping secret update.")
        return False


def run_1tap_sync():
    print("=" * 65)
    print("🚀 TRENDROP 1-TAP INSTAGRAM COOKIE SYNC")
    print("=" * 65)
    
    current_health = get_session_health()
    print(f"Current Session Status: {current_health.get('status')} | Hours remaining: {current_health.get('hours_remaining')}")
    print("\nLaunching local browser window to capture fresh Instagram session...")
    print("👉 If you are not logged in, please log in in the opened window.")
    print("👉 Once logged in, the script will automatically detect and sync cookies.")
    print("-" * 65)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is required for 1-tap sync. Run: pip install playwright")
        return

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
        print("\nWaiting for active logged-in session (looking for 'sessionid' cookie)...")

        captured_cookies = []
        start_wait = time.time()
        # Wait up to 180 seconds for user to log in if needed
        while time.time() - start_wait < 180:
            cookies = context.cookies()
            session_cookie = next((c for c in cookies if c.get("name") == "sessionid"), None)
            
            # If sessionid is present and page has loaded beyond the login page
            if session_cookie and "/accounts/login/" not in page.url:
                # Extra small sleep to allow Instagram to set remaining security cookies
                time.sleep(2)
                captured_cookies = context.cookies()
                print("🎉 Active logged-in session detected!")
                break
            time.sleep(2)

        browser.close()

        if not captured_cookies:
            print("\n❌ Timed out waiting for login. No active session cookies captured.")
            return

        # 1. Save to local cookies.json
        cookies_json_path = os.path.join(backend_dir, "cookies.json")
        with open(cookies_json_path, "w", encoding="utf-8") as f:
            json.dump(captured_cookies, f, indent=2)
        print(f"\n  ✓ Saved fresh cookies to {cookies_json_path}")

        # 2. Encode to base64
        cookies_b64 = base64.b64encode(json.dumps(captured_cookies).encode("utf-8")).decode("utf-8")

        # 3. Save to Supabase scraper_sessions table
        saved_db = save_slid_cookies(captured_cookies, reels_scraped=0, run_id="1tap_local_sync")
        if saved_db:
            print("  ✓ Saved fresh session to Supabase `scraper_sessions` table!")

        # 4. Update GitHub Secrets
        print("\nUpdating GitHub Actions Secrets:")
        update_github_secret("chin1-ux/tren", "INSTAGRAM_COOKIES_B64", cookies_b64)
        update_github_secret("ch1n-may/trendrop", "INSTAGRAM_COOKIES_B64", cookies_b64)

        # 5. Show summary
        exp_ts, exp_iso = _parse_cookie_expiry(captured_cookies)
        print("\n" + "=" * 65)
        print("✅ 1-TAP SYNC COMPLETED SUCCESSFULLY!")
        print(f"Total Cookies Captured: {len(captured_cookies)}")
        print(f"Earliest Expiry: {exp_iso}")
        print("Scrapers will automatically use these fresh cookies on next run!")
        print("=" * 65)


if __name__ == "__main__":
    run_1tap_sync()
