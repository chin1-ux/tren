import os
import sys
import re
import json
import time
import asyncio
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client
from playwright.async_api import async_playwright

# Set console encoding to UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# Load environment
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: Supabase credentials not found in environment.")
    sys.exit(1)

sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

async def verify_trends():
    # 1. Fetch active trends
    print("Fetching active trends from Supabase...")
    res = sb.table("trends").select("id,audio_title,audio_artist,audio_id,status,audio_use_count").in_("status", ["emerging", "rising"]).execute()
    trends = res.data or []
    print(f"Found {len(trends)} active trends to verify.")

    if not trends:
        print("No active trends to verify.")
        return

    # Create screenshots directory in artifacts
    screenshots_dir = r"C:\Users\Chinmay\.gemini\antigravity-ide\brain\3d13ac3c-178f-4c4c-904c-0ed927f6fd3c\screenshots"
    os.makedirs(screenshots_dir, exist_ok=True)

    results = []

    # 2. Launch Playwright
    async with async_playwright() as p:
        print("Launching Chromium browser...")
        browser = await p.chromium.launch(headless=True)
        
        # Setup context with cookies if available
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Load cookies
        cookies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.json")
        if os.path.exists(cookies_path):
            try:
                with open(cookies_path, "r", encoding="utf-8") as f:
                    cookies = json.load(f)
                formatted_cookies = [
                    {
                        "name": c["name"],
                        "value": c["value"],
                        "domain": c.get("domain", ".instagram.com"),
                        "path": c.get("path", "/"),
                    }
                    for c in cookies
                ]
                await context.add_cookies(formatted_cookies)
                print(f"Loaded {len(formatted_cookies)} cookies from cookies.json")
            except Exception as e:
                print(f"Warning: Failed to load cookies: {e}")
        else:
            print("Warning: cookies.json not found, proceeding without authentication.")

        page = await context.new_page()

        for idx, trend in enumerate(trends, 1):
            trend_id = trend["id"]
            audio_title = trend["audio_title"]
            audio_artist = trend["audio_artist"]
            audio_id = trend.get("audio_id")
            db_count = trend.get("audio_use_count") or 0
            status = trend["status"]

            print(f"\n[{idx}/{len(trends)}] Verifying: {audio_title} by {audio_artist} (ID: {trend_id}, Status: {status})")

            if not audio_id:
                print(f"  Skipping: No audio_id for trend {trend_id}")
                results.append({
                    "id": trend_id,
                    "title": audio_title,
                    "artist": audio_artist,
                    "status": status,
                    "db_count": db_count,
                    "live_count": None,
                    "trending_badge": False,
                    "verified": "No Audio ID",
                    "screenshot_path": None
                })
                continue

            url = f"https://www.instagram.com/reels/audio/{audio_id}/"
            print(f"  Navigating to: {url}")
            
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                # Wait 5 seconds for client-side JS / hydration
                await page.wait_for_timeout(5000)

                # Get DOM text content of the body to search for reel counts
                body_text = await page.inner_text("body")
                
                # Check for reels count in the DOM text
                # Look for patterns like "123,456 reels" or "1.2M reels" or "10.5K reels"
                reels_match = re.search(r"([\d\.,]+[KMB]?)\s*reels", body_text, re.IGNORECASE)
                live_count_text = reels_match.group(1) if reels_match else None
                
                # Also try looking for elements with specific text containing "reels" to be sure
                if not live_count_text:
                    # Let's inspect all elements containing "reels"
                    elements = await page.query_selector_all("text=/reels/i")
                    for el in elements:
                        text = await el.inner_text()
                        match = re.search(r"([\d\.,]+[KMB]?)\s*reels", text, re.IGNORECASE)
                        if match:
                            live_count_text = match.group(1)
                            break

                # Check for trending badge
                # Instagram trending icon is typically an SVG containing a diagonal up arrow,
                # or a container containing "Trending" text, or an icon next to the reel count.
                trending_badge = False
                
                # Method A: Look for "Trending" text in the DOM
                if "trending" in body_text.lower():
                    trending_badge = True
                
                # Method B: Look for the trending SVG icon
                # Up-right arrow SVG path is typical for trending on Instagram
                svg_elements = await page.query_selector_all("svg")
                for svg in svg_elements:
                    html_content = await svg.inner_html()
                    # A trending arrow path usually contains diagonal up-right coordinates
                    if "trending" in html_content.lower() or "arrow" in html_content.lower():
                        trending_badge = True
                        break

                # Parse live count to integer
                live_count = None
                if live_count_text:
                    clean_text = live_count_text.upper().replace(",", "").strip()
                    try:
                        if 'K' in clean_text:
                            live_count = int(float(clean_text.replace('K', '')) * 1000)
                        elif 'M' in clean_text:
                            live_count = int(float(clean_text.replace('M', '')) * 1000000)
                        elif 'B' in clean_text:
                            live_count = int(float(clean_text.replace('B', '')) * 1000000000)
                        else:
                            live_count = int(clean_text)
                    except ValueError:
                        pass

                # Take screenshot
                screenshot_filename = f"trend_{trend_id}_{audio_id}.png"
                screenshot_path = os.path.join(screenshots_dir, screenshot_filename)
                await page.screenshot(path=screenshot_path)
                print(f"  Screenshot saved: {screenshot_path}")

                # Determine if verified true
                # If the live count is reasonably high, or has trending badge, or count is growing
                is_verified = "False"
                reasons = []
                if trending_badge:
                    is_verified = "True"
                    reasons.append("Trending Badge Found")
                if live_count and live_count >= db_count:
                    is_verified = "True"
                    reasons.append(f"Reel count increased or matches ({live_count} vs {db_count})")
                elif live_count and live_count > 1000:
                    is_verified = "True"
                    reasons.append(f"Has substantial active reels count ({live_count})")
                
                if not reasons:
                    reasons.append("Low count / no trending indicators found")
                
                verification_reason = ", ".join(reasons)
                print(f"  Live Reels Count: {live_count_text} ({live_count}) | Trending Badge: {trending_badge}")
                print(f"  Verification result: {is_verified} ({verification_reason})")

                results.append({
                    "id": trend_id,
                    "title": audio_title,
                    "artist": audio_artist,
                    "status": status,
                    "db_count": db_count,
                    "live_count_text": live_count_text,
                    "live_count": live_count,
                    "trending_badge": trending_badge,
                    "verified": is_verified,
                    "reason": verification_reason,
                    "screenshot_path": f"screenshots/{screenshot_filename}"
                })

            except Exception as e:
                print(f"  Error loading/parsing page: {e}")
                results.append({
                    "id": trend_id,
                    "title": audio_title,
                    "artist": audio_artist,
                    "status": status,
                    "db_count": db_count,
                    "live_count": None,
                    "trending_badge": False,
                    "verified": "Error",
                    "reason": str(e),
                    "screenshot_path": None
                })
            
            # Simple delay to respect rate limits
            await asyncio.sleep(2)

        await browser.close()

    # 3. Generate verification report
    report_path = r"C:\Users\Chinmay\.gemini\antigravity-ide\brain\3d13ac3c-178f-4c4c-904c-0ed927f6fd3c\verification_report.md"
    with open(report_path, "w", encoding="utf-8") as rf:
        rf.write("# Instagram Audio Trend Verification Report\n\n")
        rf.write(f"Generated at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n")
        rf.write("| ID | Audio Title | Status | DB Count | Live Count | Trending Badge | Verified? | Reason | Screenshot |\n")
        rf.write("|---|---|---|---|---|---|---|---|---|\n")
        for r in results:
            title_esc = r["title"].replace("|", "\\|")
            artist_esc = r["artist"].replace("|", "\\|") if r["artist"] else ""
            screenshot_link = f"[View](./{r['screenshot_path']})" if r.get("screenshot_path") else "N/A"
            rf.write(f"| {r['id']} | **{title_esc}** <br>_{artist_esc}_ | {r['status']} | {r['db_count']:,} | {r.get('live_count_text') or 'N/A'} | {'Yes' if r['trending_badge'] else 'No'} | **{r['verified']}** | {r.get('reason') or ''} | {screenshot_link} |\n")

    print(f"\nVerification completed! Report generated at: {report_path}")

if __name__ == "__main__":
    asyncio.run(verify_trends())
