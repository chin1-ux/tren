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


def extract_reels_from_graphql_payload(data: dict) -> list[dict]:
    """Extract structured reel metadata from an intercepted GraphQL response."""
    reels = []
    if not isinstance(data, dict):
        return reels

    # Check connection_v2 or generic edges
    connection = (
        data.get("data", {}).get("xdt_api__v1__clips__home__connection_v2")
        or data.get("data", {}).get("xdt_api__v1__clips__home__connection")
    )
    edges = connection.get("edges", []) if connection else []

    for edge in edges:
        m = edge.get("node", {}).get("media") or {}
        if not m:
            continue

        reel_code = m.get("code")
        if not reel_code:
            continue

        cap = m.get("caption")
        caption_text = cap.get("text", "") if isinstance(cap, dict) else ""

        # Extract hashtags from caption
        hashtags = [t.strip("#").lower() for t in re.findall(r"#\w+", caption_text)]

        # Extract audio information
        clips_meta = m.get("clips_metadata") or {}
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

        reel_obj = {
            "reel_id": reel_code,
            "pk": m.get("pk"),
            "owner_username": (m.get("user") or {}).get("username"),
            "owner_follower_count": None,
            "caption": caption_text,
            "hashtags": hashtags,
            "view_count": m.get("play_count") or m.get("view_count") or 0,
            "like_count": m.get("like_count") or 0,
            "comment_count": m.get("comment_count") or 0,
            "audio_id": str(audio_id) if audio_id else None,
            "audio_title": audio_title,
            "audio_artist": audio_artist,
            "is_trending_in_clips": is_trending,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "source_surface": "algorithmic_feed",
        }
        reels.append(reel_obj)

    return reels


async def harvest_algorithmic_feed(scroll_count: int = 5) -> list[dict]:
    """Scroll through Instagram Reels feed and harvest intercepted items."""
    cookies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.json")
    if not os.path.exists(cookies_path):
        raise FileNotFoundError(f"cookies.json not found at {cookies_path}")

    with open(cookies_path, "r", encoding="utf-8") as f:
        cookies_raw = json.load(f)

    formatted_cookies = [
        {
            "name": c["name"],
            "value": c["value"],
            "domain": c.get("domain", ".instagram.com"),
            "path": c.get("path", "/"),
        }
        for c in cookies_raw
    ]

    from playwright.async_api import async_playwright

    all_harvested_reels = []
    seen_reel_ids = set()

    logger.info(f"Launching Playwright to harvest {scroll_count} scrolls from /reels/...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            locale="en-US"
        )
        await ctx.add_cookies(formatted_cookies)
        page = await ctx.new_page()

        async def handle_response(response):
            if "graphql/query" in response.url or "api/v1/clips/home" in response.url:
                try:
                    data = await response.json()
                    new_items = extract_reels_from_graphql_payload(data)
                    for item in new_items:
                        if item["reel_id"] not in seen_reel_ids:
                            seen_reel_ids.add(item["reel_id"])
                            all_harvested_reels.append(item)
                            logger.info(
                                f"  [INTERCEPTED] Reel {item['reel_id']} | "
                                f"Sound: '{item['audio_title']}' by {item['audio_artist']} | "
                                f"Plays: {item['view_count']:,} | Trending: {item['is_trending_in_clips']}"
                            )
                except Exception:
                    pass

        page.on("response", handle_response)

        logger.info("Navigating to https://www.instagram.com/reels/...")
        await page.goto("https://www.instagram.com/reels/", wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(3500)

        for step in range(scroll_count):
            logger.info(f"Advancing feed (scroll step {step + 1}/{scroll_count})...")
            await page.keyboard.press("PageDown")
            # Natural human viewing pause (2.5 - 4 seconds)
            await page.wait_for_timeout(3000)

        await browser.close()

    logger.info(f"Harvest complete. Intercepted {len(all_harvested_reels)} unique algorithmic reels.")
    return all_harvested_reels


def save_harvested_reels(sb, reels: list[dict], live=False) -> dict:
    """Save newly discovered algorithmic reels into Supabase reels table."""
    if not reels:
        return {"saved": 0, "existing": 0}

    new_saved = 0
    existing = 0

    for r in reels:
        # Check if reel already exists in reels table
        check = sb.table("reels").select("id").eq("reel_id", r["reel_id"]).limit(1).execute()
        if check.data:
            existing += 1
            continue

        if live:
            insert_payload = {
                "reel_id": r["reel_id"],
                "audio_id": r["audio_id"],
                "audio_title": r["audio_title"],
                "audio_artist": r["audio_artist"],
                "caption": r["caption"][:1000] if r["caption"] else "",
                "hashtags": r["hashtags"],
                "view_count": r["view_count"],
                "like_count": r["like_count"],
                "comment_count": r["comment_count"],
                "owner_username": r["owner_username"],
                "scraped_at": r["scraped_at"],
                "source_hashtag_pool": "ALGORITHMIC_FEED",
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
