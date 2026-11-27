"""
Algorithmic Feed Harvester (Stream-Based Companion Scraper)
==========================================================
Taps directly into Instagram's live algorithmic recommendation stream (`/reels/`),
intercepting `xdt_api__v1__clips__home__connection_v2` GraphQL responses.

Captures:
- Real-time viral audios served by Meta's recommendation engine (DLRM)
- `is_trending_in_clips` native Meta flag
- Exact view/play counts, like counts, and creator usernames
- Captures zero-hashtag viral trends (e.g., 'I LOVE YOU FUNK', dance challenges, memes)

Safety:
- Isolated companion script (100% preserves golden-scraper-v1.0).
- PostgREST Supabase client only.
- Dry-run mode by default.
"""

import os
import sys
import json
import re
import asyncio
import logging
from datetime import datetime, timezone

# Ensure UTF-8 console output on Windows
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("feed_harvester")


def _media_dict_to_reel(m: dict, source_surface: str = "algorithmic_feed") -> dict | None:
    """Convert an Instagram media dict into our standardized reel dict."""
    if not isinstance(m, dict):
        return None
    reel_code = m.get("code")
    if not reel_code:
        return None

    clips_meta = m.get("clips_metadata") or {}
    if not clips_meta and m.get("media_type") != 2 and not m.get("play_count"):
        return None

    cap = m.get("caption")
    caption_text = cap.get("text", "") if isinstance(cap, dict) else (cap if isinstance(cap, str) else "")
    hashtags = [t.strip("#").lower() for t in re.findall(r"#\w+", caption_text)]

    music_info = clips_meta.get("music_info")
    orig_sound = clips_meta.get("original_sound_info")

    audio_id = None
    audio_title = None
    audio_artist = None
    is_trending = False

    if music_info:
        asset = music_info.get("music_asset_info", {})
        audio_id = asset.get("audio_cluster_id") or asset.get("id")
        audio_title = asset.get("title")
        audio_artist = asset.get("display_artist")
        is_trending = bool(asset.get("is_trending_in_clips"))
    elif orig_sound:
        audio_id = orig_sound.get("audio_asset_id")
        audio_title = orig_sound.get("original_audio_title")
        artist_dict = orig_sound.get("ig_artist") or {}
        audio_artist = artist_dict.get("username") or "Original Audio"
        is_trending = bool(orig_sound.get("is_trending_in_clips"))

    views = int(m.get("play_count") or m.get("view_count") or 0)
    return {
        "reel_id": reel_code,
        "pk": m.get("pk"),
        "owner_username": (m.get("user") or {}).get("username"),
        "owner_follower_count": None,
        "caption": caption_text,
        "hashtags": hashtags,
        "view_count": views,
        "like_count": int(m.get("like_count") or 0),
        "comment_count": int(m.get("comment_count") or 0),
        "audio_id": str(audio_id) if audio_id else None,
        "audio_title": audio_title,
        "audio_artist": audio_artist,
        "is_trending_in_clips": is_trending,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "source_surface": source_surface,
    }


def extract_reels_from_graphql_payload(data: dict, source_surface: str = "algorithmic_feed") -> list[dict]:
    """Recursively extract structured reel metadata from GraphQL/SSR JSON responses."""
    reels = []
    seen = set()

    def _walk(node, depth=0):
        if depth > 14 or not node:
            return
        if isinstance(node, dict):
            if "code" in node and ("clips_metadata" in node or "play_count" in node):
                r = _media_dict_to_reel(node, source_surface=source_surface)
                if r and r["reel_id"] not in seen:
                    seen.add(r["reel_id"])
                    reels.append(r)
            for v in node.values():
                if isinstance(v, (dict, list)):
                    _walk(v, depth + 1)
        elif isinstance(node, list):
            for item in node:
                if isinstance(item, (dict, list)):
                    _walk(item, depth + 1)

    _walk(data)
    return reels


def _load_harvester_cookies() -> list[dict]:
    """Load active session cookies from cookie_sliding_manager, env, or disk."""
    cookies_raw = None
    try:
        from cookie_sliding_manager import load_active_session_cookies
        cookies_raw = load_active_session_cookies()
    except Exception:
        pass

    if not cookies_raw:
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

    if not cookies_raw:
        return []
    return [
        {
            "name": c["name"],
            "value": c["value"],
            "domain": c.get("domain", ".instagram.com"),
            "path": c.get("path", "/"),
        }
        for c in cookies_raw
        if isinstance(c, dict) and "name" in c and "value" in c
    ]


