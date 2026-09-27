import os
import sys
import logging
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Set, Tuple
from dotenv import load_dotenv

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

load_dotenv(os.path.join(backend_dir, ".env"))

from supabase import create_client, Client
from audio_title_normalize import normalize_audio_title

logger = logging.getLogger("spotify_search_ingester")

def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    return create_client(url, key)

def get_spotify_token() -> str:
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ValueError("SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET missing in environment")

    res = requests.post(
        "https://accounts.spotify.com/api/token",
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
        timeout=10
    )
    res.raise_for_status()
    return res.json()["access_token"]

def make_canonical_key(title: str, artist: str) -> Tuple[str, str]:
    norm_t = normalize_audio_title(title or "").lower().strip()
    primary_a = (artist or "").split(",")[0].split("&")[0].split("feat")[0].lower().strip()
    return (norm_t, primary_a)

def fetch_spotify_search_tracks(token: str, limit_per_query: int = 50) -> List[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    tracks = []
    seen_spotify_ids: Set[str] = set()

    search_queries = [
        "tag:new year:2025-2026",
        "year:2025-2026",
        "tag:new",
        "remix year:2025-2026",
        "speed up year:2025-2026",
        "viral year:2025-2026",
        "bollywood year:2025-2026",
        "punjabi year:2025-2026",
        "telugu year:2025-2026",
        "tamil year:2025-2026"
    ]

    for q in search_queries:
        for offset in [0, 10, 20, 30, 40]:
            try:
                res = requests.get(
                    "https://api.spotify.com/v1/search",
                    headers=headers,
                    params={"q": q, "type": "track", "market": "IN", "limit": 10, "offset": offset},
                    timeout=12
                )
                if not res.ok:
                    logger.warning(f"Spotify search failed for query '{q}' offset {offset}: {res.status_code}")
                    continue

                items = res.json().get("tracks", {}).get("items", []) or []
                for item in items:
                    if not item:
                        continue
                    sid = item.get("id")
                    if not sid or sid in seen_spotify_ids:
                        continue
                    seen_spotify_ids.add(sid)

                    album = item.get("album") or {}
                    rel_date = album.get("release_date") or ""
                    rel_year = int(rel_date.split("-")[0]) if rel_date and rel_date.split("-")[0].isdigit() else None
                    artists_str = ", ".join([a.get("name") for a in item.get("artists", []) if a.get("name")])
                    
                    images = album.get("images") or []
                    image_url = images[0].get("url") if images else None
                    spotify_url = item.get("external_urls", {}).get("spotify") or f"https://open.spotify.com/track/{sid}"

                    tracks.append({
                        "spotify_id": sid,
                        "title": item.get("name") or "",
                        "artist": artists_str,
                        "album_name": album.get("name"),
                        "release_date": rel_date,
                        "release_year": rel_year,
                        "preview_url": item.get("preview_url"),
                        "image_url": image_url,
                        "spotify_url": spotify_url
                    })
            except Exception as e:
                logger.warning(f"Error during Spotify search for '{q}' offset {offset}: {e}")

    logger.info(f"Fetched {len(tracks)} fresh tracks via Spotify /v1/search API.")
    return tracks

def populate_spotify_feed_cache() -> Dict[str, Any]:
    sb = get_supabase()
    token = get_spotify_token()

    # 1. Fetch search tracks from Spotify
    raw_tracks = fetch_spotify_search_tracks(token)
    if not raw_tracks:
        logger.warning("No search tracks returned from Spotify.")
        return {"fetched": 0, "inserted": 0, "excluded_trends": 0}

    # 2. Fetch existing trends from 'trends' table for exclusion
    res_trends = sb.table("trends").select("audio_title, audio_artist").execute()
    existing_trends = res_trends.data or []

    trend_keys: Set[Tuple[str, str]] = set()
    for t in existing_trends:
        ckey = make_canonical_key(t.get("audio_title"), t.get("audio_artist"))
        if ckey[0]:
            trend_keys.add(ckey)

    # 3. Fetch reels from the last 7 days for Instagram spotting match
    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    res_reels = sb.table("reels").select("audio_title, audio_artist").gte("scraped_at", seven_days_ago).execute()
    reels_data = res_reels.data or []

    reels_count_map: Dict[Tuple[str, str], int] = {}
    for r in reels_data:
        rkey = make_canonical_key(r.get("audio_title"), r.get("audio_artist"))
        if rkey[0]:
            reels_count_map[rkey] = reels_count_map.get(rkey, 0) + 1

    # 4. Filter out existing trends & tag Instagram matches
    cache_payloads = []
    excluded_count = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    for track in raw_tracks:
        ckey = make_canonical_key(track["title"], track["artist"])
        
        # Exclude if already in trends table
        if ckey in trend_keys:
            excluded_count += 1
            continue

        ig_count = reels_count_map.get(ckey, 0)
        is_spotted = ig_count > 0

        cache_payloads.append({
            "spotify_id": track["spotify_id"],
            "title": track["title"],
            "artist": track["artist"],
            "audio_title": track["title"],
            "audio_artist": track["artist"],
            "album_name": track["album_name"],
            "release_date": track["release_date"],
            "release_year": track["release_year"],
            "preview_url": track["preview_url"],
            "image_url": track["image_url"],
            "spotify_url": track["spotify_url"],
            "popularity": track.get("popularity", 0),
            "data_source": "spotify_search",
            "is_spotted_on_instagram": is_spotted,
            "ig_reel_count": ig_count,
            "updated_at": now_iso
        })

    logger.info(f"Evaluated {len(raw_tracks)} search tracks: {excluded_count} excluded (already in trends), {len(cache_payloads)} queued for spotify_feed_cache.")

    # 5. Write into spotify_feed_cache (try upsert, fallback to select/insert/update)
    inserted_count = 0
    chunk_size = 50
    for i in range(0, len(cache_payloads), chunk_size):
        chunk = cache_payloads[i:i + chunk_size]
        try:
            sb.table("spotify_feed_cache").upsert(chunk, on_conflict="spotify_id").execute()
            inserted_count += len(chunk)
        except Exception as e:
            logger.warning(f"Batch upsert fallback mode triggered for chunk {i}: {e}")
            for item in chunk:
                try:
                    # Check if row exists by spotify_id
                    existing = sb.table("spotify_feed_cache").select("id").eq("spotify_id", item["spotify_id"]).execute()
                    if existing.data and len(existing.data) > 0:
                        sb.table("spotify_feed_cache").update(item).eq("spotify_id", item["spotify_id"]).execute()
                    else:
                        sb.table("spotify_feed_cache").insert(item).execute()
                    inserted_count += 1
                except Exception as row_err:
                    logger.error(f"Failed to save spotify_feed_cache item {item.get('spotify_id')}: {row_err}")

    logger.info(f"spotify_feed_cache population complete. Inserted/Updated: {inserted_count} rows.")
    return {
        "fetched": len(raw_tracks),
        "excluded_trends": excluded_count,
        "inserted": inserted_count
    }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = populate_spotify_feed_cache()
    print("Population Summary:", res)
