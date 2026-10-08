import os
import re
import sys
import socket
import logging
from datetime import datetime, timezone
import requests
import urllib3.util.connection as connection
from dotenv import load_dotenv

# Force IPv4 to prevent Windows socket hangs
connection.allowed_gai_family = lambda: socket.AF_INET

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("seed_charts")

REGIONS = ["SA", "AE", "EG", "BR", "MX", "KR", "JP", "ID", "TR", "NG", "ZA", "US", "GB", "IN"]


def clean_title_and_artist(raw_title: str, channel_title: str) -> tuple[str, str]:
    """
    Clean titles per Order 52 specs:
    Strip text after '|', brackets, 'official', 'video', 'lyrics', years.
    """
    cleaned = raw_title
    # Strip text after '|'
    if "|" in cleaned:
        cleaned = cleaned.split("|")[0].strip()
    # Strip brackets () and []
    cleaned = re.sub(r'\(.*?\)|\[.*?\]', '', cleaned).strip()
    # Strip year numbers
    cleaned = re.sub(r'\b(19\d\d|20\d\d)\b', '', cleaned).strip()
    # Strip common video/audio suffixes
    cleaned = re.sub(r"(?i)\s*\b(official\s*(music\s*)?video|audio|lyric\s*video|visualizer|lyrics|lyric|official|video|remix|hd|4k)\b", "", cleaned).strip()

    if " - " in cleaned:
        parts = cleaned.split(" - ", 1)
        artist = parts[0].strip()
        title = parts[1].strip()
    else:
        title = cleaned
        artist = channel_title.replace(" - Topic", "").replace("VEVO", "").strip()

    title = " ".join(title.split())
    artist = " ".join(artist.split())
    return title, artist


def fetch_youtube_charts_for_region(region: str, api_key: str, max_results: int = 50) -> list[dict]:
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet",
        "chart": "mostPopular",
        "regionCode": region,
        "videoCategoryId": "10",  # Music
        "maxResults": max_results,
        "key": api_key,
    }
    resp = requests.get(url, params=params, timeout=15)
    if not resp.ok:
        logger.warning(f"YouTube API returned HTTP {resp.status_code} for region {region}: {resp.text[:120]}")
        return []

    data = resp.json()
    items = data.get("items", [])
    now_utc = datetime.now(timezone.utc).isoformat()
    rows = []
    for rank, item in enumerate(items, 1):
        snippet = item.get("snippet", {})
        raw_title = snippet.get("title", "")
        channel_title = snippet.get("channelTitle", "")
        title, artist = clean_title_and_artist(raw_title, channel_title)
        rows.append({
            "source": "youtube",
            "region": region,
            "rank": rank,
            "title": title,
            "artist": artist,
            "fetched_at": now_utc,
        })
    return rows


async def fetch_shazam_charts_for_region(region: str, limit: int = 50) -> list[dict]:
    try:
        from shazamio import Shazam
        shazam = Shazam()
        data = await shazam.top_country_tracks(country_code=region, limit=limit)
        tracks = data.get("tracks", [])
        now_utc = datetime.now(timezone.utc).isoformat()
        rows = []
        for rank, track in enumerate(tracks, 1):
            raw_title = track.get("title") or "Unknown"
            raw_artist = track.get("subtitle") or "Unknown"
            title, artist = clean_title_and_artist(raw_title, raw_artist)
            rows.append({
                "source": "shazam",
                "region": region,
                "rank": rank,
                "title": title,
                "artist": artist,
                "fetched_at": now_utc,
            })
        return rows
    except Exception as e:
        logger.debug(f"Shazam chart lookup unavailable for region {region}: {e}")
        return []


def run_seeding():
    load_dotenv("backend/.env")
    load_dotenv()

    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        logger.error("YOUTUBE_API_KEY environment variable not configured.")
        return {}

    sb_url = os.getenv("SUPABASE_URL")
    sb_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    sb_client = None
    if sb_url and sb_key:
        try:
            from supabase import create_client
            sb_client = create_client(sb_url, sb_key)
        except Exception as e:
            logger.warning(f"Could not initialize Supabase client: {e}")

    region_counts: dict[str, int] = {}
    all_seeded_rows = []

    logger.info(f"Starting external chart seeding across {len(REGIONS)} regions...")
    for region in REGIONS:
        yt_rows = fetch_youtube_charts_for_region(region, api_key)
        region_counts[region] = len(yt_rows)
        all_seeded_rows.extend(yt_rows)
        logger.info(f"Region [{region}]: fetched {len(yt_rows)} tracks from YouTube Music")

    # Idempotent persistence into Supabase
    if sb_client and all_seeded_rows:
        try:
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            # Query existing seeds fetched today to guarantee idempotency
            existing_res = sb_client.table("seed_audios") \
                .select("source, region, rank") \
                .gte("fetched_at", f"{today_str}T00:00:00") \
                .execute()
            existing_keys = {(r["source"], r["region"], r["rank"]) for r in (existing_res.data or [])}

            new_rows = [r for r in all_seeded_rows if (r["source"], r["region"], r["rank"]) not in existing_keys]
            if new_rows:
                chunk_size = 200
                for i in range(0, len(new_rows), chunk_size):
                    chunk = new_rows[i:i + chunk_size]
                    sb_client.table("seed_audios").insert(chunk).execute()
                logger.info(f"Successfully persisted {len(new_rows)} new seed tracks (skipped {len(all_seeded_rows) - len(new_rows)} already seeded today).")
            else:
                logger.info(f"All {len(all_seeded_rows)} seed tracks already present for {today_str}. Idempotent no-op.")
        except Exception as persist_err:
            logger.warning(f"seed_audios persistence notice: {persist_err}")

    print("\n================ PER-REGION ROW COUNTS ================")
    for region, count in region_counts.items():
        print(f"{region}: {count} tracks")
    print(f"TOTAL: {sum(region_counts.values())} tracks across {len(region_counts)} regions")
    print("=======================================================\n")
    return region_counts


if __name__ == "__main__":
    run_seeding()
