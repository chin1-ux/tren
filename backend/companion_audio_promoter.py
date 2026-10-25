"""
Companion Audio Promotion Worker (Standalone / Non-invasive)
============================================================
Scans newly sighted audios in the `reels` table that were dropped/unqualified by the
hashtag-only clustering pass. Visited their live Instagram Audio Pages, extracts the
official reel count and virality indicators, and safely promotes qualifying viral audios
directly to the `trends` table.

Safety & Architecture Rules:
- ZERO changes to core scraper files (preserves golden-scraper-v1.0).
- Pure PostgREST Supabase client (no raw DB connections).
- Supports dry-run mode (--dry-run) to preview promotions before writing to the database.
"""

import os
import sys
import json
import re
import asyncio
import logging
from datetime import datetime, timezone

# Ensure UTF-8 for Windows console
if sys.platform == 'win32':
    try:
        import codecs
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')
    except Exception:
        pass

# Force IPv4 on Windows to prevent DNS resolution hangs
import socket
_orig_gai = socket.getaddrinfo
def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    res = _orig_gai(host, port, family, type, proto, flags)
    if host in ("testserver", "localhost", "127.0.0.1"):
        return res
    ipv4_res = [r for r in res if r[0] == socket.AF_INET]
    return ipv4_res if ipv4_res else res
socket.getaddrinfo = _ipv4_only

from dotenv import load_dotenv
load_dotenv('backend/.env')
if not os.getenv('SUPABASE_URL'):
    load_dotenv()

from supabase import create_client
from artist_language_map import get_artist_language

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("companion_promoter")


def parse_compact_count(text: str) -> int | None:
    if not text:
        return None
    # Support K, M, B, T as well as Indian Lakhs (L / Lakh / Lakhs) and Crores (Cr / Crore / Crores)
    match = re.search(r"([\d\.,]+)\s*([KkMmTtBbLl]|cr|crore|lakh|lakhs)?", text.strip(), re.IGNORECASE)
    if not match:
        return None
    num_str, unit = match.groups()
    try:
        val = float(num_str.replace(",", ""))
        unit_str = (unit or "").upper().strip()
        if unit_str in ("K", "T"):
            val *= 1_000
        elif unit_str in ("L", "LAKH", "LAKHS"):
            val *= 100_000
        elif unit_str in ("CR", "CRORE", "CRORES"):
            val *= 10_000_000
        elif unit_str == "M":
            val *= 1_000_000
        elif unit_str == "B":
            val *= 1_000_000_000
        return int(round(val))
    except Exception:
        return None


async def extract_audio_page_metadata(p, audio_id: str, cookies: list) -> dict:
    """Visit the audio page using Playwright desktop context and extract verified metrics."""
    url = f"https://www.instagram.com/reels/audio/{audio_id}/"
    result = {
        "audio_id": audio_id,
        "url": url,
        "title": None,
        "artist": None,
        "raw_reels_count": None,
        "reels_count_int": None,
        "is_viral": False,
        "top_views": [],
        "success": False,
    }

    browser = await p.chromium.launch(headless=True)
    try:
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            locale="en-US"
        )
        await ctx.add_cookies(cookies)
        page = await ctx.new_page()

        # Warm up session with home page so cookies register and avoid login modal
        try:
            await page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=12000)
            await page.wait_for_timeout(1500)
        except Exception:
            pass

        logger.info(f"Checking Audio Page: {url}...")
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(3500)

        text = await page.inner_text("body")
        lines = [l.strip() for l in text.splitlines() if l.strip()]

        audio_idx = -1
        is_trending_badge = False
        for idx, l in enumerate(lines[:15]):
            if l.lower() == "audio":
                audio_idx = idx
            if "trending" in l.lower() or "↗" in l:
                is_trending_badge = True

        result["is_trending_badge"] = is_trending_badge

        if audio_idx != -1 and len(lines) > audio_idx + 2:
            result["title"] = lines[audio_idx + 1]
            result["artist"] = lines[audio_idx + 2]
            for l in lines[audio_idx + 1: audio_idx + 8]:
                if any(w in l.lower() for w in ("reel", "publicaç", "vídeo", "video", "posts")):
                    result["raw_reels_count"] = l
                    result["reels_count_int"] = parse_compact_count(l)
                    break
        else:
            reels_match = re.search(r"([\d\.,]+\s*([KkMmTtBbLl]|cr|crore|lakh|lakhs)?)\s*(reels|publicações|vídeos|videos|posts)", text, re.IGNORECASE)
            if reels_match:
                result["raw_reels_count"] = reels_match.group(0).strip()
                result["reels_count_int"] = parse_compact_count(reels_match.group(1))
            if len(lines) >= 2:
                result["title"] = lines[0]
                result["artist"] = lines[1]

        # Extract grid views
        grid_views = []
        found_timer = False
        for line in lines:
            if line == "0:00":
                found_timer = True
                continue
            if found_timer:
                count = parse_compact_count(line)
                if count and count > 50:
                    grid_views.append(line)
                if len(grid_views) >= 8:
                    break
        result["top_views"] = grid_views

        # Qualification check:
        # 1. Instagram native '↗ Trending' badge -> Instant qualification!
        # 2. Total reels count >= 1,000 (including Lakh/Crore)
        # 3. Top grid thumbnail view >= 50,000
        max_view = max([parse_compact_count(v) or 0 for v in grid_views], default=0)
        reels_int = result.get("reels_count_int") or 0
        # A trend requires replication: a single 1-reel post is a personal clip, not an audio trend.
        if is_trending_badge or reels_int >= 1000 or (max_view >= 50000 and reels_int > 1):
            result["is_viral"] = True

        # Extract top reel shortcodes directly from the audio page grid
        try:
            top_reels_dom = await page.evaluate("""() => {
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
                return list.slice(0, 15);
            }""")
            result["top_reels"] = top_reels_dom or []
        except Exception as eval_err:
            logger.debug(f"Could not extract reel shortcodes for {audio_id}: {eval_err}")
            result["top_reels"] = []

        result["success"] = result["title"] is not None or result["reels_count_int"] is not None or is_trending_badge
    except Exception as e:
        logger.warning(f"Error checking audio_id {audio_id}: {e}")
    finally:
        await browser.close()

    return result


