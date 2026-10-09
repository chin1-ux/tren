r"""
backend/audio_capture.py
Audio-First Capture Job (Order 59 Part C).
- Incorporates exact production extractor patterns:
  1) Session warm-up on https://www.instagram.com/
  2) Pattern 1: Modern Instagram Audio page layout: r'Audio\s*\n?\s*([\d,.]+)\s*([KMB]?)'
  3) Pattern 2: Traditional layout: r'([\d,.]+)\s*([KMB]?)\s*(?:reels?|posts?|videos?)'
  4) Fallback from inner_text to page.content() HTML search
- Candidates: Audios with 2+ reels OR 2+ creators in a rolling 72h window from reels (paginated .range()).
- Excludes audios measured within the last 3 hours.
- Pacing: Max 15 pages/run, 150/day, random 8-20s delays.
- Aborts immediately on challenge / login redirect.
- Stores: raw_text, parsed int, precision (exact/K/M) into audio_count_history.
"""

import os
import re
import sys
import time
import json
import random
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("audio_capture")

def parse_reels_count_text(text: str) -> tuple[int | None, str | None, str | None]:
    if not text:
        return None, None, None

    # Strict pattern requiring the word 'reels', 'posts', or 'videos'
    match = re.search(r'([\d,.]+)\s*([KMB]?)\s*(?:reels?|posts?|videos?)', text, re.IGNORECASE)
    if not match:
        return None, None, None

    raw_matched = match.group(0).strip()
    val_str, suffix = match.groups()
    val_str = val_str.replace(',', '').strip()
    try:
        val = float(val_str)
        if val <= 0:
            return None, None, None
        suffix_upper = suffix.upper() if suffix else ''
        if suffix_upper == 'K':
            val *= 1000
            precision_bucket = 'K'
        elif suffix_upper == 'M':
            val *= 1_000_000
            precision_bucket = 'M'
        elif suffix_upper == 'B':
            val *= 1_000_000_000
            precision_bucket = 'B'
        else:
            precision_bucket = 'exact'
        return int(val), precision_bucket, raw_matched
    except ValueError:
        return None, None, None

def run_audio_capture():
    load_dotenv("backend/.env")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        logger.error("Supabase credentials not configured.")
        return

    sb = create_client(url, key)
    now_utc = datetime.now(timezone.utc)

    # 1. Daily rate limit check (max 150/day)
    day_ago = (now_utc - timedelta(days=1)).isoformat()
    daily_res = sb.table("audio_count_history").select("id", count="exact").gte("captured_at", day_ago).execute()
    daily_count = daily_res.count or 0
    if daily_count >= 150:
        logger.info(f"Daily audio capture cap reached ({daily_count}/150). Skipping run.")
        return

    # 2. Watchlist Priority (Order 61 Part E2): measure active watchlist audios first (re-measure every 6h)
    h6_ago = (now_utc - timedelta(hours=6)).isoformat()
    wl_res = sb.table("watchlist").select("audio_id").eq("status", "watching").execute()
    active_wl_aids = [r["audio_id"] for r in (wl_res.data or []) if r.get("audio_id")]

    # Check which watchlist audios were measured in last 6h
    measured_6h = set()
    if active_wl_aids:
        ach_6h = sb.table("audio_count_history").select("audio_id").in_("audio_id", active_wl_aids).gte("captured_at", h6_ago).execute()
        measured_6h = {r["audio_id"] for r in (ach_6h.data or []) if r.get("audio_id")}

    watchlist_targets = [aid for aid in active_wl_aids if aid not in measured_6h][:15]

    # 3. Exclude audios measured in last 3h for general candidates
    h3_ago = (now_utc - timedelta(hours=3)).isoformat()
    recent_res = sb.table("audio_count_history").select("audio_id").gte("captured_at", h3_ago).execute()
    recent_measured = set(r["audio_id"] for r in (recent_res.data or []))
    recent_measured.update(watchlist_targets)

    # 4. Fetch additional candidates from reels in rolling 72h window if under 15 cap
    candidates_needed = 15 - len(watchlist_targets)
    candidate_targets = []
    if candidates_needed > 0:
        h72_ago = (now_utc - timedelta(hours=72)).isoformat()
        audio_stats = {}
        offset = 0
        PAGE_SIZE = 1000

        while True:
            res = sb.table("reels") \
                .select("audio_id, owner_username") \
                .gte("created_at", h72_ago) \
                .not_.is_("audio_id", "null") \
                .range(offset, offset + PAGE_SIZE - 1) \
                .execute()
            data = res.data or []
            for r in data:
                aid = r.get("audio_id")
                if not aid:
                    continue
                aid = str(aid).strip()
                if not aid or aid in ("0", "Unknown"):
                    continue
                if aid not in audio_stats:
                    audio_stats[aid] = {"creators": set(), "reels": 0}
                audio_stats[aid]["reels"] += 1
                if r.get("owner_username"):
                    audio_stats[aid]["creators"].add(r["owner_username"])

            if len(data) < PAGE_SIZE:
                break
            offset += PAGE_SIZE

        eligible = []
        for aid, st in audio_stats.items():
            if aid in recent_measured:
                continue
            c_cnt = len(st["creators"])
            r_cnt = st["reels"]
            if r_cnt >= 2 or c_cnt >= 2:
                eligible.append((aid, c_cnt, r_cnt))

        eligible.sort(key=lambda x: (x[1], x[2]), reverse=True)
        candidate_targets = eligible[:candidates_needed]

    # Combine: (audio_id, creators, reels)
    targets = [(aid, 0, 0) for aid in watchlist_targets] + candidate_targets

    if not targets:
        logger.info("No eligible audio capture targets for this cycle.")
        return

    logger.info(f"Selected {len(targets)} candidate audios for count measurement.")

    import asyncio
    asyncio.run(_measure_audio_targets(targets, sb))

