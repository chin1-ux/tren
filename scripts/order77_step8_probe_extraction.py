import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from playwright.async_api import async_playwright

AUDIOS = [
    {"name": "Naina", "id": 7863, "audio_id": "2191461117582801"},
    {"name": "Sadeness", "id": 7816, "audio_id": "474517893035258"},
    {"name": "Yetu Pone", "id": 7857, "audio_id": "1434534261149691"},
    {"name": "Nenjukulle Nee", "id": 7826, "audio_id": "278125558187905"},
    {"name": "Milegi Milegi", "id": 7864, "audio_id": "368085497101907"},
]

COOKIE_FILE = "backend/cookies.json"

async def run_probe():
    print("=" * 80)
    print("ORDER 77 ITEM 8 - STEP A: AUDIO PAGE EXTRACTION PROOF")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80)

    if not os.path.exists(COOKIE_FILE):
        print(f"ERROR: Cookie file {COOKIE_FILE} not found!")
        sys.exit(1)

    with open(COOKIE_FILE) as f:
        cookies_raw = json.load(f)

    cookies = [
        {
            "name": c.get("name"),
            "value": c.get("value"),
            "domain": c.get("domain", ".instagram.com"),
            "path": c.get("path", "/"),
        }
        for c in cookies_raw
    ]

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        await context.add_cookies(cookies)

        page = await context.new_page()

        for item in AUDIOS:
            name = item["name"]
            aid = item["audio_id"]
            url = f"https://www.instagram.com/reels/audio/{aid}/"
            print(f"\nProbing [{name}] (audio_id: {aid})...")
            start_t = time.time()
            challenge_detected = False
            reels_extracted = []
            thumbs_downloaded = 0
            thumb_total_bytes = 0

            try:
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_timeout(3500)

                current_url = page.url
                if "challenge" in current_url or "login" in current_url:
                    challenge_detected = True
                    print(f"  [WARN] Challenge or Login redirect detected: {current_url}")

                # Extract reel cards from audio page
                cards = await page.evaluate("""() => {
                    const anchors = Array.from(document.querySelectorAll('a[href*="/reel/"], a[href*="/p/"]'));
                    return anchors.map(a => {
                        const bgDiv = a.querySelector('div[style*="background-image"]');
                        let bgUrl = null;
                        if (bgDiv) {
                            const style = bgDiv.getAttribute('style') || '';
                            const m = style.match(/url\\(["']?([^"']+)["']?\\)/);
                            if (m) bgUrl = m[1].replace(/&amp;/g, '&');
                        }
                        return {
                            href: a.getAttribute('href'),
                            bgUrl: bgUrl,
                            text: a.innerText
                        };
                    });
                }""")

                # Deduplicate by shortcode
                seen_codes = set()
                for c in cards:
                    href = c.get("href") or ""
                    m = re.search(r'/(?:reel|p)/([A-Za-z0-9_-]+)/', href)
                    if m:
                        sc = m.group(1)
                        if sc not in seen_codes:
                            seen_codes.add(sc)
                            reels_extracted.append({
                                "shortcode": sc,
                                "views_text": c.get("text", "").strip(),
                                "bg_url": c.get("bgUrl"),
                            })

                # Download thumbnails inside same session context (up to 12)
                for r in reels_extracted[:12]:
                    bg = r.get("bg_url")
                    if bg:
                        try:
                            img_resp = await context.request.get(bg, timeout=6000)
                            if img_resp.status == 200:
                                body = await img_resp.body()
                                thumbs_downloaded += 1
                                thumb_total_bytes += len(body)
                                r["thumb_bytes"] = len(body)
                        except Exception:
                            pass

            except Exception as e:
                print(f"  ERROR probing {name}: {e}")

            duration = time.time() - start_t
            res_summary = {
                "name": name,
                "audio_id": aid,
                "url": url,
                "duration_seconds": round(duration, 2),
                "reels_extracted": len(reels_extracted),
                "reels_sample": [r["shortcode"] for r in reels_extracted[:6]],
                "thumbnails_downloaded": thumbs_downloaded,
                "thumbnail_bytes_total": thumb_total_bytes,
                "challenge_detected": challenge_detected,
            }
            results.append(res_summary)

            print(f"  Reels extracted: {len(reels_extracted)} | Thumbs DL: {thumbs_downloaded} ({thumb_total_bytes:,} B) | Time: {duration:.2f}s | Challenge: {challenge_detected}")
            if reels_extracted:
                sample_scs = [r["shortcode"] for r in reels_extracted[:4]]
                print(f"  Sample shortcodes: {sample_scs}")

            # Polite pause between audios
            await asyncio.sleep(2.0)

        await browser.close()

    print("\n" + "=" * 80)
    print("STEP A PROBE SUMMARY TABLE:")
    print("-" * 80)
    print(f"{'Audio':<16} | {'Audio ID':<18} | {'Reels':<6} | {'Thumbs DL':<10} | {'Thumb KB':<10} | {'Time (s)':<8} | {'Challenge'}")
    print("-" * 80)
    for r in results:
        kb = f"{r['thumbnail_bytes_total'] / 1024:.1f} KB" if r['thumbnail_bytes_total'] else "0 KB"
        print(f"{r['name']:<16} | {r['audio_id']:<18} | {r['reels_extracted']:<6} | {r['thumbnails_downloaded']:<10} | {kb:<10} | {r['duration_seconds']:<8} | {r['challenge_detected']}")
    print("-" * 80)

    avg_reels = sum(r['reels_extracted'] for r in results) / max(1, len(results))
    print(f"Average reels extracted per audio: {avg_reels:.1f}")
    
    if any(r['challenge_detected'] for r in results):
        print("GATE RESULT: FAIL (Challenge/login-wall detected on at least one audio)")
    elif avg_reels < 8:
        print(f"GATE RESULT: FAIL (Average reels extracted {avg_reels:.1f} < 8 threshold)")
    else:
        print("GATE RESULT: PASS (All criteria met)")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_probe())