def get_auto_mined_creators(sb, mode: str = "india", run_count: int = 0, limit: int = 3) -> list[str]:
    """
    Auto-mine repeat high-velocity creators from our own Supabase reels table.
    Zero manual curation needed; filters out mega-news/paparazzi repost accounts.
    """
    if not sb or limit <= 0:
        return []
    _exclude = {
        "filmygyan", "instantbollywood", "viralbhayani", "voompla", "pinkvilla",
        "manav.manglani", "bollywoodhungama", "zoomtv", "tseries.official",
    }
    try:
        q = (
            sb.table("reels")
            .select("owner_username, creator_country, velocity_score")
            .not_.is_("owner_username", "null")
            .gt("velocity_score", 1000)
            .order("velocity_score", desc=True)
            .limit(400)
        )
        rows = q.execute().data or []
        from collections import Counter
        counts = Counter()
        for r in rows:
            u = (r.get("owner_username") or "").strip().lower()
            if not u or u in _exclude:
                continue
            cc = (r.get("creator_country") or "").upper()
            if mode == "india" and cc and cc not in ("IN", "INDIA"):
                continue
            if mode == "global" and cc == "IN":
                continue
            counts[u] += 1
        ranked = [u for u, _ in counts.most_common(40)]
        if not ranked:
            return []
        start = (run_count * limit) % len(ranked)
        return [ranked[(start + i) % len(ranked)] for i in range(min(limit, len(ranked)))]
    except Exception as e:
        logger.debug(f"Auto-mined creator lookup skipped: {e}")
        return []


