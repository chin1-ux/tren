import os
import sys
import time
import random
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("comment_scraper_pilot")

load_dotenv()
load_dotenv(".env")
load_dotenv("backend/.env")


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def load_cookies():
    # Load cookie headers using same fallback logic
    import json
    cookies_path = "backend/cookies.json"
    if not os.path.exists(cookies_path):
        cookies_path = "cookies.json"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "X-IG-App-ID": "936619743392459",
        "X-Requested-With": "XMLHttpRequest",
    }
    cookies = {}
    try:
        with open(cookies_path, "r", encoding="utf-8") as f:
            raw_cookies = json.load(f)
        for cookie in raw_cookies:
            cookies[cookie["name"]] = cookie["value"]
    except Exception as e:
        logger.error(f"Failed to load cookies: {e}")
    return headers, cookies

def get_top_reels() -> list[dict]:
    # Query 20 high-traffic reels with pk values that are not null
    res = supabase.table("reels").select("reel_id, pk").not_.is_("pk", "null").order("view_count", desc=True).limit(20).execute()
    return res.data or []

def fetch_comments_for_reel(reel_id: str, pk: int | None, headers: dict, cookies: dict) -> list[dict]:
    if not pk:
        logger.warning(f"Reel {reel_id} has no pk stored, skipping comment fetch.")
        return []
    # Convert pk to string formatted representation for url query
    pk_str = str(int(pk))
    url = f"https://www.instagram.com/api/v1/media/{pk_str}/comments/"
    try:
        logger.info(f"Fetching comments for reel {reel_id} using pk: {pk_str}")
        res = requests.get(url, headers=headers, cookies=cookies, timeout=15)
        if res.status_code == 403:
            logger.warning(f"403 Forbidden on reel {reel_id}. Rate-limited or session expired.")
            return []
        res.raise_for_status()
        # Explicitly configure utf-8 encoding on response text
        res.encoding = 'utf-8'
        import json
        data = json.loads(res.text)
        raw_comments = data.get("comments", [])
        logger.info(f"Successfully fetched {len(raw_comments)} comments for reel {reel_id}")
        return raw_comments
    except Exception as e:
        logger.error(f"Error fetching comments for {reel_id}: {e}")
        return []

def run_pilot():
    headers, cookies = load_cookies()
    if not cookies:
        logger.error("No cookies loaded, exiting.")
        return

    reels = get_top_reels()
    logger.info(f"Found {len(reels)} top reels to query comments for.")
    
    total_comments_inserted = 0
    for idx, r in enumerate(reels, 1):
        reel_id = r["reel_id"]
        pk = r.get("pk")
        comments = fetch_comments_for_reel(reel_id, pk, headers, cookies)
        
        to_insert = []
        for c in comments:
            to_insert.append({
                "comment_id": str(c.get("pk")),
                "reel_id": reel_id,
                "text": c.get("text", ""),
                "commenter_username": c.get("user", {}).get("username", "unknown"),
                "created_at": datetime.fromtimestamp(c.get("created_at", time.time())).isoformat() if c.get("created_at") else None
            })
        
        if to_insert:
            try:
                supabase.table("comments").upsert(to_insert).execute()
                total_comments_inserted += len(to_insert)
                logger.info(f"Saved {len(to_insert)} comments to DB.")
            except Exception as e:
                logger.error(f"Failed to save comments to Supabase: {e}")
                
        # Sleep randomly between 2 and 4 seconds
        if idx < len(reels) and pk:
            delay = random.uniform(2.0, 4.0)
            logger.info(f"Sleeping for {delay:.2f} seconds...")
            time.sleep(delay)

    logger.info(f"Pilot execution completed. Total comments inserted: {total_comments_inserted}")

if __name__ == "__main__":
    run_pilot()

