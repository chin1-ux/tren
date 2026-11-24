#!/usr/bin/env python3
"""
PROBE v2: Deep Instagram Session & Search Exploration Diagnostics
Used for ORDER 94 Item 3.
Runs locally and on GitHub Actions runner.
"""

import os
import sys
import json
import asyncio
import re

# Ensure backend directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

from dotenv import load_dotenv
load_dotenv("backend/.env")
load_dotenv()

def get_public_ip_and_geo():
    import urllib.request
    try:
        req = urllib.request.Request("https://ipapi.co/json/", headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return f"{data.get('ip')} ({data.get('city')}, {data.get('region')}, {data.get('country_name')}) [Org: {data.get('org')}]"
    except Exception:
        pass
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as resp:
            ip = resp.read().decode("utf-8").strip()
            return f"{ip} (Geo lookup failed)"
    except Exception as e:
        return f"Unknown IP ({e})"

def load_cookies():
    # 1. Try cookie_sliding_manager (Supabase)
    try:
        from cookie_sliding_manager import load_active_session_cookies
        cookies = load_active_session_cookies()
        if cookies:
            mode = os.getenv("SCRAPER_MODE", "india")
            print(f"[AUTH] Loaded cookies for mode '{mode}' from Supabase scraper_sessions.")
            return cookies
    except Exception as e:
        print(f"[AUTH] Note: Could not load cookies from Supabase: {e}")

    # 2. Try cookies.json
    local_path = os.path.join(os.path.dirname(__file__), "..", "backend", "cookies.json")
    if os.path.exists(local_path):
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                cookies = json.load(f)
                print(f"[AUTH] Loaded cookies from backend/cookies.json.")
                return cookies
        except Exception as e:
            print(f"[AUTH] Error reading cookies.json: {e}")

    # 3. Try base64 env var
    b64_val = os.getenv("INSTAGRAM_COOKIES_B64")
    if b64_val:
        try:
            import base64
            decoded = base64.b64decode(b64_val).decode("utf-8")
            cookies = json.loads(decoded)
            print("[AUTH] Loaded cookies from INSTAGRAM_COOKIES_B64 env var.")
            return cookies
        except Exception as e:
            print(f"[AUTH] Error decoding INSTAGRAM_COOKIES_B64: {e}")

    return None

async def run_probe():
    print("=" * 60)
    print("ORDER 94 — ITEM 3: PROBE v2 EXECUTION")
    print("=" * 60)

    ip_info = get_public_ip_and_geo()
    print(f"Egress Public IP & Geo: {ip_info}\n")

    cookies = load_cookies()
    if not cookies:
        print("FATAL: No cookies available to probe.")
        sys.exit(1)

    if isinstance(cookies, list):
        cookie_dict = {c["name"]: c["value"] for c in cookies if isinstance(c, dict) and "name" in c and "value" in c}
        playwright_cookies = cookies
    elif isinstance(cookies, dict):
        cookie_dict = cookies
        playwright_cookies = [{"name": k, "value": v, "domain": ".instagram.com", "path": "/"} for k, v in cookies.items()]
    else:
        print("FATAL: Invalid cookie format.")
        sys.exit(1)

    csrf_token = cookie_dict.get("csrftoken", "")
    print(f"Cookie count: {len(cookie_dict)} | sessionid present: {'sessionid' in cookie_dict} | csrftoken present: {bool(csrf_token)}")

    try:
        from camoufox.async_api import AsyncCamoufox
    except ImportError:
        print("Camoufox not installed. Trying playwright firefox...")
        from playwright.async_api import async_playwright
        pw = await async_playwright().start()
        browser = await pw.firefox.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1280, "height": 800}, locale="en-US")
    else:
        camoufox_cm = AsyncCamoufox(headless=True, geoip=True)
        browser = await camoufox_cm.__aenter__()
        ctx = await browser.new_context(viewport={"width": 1280, "height": 800}, locale="en-US")

    try:
        # Standardize cookies for domain
        formatted_cookies = []
        for c in playwright_cookies:
            domain = c.get("domain", ".instagram.com")
            if not domain.startswith("."):
                domain = "." + domain
            formatted_cookies.append({
                "name": c["name"],
                "value": c["value"],
                "domain": domain,
                "path": c.get("path", "/"),
                "secure": True
            })
        await ctx.add_cookies(formatted_cookies)

        page = await ctx.new_page()

        # ------------------------------------------------------------------
        # 3a. Goto https://www.instagram.com/ first, then fetch /api/v1/accounts/current_user/?edit=true
        # ------------------------------------------------------------------
        print("\n--- 3a. NAVIGATE TO INSTAGRAM HOME & FETCH CURRENT_USER ---")
        try:
            await page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"Navigation to home failed: {e}")

        home_url = page.url
        home_title = await page.title()
        print(f"Home URL: {home_url}")
        print(f"Home Title: {home_title}")

        eval_current_user = f"""
        async () => {{
            try {{
                const res = await fetch('/api/v1/accounts/current_user/?edit=true', {{
                    method: 'GET',
                    headers: {{
                        'X-IG-App-ID': '936619743392459',
                        'X-CSRFToken': '{csrf_token}',
                        'X-Requested-With': 'XMLHttpRequest',
                        'Accept': '*/*'
                    }}
                }});
                const contentType = res.headers.get('content-type') || '';
                const text = await res.text();
                return {{
                    status: res.status,
                    contentType: contentType,
                    url: res.url,
                    body: text.substring(0, 300)
                }};
            }} catch (err) {{
                return {{ error: err.toString() }};
            }}
        }}
        """
        user_probe = await page.evaluate(eval_current_user)
        print(f"Current User Status: {user_probe.get('status')}")
        print(f"Content-Type: {user_probe.get('contentType')}")

        probe_username = None
        is_session_valid = False
        body_text = user_probe.get("body", "")

        if user_probe.get("status") == 200 and "application/json" in user_probe.get("contentType", ""):
            try:
                # Remove anti-hijacking prefix if present
                clean_body = body_text.replace("for (;;);", "").strip()
                data = json.loads(clean_body)
                probe_username = data.get("user", {}).get("username")
                if probe_username:
                    is_session_valid = True
                    print(f"JSON Username: {probe_username}")
            except Exception as pe:
                print(f"JSON parse error on current_user: {pe}")
        else:
            print(f"Non-JSON / Non-200 Body preview (first 200 chars): {body_text[:200]}")

        # ------------------------------------------------------------------
        # 3b. Goto /explore/search/keyword/?q=%23trendingreels & log responses
        # ------------------------------------------------------------------
        print("\n--- 3b. GOTO /explore/search/keyword/?q=%23trendingreels & LOG RESPONSES ---")
        captured_responses = []

        async def on_response(response):
            try:
                url = response.url
                # Filter down to instagram API, graphql, and relevant endpoints
                if any(x in url for x in ["/api/", "/graphql", "graphql/query", "/query", "/sections/"]):
                    status = response.status
                    headers = response.headers
                    friendly_name = headers.get("x-fb-friendly-name", "")
                    
                    # Try to extract doc_id from URL params if present
                    doc_id = ""
                    if "doc_id=" in url:
                        m = re.search(r'doc_id=([0-9]+)', url)
                        if m:
                            doc_id = m.group(1)

                    # Extract body keys
                    top_keys = []
                    has_media = False
                    has_items = False
                    has_edges = False

                    try:
                        resp_text = await response.text()
                        cleaned_resp = resp_text.replace("for (;;);", "").strip()
                        if "media" in cleaned_resp:
                            has_media = True
                        if "items" in cleaned_resp:
                            has_items = True
                        if "edges" in cleaned_resp:
                            has_edges = True

                        if cleaned_resp.startswith("{") or cleaned_resp.startswith("["):
                            parsed = json.loads(cleaned_resp)
                            if isinstance(parsed, dict):
                                top_keys = list(parsed.keys())
                            elif isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
                                top_keys = [f"[{len(parsed)} items: {list(parsed[0].keys())}]"]
                    except Exception:
                        pass

                    url_path = url.split("?")[0].replace("https://www.instagram.com", "")
                    flags = []
                    if has_media: flags.append("media")
                    if has_items: flags.append("items")
                    if has_edges: flags.append("edges")
                    flag_str = f" [FLAGS: {','.join(flags)}]" if flags else ""

                    entry = f"Response: {url_path} | Status: {status} | FriendlyName: {friendly_name} | doc_id: {doc_id} | Keys: {top_keys}{flag_str}"
                    captured_responses.append(entry)
                    print(entry)
            except Exception:
                pass

        page.on("response", on_response)

        search_url = "https://www.instagram.com/explore/search/keyword/?q=%23trendingreels"
        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(8000)
        except Exception as e:
            print(f"Navigation to search keyword URL timed out or failed: {e}")

        # ------------------------------------------------------------------
        # 3c. Print page text (first 500 chars), final URL, title, screenshot
        # ------------------------------------------------------------------
        print("\n--- 3c. SEARCH KEYWORD PAGE STATE & SCREENSHOT ---")
        final_url = page.url
        final_title = await page.title()
        print(f"Final URL: {final_url}")
        print(f"Final Title: {final_title}")

        try:
            raw_text = await page.evaluate("() => document.body ? document.body.innerText : ''")
            cleaned_text = re.sub(r'\s+', ' ', raw_text).strip()
            print(f"Page Text Preview (first 500 chars):\n{cleaned_text[:500]}\n")
        except Exception as te:
            print(f"Could not retrieve page text: {te}")

        screenshot_path = "probe_v2_screenshot.png"
        await page.screenshot(path=screenshot_path, full_page=False)
        print(f"Screenshot saved to: {screenshot_path}")

        # Also copy screenshot to artifact dir if it exists
        artifact_dir = os.path.join(os.path.expanduser("~"), ".gemini", "antigravity", "brain", "c4d85c1e-97dd-4791-8546-3219f8a3f107")
        if os.path.exists(artifact_dir):
            import shutil
            shutil.copy(screenshot_path, os.path.join(artifact_dir, "probe_v2_screenshot.png"))
            print(f"Screenshot copied to artifact dir: {artifact_dir}")

        # Overall Verdict
        print("\n" + "=" * 60)
        if is_session_valid:
            print(f"FINAL PROBE VERDICT: VALID (Username: {probe_username})")
        else:
            print("FINAL PROBE VERDICT: DEAD / BLOCKED")
        print("=" * 60)

    finally:
        try:
            await ctx.close()
            await browser.close()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(run_probe())