def _extract_ssr_scripts(html: str, source_surface: str) -> list[dict]:
    """Parse Instagram SSR <script type='application/json'> payloads for embedded reels."""
    found = []
    for raw in re.findall(r'<script[^>]+type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.S):
        if "clips_metadata" not in raw and "xdt_api__v1__clips" not in raw:
            continue
        try:
            payload = json.loads(raw)
            found.extend(extract_reels_from_graphql_payload(payload, source_surface=source_surface))
        except Exception:
            pass
    return found


async def harvest_algorithmic_feed(
    scroll_count: int = 5,
    creator_usernames: list[str] | None = None,
) -> list[dict]:
    """
    Use Camoufox stealth browser to harvest:
      1. Instagram's live /reels/ algorithmic stream (SSR HTML + GraphQL XHR)
      2. Optional auto-mined trendsetter creators' /{username}/reels/ tabs
    """
    formatted_cookies = _load_harvester_cookies()
    if not formatted_cookies:
        logger.warning("No Instagram cookies found in session manager/env/disk. Skipping feed harvest.")
        return []

    all_harvested_reels: list[dict] = []
    seen_reel_ids: set[str] = set()
    current_surface = "algorithmic_feed"

    def _collect(items: list[dict]):
        for item in items:
            rid = item.get("reel_id")
            if rid and rid not in seen_reel_ids:
                seen_reel_ids.add(rid)
                all_harvested_reels.append(item)
                logger.info(
                    f"  [INTERCEPTED:{item.get('source_surface')}] Reel {rid} | "
                    f"Sound: '{item.get('audio_title')}' by {item.get('audio_artist')} | "
                    f"Plays: {item.get('view_count', 0):,}"
                )

    async def _run_on_context(ctx):
        page = await ctx.new_page()

        async def handle_response(response):
            if any(k in response.url for k in ("api/graphql", "graphql/query", "api/v1/clips/")):
                try:
                    data = await response.json()
                    _collect(extract_reels_from_graphql_payload(data, source_surface=current_surface))
                except Exception:
                    pass

        page.on("response", handle_response)

        # 1. /reels/ algorithmic stream
        logger.info("Navigating Camoufox to https://www.instagram.com/reels/...")
        await page.goto("https://www.instagram.com/reels/", wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(3500)
        try:
            _collect(_extract_ssr_scripts(await page.content(), current_surface))
        except Exception:
            pass

        for step in range(scroll_count):
            logger.info(f"Advancing /reels/ feed (scroll step {step + 1}/{scroll_count})...")
            try:
                await asyncio.wait_for(page.mouse.wheel(0, 900), timeout=3.0)
                await asyncio.wait_for(page.keyboard.press("ArrowDown"), timeout=3.0)
                await page.wait_for_timeout(2000)
            except Exception as scroll_err:
                logger.warning(f"Scroll step {step + 1} interrupted ({scroll_err}); stopping feed scroll.")
                break

        # 2. Auto-mined creator /reels/ tabs
        for uname in (creator_usernames or []):
            current_surface = f"creator:{uname}"
            try:
                logger.info(f"Checking auto-mined creator @{uname}/reels/...")
                await page.goto(f"https://www.instagram.com/{uname}/reels/", wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(2500)
                _collect(_extract_ssr_scripts(await page.content(), current_surface))
            except Exception as c_err:
                logger.debug(f"Creator @{uname} harvest skipped: {c_err}")

    try:
        from camoufox.async_api import AsyncCamoufox
        logger.info(f"Launching Camoufox for /reels/ ({scroll_count} scrolls) + {len(creator_usernames or [])} auto-mined creators...")
        async with AsyncCamoufox(headless=True) as browser:
            ctx = await browser.new_context(viewport={"width": 1280, "height": 800}, locale="en-US")
            await ctx.add_cookies(formatted_cookies)
            await _run_on_context(ctx)
    except Exception as cam_err:
        logger.warning(f"Camoufox unavailable ({cam_err}); falling back to Playwright Chromium...")
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                locale="en-US",
            )
            await ctx.add_cookies(formatted_cookies)
            await _run_on_context(ctx)
            await browser.close()

    logger.info(f"Harvest complete. Intercepted {len(all_harvested_reels)} unique algorithmic/creator reels.")
    return all_harvested_reels


def save_harvested_reels(sb, reels: list[dict], live=False, mode: str = "india") -> dict:
    """Save newly discovered algorithmic/creator reels into Supabase reels table."""
    if not reels:
        return {"saved": 0, "existing": 0}

    new_saved = 0
    existing = 0

    for r in reels:
        check = sb.table("reels").select("id").eq("reel_id", r["reel_id"]).limit(1).execute()
        if check.data:
            existing += 1
            continue

        if live:
            views = int(r.get("view_count") or 0)
            vel = round(max(1.0, views / 24.0), 3)
            insert_payload = {
                "reel_id": r["reel_id"],
                "audio_id": r["audio_id"],
                "audio_title": r["audio_title"],
                "audio_artist": r["audio_artist"],
                "caption": r["caption"][:1000] if r["caption"] else "",
                "hashtags": r["hashtags"],
                "view_count": views,
                "like_count": r["like_count"],
                "comment_count": r["comment_count"],
                "velocity_score": vel,
                "owner_username": r["owner_username"],
                "scraped_at": r["scraped_at"],
                "source_hashtag_pool": "feed",
                "source_tag": r.get("source_surface") or "algorithmic_feed",
                "creator_country": "IN" if mode == "india" else None,
            }
            try:
                sb.table("reels").insert(insert_payload).execute()
                new_saved += 1
            except Exception as e:
                logger.warning(f"Error saving reel {r['reel_id']}: {e}")
        else:
            new_saved += 1

    return {"saved": new_saved, "existing": existing}


async def main():
    print("=" * 70)
    print("INSTAGRAM ALGORITHMIC FEED HARVESTER (PROTOTYPE)")
    print("=" * 70)

    is_live = "--live" in sys.argv
    scrolls = 4
    for arg in sys.argv:
        if arg.startswith("--scrolls="):
            scrolls = int(arg.split("=")[1])

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    sb = create_client(url, key)

    reels = await harvest_algorithmic_feed(scroll_count=scrolls)

    # Audio aggregation summary
    audios = {}
    trending_audios = []
    zero_hashtag_reels = 0

    for r in reels:
        if not r["hashtags"]:
            zero_hashtag_reels += 1
        aid = r["audio_id"]
        if aid:
            audios.setdefault(aid, {
                "title": r["audio_title"],
                "artist": r["audio_artist"],
                "is_trending": r["is_trending_in_clips"],
                "reels": 0
            })
            audios[aid]["reels"] += 1
            if r["is_trending_in_clips"] and aid not in trending_audios:
                trending_audios.append(aid)

    stats = save_harvested_reels(sb, reels, live=is_live)

    print("\n" + "=" * 70)
    print("HARVEST RESULTS SUMMARY")
    print("=" * 70)
    print(f"Total Unique Reels Intercepted: {len(reels)}")
    print(f"Zero-Hashtag Reels: {zero_hashtag_reels} ({(zero_hashtag_reels/len(reels)*100):.1f}% of feed had ZERO hashtags!)" if reels else "")
    print(f"Distinct Audios Captured: {len(audios)}")
    print(f"Audios Flagged Native Meta Trending: {len(trending_audios)}")
    print(f"Database Ingestion: {stats['saved']} new reels ({'SAVED LIVE' if is_live else 'DRY-RUN'}), {stats['existing']} already existed.")
    print("\nSample Captured Audios:")
    for aid, a in list(audios.items())[:5]:
        print(f"  - '{a['title']}' by {a['artist']} (Trending: {a['is_trending']})")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
