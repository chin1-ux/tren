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
    cleaned = re.sub(r"(?i)\s*[\(\[](official\s*(music\s*)?video|audio|lyric\s*video|visualizer|official)[\)\]]", "", raw_title).strip()
    if " - " in cleaned:
        parts = cleaned.split(" - ", 1)
        artist = parts[0].strip()
        title = parts[1].strip()
    else:
        title = cleaned
        artist = channel_title.replace(" - Topic", "").replace("VEVO", "").strip()
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
            title = track.get("title") or "Unknown"
            artist = track.get("subtitle") or "Unknown"
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

    # If Supabase table exists, persist batch
    if sb_client and all_seeded_rows:
        try:
            chunk_size = 200
            for i in range(0, len(all_seeded_rows), chunk_size):
                chunk = all_seeded_rows[i:i + chunk_size]
                sb_client.table("seed_audios").insert(chunk).execute()
            logger.info(f"Successfully persisted {len(all_seeded_rows)} seed tracks into seed_audios.")
        except Exception as persist_err:
            logger.warning(f"seed_audios persistence notice (run migration 008 if table pending): {persist_err}")

    print("\n================ PER-REGION ROW COUNTS ================")
    for region, count in region_counts.items():
        print(f"{region}: {count} tracks")
    print(f"TOTAL: {sum(region_counts.values())} tracks across {len(region_counts)} regions")
    print("=======================================================\n")
    return region_counts

if __name__ == "__main__":
    run_seeding()
