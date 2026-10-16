import os
import sys
import json
import time
import random
import asyncio
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")

TARGET_AUDIOS = [
    {"name": "Naina", "audio_id": "2191461117582801"},
    {"name": "Sadeness", "audio_id": "474517893035258"},
    {"name": "Yetu Pone", "audio_id": "1434534261149691"},
    {"name": "Nenjukulle Nee", "audio_id": "278125558187905"},
    {"name": "Milegi Milegi", "audio_id": "368085497101907"},
]

async def run_probe():
    lines = []
    def log(msg=""):
        print(msg)
        lines.append(msg)

    log("=" * 85)
    log("ORDER 77 ITEM 8 STEP A: LIVE AUDIO PAGE EXTRACTION GATE (GITHUB ACTIONS RUNNER)")
    log(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    log(f"Runner OS: {os.getenv('RUNNER_OS', 'local')}")
    log("=" * 85)

    cookies_path = "backend/cookies.json"
    cookies = []
    if os.path.exists(cookies_path):
        try:
            with open(cookies_path, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            log(f"[OK] Loaded {len(cookies)} Instagram session cookies from {cookies_path}")
        except Exception as e:
            log(f"[WARN] Failed to load cookies: {e}")
    else:
        log(f"[WARN] No {cookies_path} found! Proceeding tokenless / unauthenticated.")

    audio_results = []
    total_reels_extracted = 0
    total_thumbs_downloaded = 0

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
            locale="en-US"
        )

        if cookies:
            # Format cookies for playwright
            pw_cookies = []
            for c in cookies:
                cookie_entry = {
                    "name": c.get("name"),
                    "value": c.get("value"),
                    "domain": c.get("domain", ".instagram.com"),
                    "path": c.get("path", "/"),
                }
                # Fix domain leading dot if needed
                if cookie_entry["domain"].startswith("http"):
                    cookie_entry["domain"] = ".instagram.com"
                pw_cookies.append(cookie_entry)
            await context.add_cookies(pw_cookies)
            log("[OK] Injected cookies into browser context")

        page = await context.new_page()

        for idx, item in enumerate(TARGET_AUDIOS, 1):
            name = item["name"]
            aid = item["audio_id"]
            url = f"https://www.instagram.com/reels/audio/{aid}/"

            log(f"\n[{idx}/5] Probing audio: '{name}' (ID: {aid})")
            log(f"URL: {url}")

            t0 = time.perf_counter()
            login_wall = False
            challenge = False
            http_429 = False
            extracted_reels = []

            # Add random human delay
            if idx > 1:
                delay = random.uniform(2.5, 4.5)
                await asyncio.sleep(delay)

            try:
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                elapsed = time.perf_counter() - t0

                if resp:
                    status = resp.status
                    if status == 429:
                        http_429 = True
                    log(f"Navigation status: {status} in {elapsed:.2f}s")

                current_url = page.url
                log(f"Landed URL: {current_url}")

                if "/accounts/login" in current_url:
                    login_wall = True
                    log("[ALERT] Redirected to Login Wall!")
                elif "/challenge" in current_url:
                    challenge = True
                    log("[ALERT] Redirected to Challenge!")

                # Check page body for challenge/login text
                body_text = await page.inner_text("body")
                if "Suspicious Login Attempt" in body_text or "help us verify" in body_text.lower():
                    challenge = True
                    log("[ALERT] Challenge text detected in page content!")

                if not login_wall and not challenge and not http_429:
                    # Scroll down once to trigger grid lazy load
                    await page.evaluate("window.scrollBy(0, 800)")
                    await asyncio.sleep(2.0)

                    # Extract reel links
                    reel_anchors = await page.query_selector_all("a[href*='/reel/'], a[href*='/p/']")
                    seen_codes = set()

                    for a in reel_anchors:
                        href = await a.get_attribute("href") or ""
                        # Match /reel/<shortcode>/ or /p/<shortcode>/
                        import re
                        m = re.search(r"/(?:reel|p)/([A-Za-z0-9_-]+)/", href)
                        if not m:
                            continue
                        sc = m.group(1)
                        if sc in seen_codes:
                            continue
                        seen_codes.add(sc)

                        # Try to find creator handle and img thumbnail in-session
                        creator = "unknown"
                        thumb_bytes = 0

                        # Check img inside this anchor
                        img = await a.query_selector("img")
                        if img:
                            alt = await img.get_attribute("alt") or ""
                            # Sometimes alt has "Photo by Creator on..." or "Creator's photo"
                            alt_m = re.search(r"by\s+([A-Za-z0-9_.]+)", alt)
                            if alt_m:
                                creator = alt_m.group(1)
                            
                            src = await img.get_attribute("src") or ""
                            if src and src.startswith("http"):
                                # Fetch thumbnail bytes inside the authenticated session
                                try:
                                    img_b64 = await page.evaluate("""async (url) => {
                                        try {
                                            const r = await fetch(url);
                                            const b = await r.blob();
                                            return new Promise((resolve) => {
                                                const reader = new FileReader();
                                                reader.onloadend = () => resolve(reader.result);
                                                reader.readAsDataURL(b);
                                            });
                                        } catch (e) {
                                            return null;
                                        }
                                    }""", src)
                                    if img_b64 and "," in img_b64:
                                        import base64
                                        raw_data = base64.b64decode(img_b64.split(",", 1)[1])
                                        thumb_bytes = len(raw_data)
                                except Exception as e_th:
                                    pass

                        extracted_reels.append({
                            "shortcode": sc,
                            "creator": creator,
                            "thumb_bytes": thumb_bytes
                        })

                elapsed_total = time.perf_counter() - t0
                log(f"Extraction completed in: {elapsed_total:.2f}s")
                log(f"Total reels found      : {len(extracted_reels)}")
                log(f"Login Wall             : {login_wall}")
                log(f"Challenge              : {challenge}")
                log(f"HTTP 429               : {http_429}")

                if extracted_reels:
                    log("Extracted Reels Sample:")
                    for r_idx, r_item in enumerate(extracted_reels[:12], 1):
                        sc = r_item["shortcode"]
                        cr = r_item["creator"]
                        tb = r_item["thumb_bytes"]
                        log(f"   [{r_idx:02d}] https://www.instagram.com/reel/{sc}/ | Creator: @{cr:<15} | Thumb bytes: {tb} B")

                audio_results.append({
                    "name": name,
                    "audio_id": aid,
                    "reels_count": len(extracted_reels),
                    "reels": extracted_reels,
                    "seconds": round(elapsed_total, 2),
                    "login_wall": login_wall,
                    "challenge": challenge,
                    "http_429": http_429
                })

            except Exception as e_page:
                elapsed_total = time.perf_counter() - t0
                log(f"Error extracting audio {name}: {e_page}")
                audio_results.append({
                    "name": name,
                    "audio_id": aid,
                    "reels_count": 0,
                    "reels": [],
                    "seconds": round(elapsed_total, 2),
                    "login_wall": True,
                    "challenge": False,
                    "http_429": False,
                    "error": str(e_page)
                })

        await browser.close()

    log("\n" + "=" * 85)
    log("STEP A GATE EVALUATION & SUMMARY")
    log("=" * 85)

    audios_ge_8 = 0
    total_reels = 0
    total_thumbs_with_bytes = 0

    for res in audio_results:
        cnt = res["reels_count"]
        total_reels += cnt
        thumbs_ok = sum(1 for r in res["reels"] if r.get("thumb_bytes", 0) > 0)
        total_thumbs_with_bytes += thumbs_ok
        if cnt >= 8:
            audios_ge_8 += 1
        log(f"Audio '{res['name']:<15}' | Reels: {cnt:2d} (>=8: {cnt>=8}) | Thumbs: {thumbs_ok}/{cnt} | Time: {res['seconds']}s | Wall: {res['login_wall']} | 429: {res['http_429']}")

    thumb_rate = (total_thumbs_with_bytes / total_reels * 100.0) if total_reels > 0 else 0.0

    log("-" * 85)
    log(f"Audios with >= 8 reels           : {audios_ge_8}/5 (Required: >= 3)")
    log(f"Thumbnail in-session success rate: {thumb_rate:.1f}% (Required: >= 80%)")

    gate_passed = (audios_ge_8 >= 3) and (thumb_rate >= 80.0)

    if gate_passed:
        log("\n>>> GATE STATUS: PASSED <<<")
        log("Proceeding with Step B thumbnail storage & cache.")
    else:
        log("\n>>> GATE STATUS: FAILED <<<")
        log("Per Order 77 Rule: Step A failed. Halting Item 8. Shipping 'Open on Instagram' fallback only.")
    log("=" * 85)

    out_file = "evidence/order77/item8_step_a_gha.txt"
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nSaved raw evidence to {out_file}")

if __name__ == "__main__":
    asyncio.run(run_probe())