async def _measure_audio_targets(targets: list[tuple[str, int, int]], sb):
    from camoufox.async_api import AsyncCamoufox

    cookies_path = os.path.join(os.path.dirname(__file__), "cookies.json")
    if not os.path.exists(cookies_path):
        cookies_path = "backend/cookies.json"

    raw_c = []
    if os.path.exists(cookies_path):
        try:
            with open(cookies_path, "r", encoding="utf-8") as f:
                raw_c = json.load(f)
        except Exception as ce:
            logger.warning(f"Error reading {cookies_path}: {ce}")
    elif os.getenv("INSTAGRAM_COOKIES_B64"):
        try:
            import base64
            b64_val = os.getenv("INSTAGRAM_COOKIES_B64").strip()
            raw_c = json.loads(base64.b64decode(b64_val).decode("utf-8"))
        except Exception as b64e:
            logger.warning(f"Error decoding INSTAGRAM_COOKIES_B64: {b64e}")

    formatted_cookies = [
        {
            "name": c["name"],
            "value": c["value"],
            "domain": c.get("domain", ".instagram.com"),
            "path": c.get("path", "/"),
        }
        for c in raw_c
        if isinstance(c, dict) and "name" in c and "value" in c
    ]

    measured_rows = []

    async with AsyncCamoufox(headless=True) as browser:
        ctx = await browser.new_context(no_viewport=True)
        if formatted_cookies:
            await ctx.add_cookies(formatted_cookies)

        page = await ctx.new_page()

        # Session warm-up
        try:
            await page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(2000)
        except Exception as warm_err:
            logger.warning(f"Warm-up navigation failed (non-fatal): {warm_err}")

        for idx, (aid, creators, reels) in enumerate(targets):
            url = f"https://www.instagram.com/reels/audio/{aid}/"
            count_val = None
            precision = None
            raw_text = None
            status = "no_count"

            for attempt in range(2):
                try:
                    if attempt == 0:
                        resp = await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    else:
                        logger.info(f"Audio {aid}: count missing on attempt 1. Waiting 10s and reloading...")
                        await page.wait_for_timeout(10000)
                        resp = await page.reload(wait_until="domcontentloaded", timeout=25000)

                    current_url = page.url
                    if "challenge" in current_url or "login" in current_url:
                        logger.error(f"CHALLENGE / LOGIN REDIRECT DETECTED at {current_url}. Aborting audio capture run.")
                        await ctx.close()
                        return

                    await page.wait_for_timeout(4000)
                    try:
                        body_text = await page.inner_text("body", timeout=10000)
                    except Exception:
                        body_text = ""

                    count_val, precision, raw_text = parse_reels_count_text(body_text)

                    # Fallback to full HTML content
                    if count_val is None:
                        content = await page.content()
                        count_val, precision, raw_text = parse_reels_count_text(content)

                    if count_val is not None and count_val > 0:
                        status = "success"
                        break
                except Exception as e:
                    logger.warning(f"Audio {aid} attempt {attempt+1} error: {e}")

            run_id = os.getenv("GITHUB_RUN_ID")
            row = {
                "audio_id": aid,
                "raw_text": raw_text,
                "use_count": count_val if status == "success" else None,
                "precision": precision if status == "success" else None,
                "status": status,
                "source": "instagram_audio_page",
            }
            if run_id:
                row["run_id"] = run_id

            measured_rows.append(row)
            if status == "success":
                logger.info(f"Captured audio {aid}: {raw_text} -> parsed={count_val} ({precision})")
            else:
                logger.warning(f"Audio {aid}: count text not found (status=no_count, use_count=None)")

            if idx < len(targets) - 1:
                delay = random.uniform(8.0, 20.0)
                await asyncio.sleep(delay)

        await ctx.close()

    if measured_rows:
        try:
            sb.table("audio_count_history").insert(measured_rows).execute()
        except Exception as insert_err:
            logger.warning(f"Insert with status/run_id failed ({insert_err}), falling back to core columns...")
            fallback_rows = [
                {
                    "audio_id": r["audio_id"],
                    "raw_text": r["raw_text"],
                    "use_count": r["use_count"],
                    "precision": r["precision"],
                    "source": r["source"],
                }
                for r in measured_rows
                if r.get("use_count") is not None
            ]
            if fallback_rows:
                sb.table("audio_count_history").insert(fallback_rows).execute()
        logger.info(f"Recorded {len(measured_rows)} audio count measurements in audio_count_history.")
    else:
        logger.info("0 audio counts recorded in this cycle.")

if __name__ == "__main__":
    run_audio_capture()