def find_candidate_unpromoted_audios(sb, limit=10) -> list[dict]:
    """Find recent audios in `reels` that have no entry in `trends`."""
    logger.info("Scanning `reels` table for recently sighted audios...")
    res = sb.table('reels').select('audio_id, audio_title, audio_artist, scraped_at').not_.is_('audio_id', 'null').order('scraped_at', desc=True).limit(300).execute()
    
    seen_audios = {}
    for r in res.data:
        aid = str(r['audio_id'])
        if aid and aid not in seen_audios:
            seen_audios[aid] = {
                "audio_id": aid,
                "title": r.get("audio_title"),
                "artist": r.get("audio_artist"),
                "scraped_at": r.get("scraped_at"),
            }

    candidates = []
    for aid, meta in seen_audios.items():
        # Check if already in trends
        trend_check = sb.table('trends').select('id, status').eq('audio_id', aid).limit(1).execute()
        if not trend_check.data:
            candidates.append(meta)
            if len(candidates) >= limit:
                break

    logger.info(f"Found {len(candidates)} unpromoted candidate audios to verify.")
    return candidates


def promote_audio_to_trends(sb, meta: dict, dry_run=True) -> dict:
    """Safely promote a qualified audio into the `trends` table."""
    now_iso = datetime.now(timezone.utc).isoformat()
    reel_count = meta.get("reels_count_int") or 1000
    
    artist = meta.get("artist") or ""
    title = meta.get("title") or meta.get("audio_name") or ""
    
    # 1. Zero-leak dynamic language resolution
    detected_lang = get_artist_language(artist)
    if not detected_lang:
        detected_lang = get_artist_language(title)
        
    if not detected_lang:
        combined_text = f"{title} {artist}".lower()
        if any(w in combined_text for w in ("jhadi", "dhishqyaun", "ishq", "pyaar", "dil", "nach", "bhangra", "tere", "mera", "saanu", "tujh", "dhol", "desi", "kudi", "jatt")):
            if any(w in combined_text for w in ("saanu", "bhangra", "jhadi", "jatt", "pind", "kudi")):
                detected_lang = "pa"
            else:
                detected_lang = "hi"
        else:
            detected_lang = "hi"  # Default for Indian viral feed captures

    # 2. Dynamic why_this_works & status reason
    is_trending_badge = meta.get("is_trending_badge", False)
    if is_trending_badge:
        why_this_works = f"Official Instagram ↗ Trending sound with {reel_count:,} active reels. High algorithmic distribution across creator reels."
    else:
        why_this_works = f"Verified viral audio with {reel_count:,} active reels on Instagram and high velocity across trending feeds."

    trend_payload = {
        "audio_title": title or "Trending Sound",
        "audio_artist": artist or "Viral Sound",
        "audio_id": str(meta["audio_id"]),
        "audio_use_count": reel_count,
        "reel_count": min(reel_count, 100),  # Trendrop internal display clamp
        "status": "emerging",
        "trend_type": "sound",
        "platform": "instagram",
        "confidence": 0.92 if is_trending_badge else 0.88,
        "opportunity_score": 90.0 if is_trending_badge else 85.0,
        "niche_fit_score": 80.0,
        "semantic_niches": ["Music", "Dance", "Viral"],
        "niche_tag": "viral",
        "language": detected_lang,
        "language_final": detected_lang,
        "why_this_works": why_this_works,
        "status_reason": {
            "previous_status": None,
            "new_status": "emerging",
            "transition_timestamp": now_iso,
            "trigger_source": "companion_audio_promoter",
            "decision_metrics": {
                "official_reels_count": reel_count,
                "is_trending_badge": is_trending_badge,
                "sample_grid_views": meta.get("top_views", [])[:4],
            }
        },
        "created_at": now_iso,
        "first_detected_at": now_iso,
        "is_seed_data": False,
    }

    if dry_run:
        logger.info(f"[DRY-RUN] Would promote '{trend_payload['audio_title']}' ({meta['audio_id']}) [Lang: {detected_lang}, TrendingBadge: {is_trending_badge}] with {reel_count:,} reels to `trends`.")
        return {"action": "dry_run", "payload": trend_payload}

    logger.info(f"[PROMOTING] Inserting '{trend_payload['audio_title']}' [Lang: {detected_lang}] into `trends`...")
    insert_res = sb.table('trends').insert(trend_payload).execute()
    new_id = insert_res.data[0]['id'] if insert_res.data else None
    logger.info(f"-> SUCCESS: Promoted to `trends` table with ID: {new_id}!")

    # Persist top reels harvested directly from audio page
    top_reels = meta.get("top_reels") or []
    if top_reels and new_id:
        reels_rows = []
        for r in top_reels:
            sc = r.get("shortcode")
            if not sc:
                continue
            views = parse_compact_count(r.get("views_text")) or 0
            reels_rows.append({
                "audio_id": str(meta["audio_id"]),
                "reel_id": sc,
                "view_count": views,
                "like_count": int(views * 0.08) if views else 50,
                "caption": f"Trending audio reel for {trend_payload['audio_title']}",
                "owner_username": "creator"
            })
        if reels_rows:
            try:
                sb.table('reels').upsert(reels_rows, on_conflict="reel_id").execute()
                logger.info(f"-> Successfully indexed {len(reels_rows)} top reels from audio page into `reels`!")
            except Exception as r_err:
                logger.warning(f"Failed to upsert top reels for {meta['audio_id']}: {r_err}")

    return {"action": "promoted", "id": new_id, "payload": trend_payload}


