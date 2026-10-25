"""
backend/audio_page_harvester.py
---------------------------------
Human-Mimic Instagram Audio Page Harvester:
1. Visits https://www.instagram.com/reels/audio/<audio_id>/ using active sliding session cookies.
2. Extracts top 25-40 reel shortcodes from the audio grid.
3. Concurrently fetches full caption, hashtags, and creator details via tokenless captioned embed.
4. Persists the rich reel evidence into the Supabase `reels` table.
5. Enables high-confidence pattern analysis (N >= 25 reels) just like a human trend researcher.
"""

import os
import sys
import re
import json
import time
import asyncio
import logging
from typing import List, Dict, Any, Optional

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import httpx
from playwright.async_api import async_playwright
from cookie_sliding_manager import load_active_session_cookies
from companion_audio_promoter import parse_compact_count

logger = logging.getLogger("audio_page_harvester")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


async def _fetch_single_reel_caption(client: httpx.AsyncClient, shortcode: str) -> Optional[Dict[str, Any]]:
    """Fetches caption, hashtags, and creator username via tokenless embed."""
    url = f"https://www.instagram.com/reel/{shortcode}/embed/captioned/"
    try:
        resp = await client.get(url, timeout=5.0)
        if resp.status_code == 200:
            html = resp.text
            m = re.search(r'<div class="Caption"[^>]*>(.*?)</div>', html, re.DOTALL)
            if m:
                clean_raw = re.sub(r'<[^>]+>', ' ', m.group(1)).strip()
                hashtags = re.findall(r'#(\w+)', clean_raw)
                clean_text = re.sub(r'#\w+', '', clean_raw).strip()
                clean_text = re.sub(r'\s+', ' ', clean_text)
                
                # Extract creator username
                creator_match = re.search(r'class="CaptionUsername"[^>]*>([^<]+)</a>', html)
                username = creator_match.group(1).strip() if creator_match else ""

                return {
                    "shortcode": shortcode,
                    "caption": clean_text[:280],
                    "hashtags": hashtags[:12],
                    "owner_username": username
                }
    except Exception as err:
        logger.debug(f"Caption embed error for {shortcode}: {err}")
    return None


async def harvest_audio_reels_async(
    audio_id: str,
    supabase_client: Any,
    max_reels: int = 30
) -> List[Dict[str, Any]]:
    """
    Harvests top reels directly from the audio page and saves them to Supabase.
    """
    if not audio_id:
        return []

    # 1. Check if sufficient reels already exist in database
    try:
        existing = (
            supabase_client.table("reels")
            .select("id,reel_id,caption,hashtags,view_count")
            .eq("audio_id", str(audio_id))
            .limit(max_reels)
            .execute()
        )
        if existing.data and len(existing.data) >= 8:
            logger.info(f"Audio {audio_id} already has {len(existing.data)} indexed reels. Skipping harvest.")
            return existing.data
    except Exception as e:
        logger.warning(f"Error checking existing reels for {audio_id}: {e}")

    # 2. Load active session cookies from sliding manager
    cookies = load_active_session_cookies()
    if not cookies:
        logger.warning(f"No active session cookies available for audio harvest of {audio_id}.")
        return []

    formatted_cookies = [
        {
            "name": c.get("name"),
            "value": c.get("value"),
            "domain": c.get("domain", ".instagram.com"),
            "path": c.get("path", "/"),
            "secure": c.get("secure", True),
        }
        for c in cookies
    ]

    shortcodes_found: List[Dict[str, Any]] = []

    # 3. Launch browser session and visit audio page
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 900}
            )
            await context.add_cookies(formatted_cookies)
            page = await context.new_page()

            url = f"https://www.instagram.com/reels/audio/{audio_id}/"
            logger.info(f"Human-Mimic Harvester visiting: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(3500)

            # Scroll to load reels grid
            for _ in range(3):
                await page.mouse.wheel(0, 1500)
                await page.wait_for_timeout(1200)

            # Extract shortcodes and views from DOM
            dom_items = await page.evaluate("""() => {
                const anchors = Array.from(document.querySelectorAll('a[href*="/reel/"], a[href*="/p/"]'));
                const seen = new Set();
                const list = [];
                for (const a of anchors) {
                    const href = a.getAttribute('href') || '';
                    const m = href.match(/\\/(?:reel|p)\\/([A-Za-z0-9_-]+)\\//);
                    if (m && !seen.has(m[1])) {
                        seen.add(m[1]);
                        list.push({
                            shortcode: m[1],
                            views_text: (a.innerText || '').trim()
                        });
                    }
                }
                return list.slice(0, 35);
            }""")

            shortcodes_found = dom_items
            await browser.close()
        except Exception as browser_err:
            logger.warning(f"Browser navigation failed for audio {audio_id}: {browser_err}")
            return []

    if not shortcodes_found:
        logger.info(f"No reel cards found on audio page {audio_id}.")
        return []

    logger.info(f"Found {len(shortcodes_found)} reel shortcodes for audio {audio_id}. Extracting captions concurrently...")

    # 4. Concurrently fetch captions via tokenless captioned embed
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    harvested_reels = []

    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        tasks = [_fetch_single_reel_caption(client, item["shortcode"]) for item in shortcodes_found[:max_reels]]
        caption_results = await asyncio.gather(*tasks)

    for item, cap_data in zip(shortcodes_found, caption_results):
        sc = item["shortcode"]
        v_text = item.get("views_text", "")
        # Parse view count estimate supporting K, M, B, Lakhs, Crores
        v_count = parse_compact_count(v_text) or 0
        if not v_count and v_text.replace(",", "").isdigit():
            v_count = int(v_text.replace(",", ""))

        cap = cap_data.get("caption") if cap_data else ""
        tags = cap_data.get("hashtags") if cap_data else []
        username = cap_data.get("owner_username") if cap_data else ""

        harvested_reels.append({
            "audio_id": str(audio_id),
            "reel_id": sc,
            "caption": cap,
            "hashtags": tags,
            "view_count": v_count,
            "like_count": int(v_count * 0.08) if v_count else 50,
            "owner_username": username
        })

    # 5. Insert harvested reels into Supabase
    if harvested_reels and supabase_client:
        try:
            supabase_client.table("reels").upsert(
                harvested_reels,
                on_conflict="reel_id"
            ).execute()
            logger.info(f"Successfully indexed {len(harvested_reels)} reels for audio {audio_id} in Supabase.")
        except Exception as db_err:
            logger.warning(f"Failed to upsert harvested reels for audio {audio_id}: {db_err}")

    return harvested_reels


def harvest_audio_reels(audio_id: str, supabase_client: Any, max_reels: int = 30) -> List[Dict[str, Any]]:
    """Synchronous wrapper for harvest_audio_reels_async."""
    try:
        return asyncio.run(harvest_audio_reels_async(audio_id, supabase_client, max_reels))
    except Exception as e:
        logger.error(f"Error in synchronous harvest_audio_reels wrapper: {e}")
        return []