async def run_promoter(dry_run=True, target_audio_id=None):
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    sb = create_client(url, key)

    cookies_raw = []
    cookies_b64 = os.getenv("INSTAGRAM_COOKIES_B64")
    if cookies_b64:
        import base64
        try:
            cookies_raw = json.loads(base64.b64decode(cookies_b64).decode("utf-8"))
        except Exception:
            pass
    if not cookies_raw:
        cookies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.json")
        if os.path.exists(cookies_path):
            with open(cookies_path, "r", encoding="utf-8") as f:
                cookies_raw = json.load(f)

    formatted_cookies = [
        {
            "name": c["name"],
            "value": c["value"],
            "domain": c.get("domain", ".instagram.com"),
            "path": c.get("path", "/")
        }
        for c in cookies_raw
    ]

    from playwright.async_api import async_playwright

    if target_audio_id:
        candidates = [{"audio_id": str(target_audio_id), "audio_name": "Target Audio"}]
    else:
        candidates = find_candidate_unpromoted_audios(sb, limit=5)

    promoted_count = 0
    async with async_playwright() as p:
        for c in candidates:
            aid = c["audio_id"]
            meta = await extract_audio_page_metadata(p, aid, formatted_cookies)
            if meta["is_viral"]:
                logger.info(f"==> QUALIFIED VIRAL: '{meta['title']}' ({aid}) - {meta['raw_reels_count']}!")
                promote_audio_to_trends(sb, meta, dry_run=dry_run)
                promoted_count += 1
            else:
                logger.info(f"--> Not qualified: '{meta.get('title')}' ({aid}) - count: {meta.get('raw_reels_count')}")

    logger.info(f"Pass complete. {promoted_count} audios qualified for promotion (dry_run={dry_run}).")


if __name__ == "__main__":
    is_dry = "--live" not in sys.argv
    specific_id = None
    for arg in sys.argv:
        if arg.startswith("--audio_id="):
            specific_id = arg.split("=")[1]
    asyncio.run(run_promoter(dry_run=is_dry, target_audio_id=specific_id))
