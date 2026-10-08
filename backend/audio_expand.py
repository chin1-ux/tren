"""
backend/audio_expand.py
Sighting-Seeded Expansion Job (Order 59 Part D).
- Takes top 10 active watchlist audios by score not expanded in last 12h.
- Derives clean hashtag from audio_title (token before |, (, [, ' - ', ' x ', 'feat', stripped, >=5 chars, not in >1% title stoplist).
- Loads hashtag explore page via Instagram web API / browser cookies.
- Records reels found with matching audio_id, distinct creators, newest posted_at, and share under 72h.
- Updates watchlist.reasons.expansion and recalculates score.
- Max 10 page loads per run, delays 8-20s.
"""

import os
import re
import sys
import time
import json
import random
import logging
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client
from collections import Counter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("audio_expand")

def compute_stop_tokens(sb) -> set[str]:
    try:
        res = sb.table("reels").select("audio_title").not_.is_("audio_title", "null").limit(5000).execute()
        titles = [r["audio_title"] for r in (res.data or []) if r.get("audio_title")]
        total = len(titles)
        if total == 0:
            return {"originalaudio"}
        thresh = total * 0.01
        counts = Counter()
        for t in titles:
            clean = re.sub(r"[^a-z0-9]", "", t.lower())
            if clean:
                counts[clean] += 1
        return {k for k, v in counts.items() if v >= thresh}
    except Exception as e:
        logger.warning(f"Could not compute title stop tokens: {e}")
        return {"originalaudio"}

def derive_hashtag(title: str, stop_tokens: set[str]) -> str | None:
    if not title:
        return None
    # take text before the first of '|', '(', '[', ' - ', ' x ', 'feat'
    pattern = r"(\||\[|\(|\s-\s|\sx\s|\bfeat\b)"
    parts = re.split(pattern, title, flags=re.IGNORECASE)
    base = parts[0].strip().lower()
    clean = re.sub(r"[^a-z0-9]", "", base)
    if len(clean) < 5:
        return None
    if clean in stop_tokens:
        return None
    return clean

def calculate_expanded_score(base_reasons: dict, expansion: dict) -> float:
    # Base score components
    max_v = base_reasons.get("max_velocity", 0.0)
    max_views = base_reasons.get("max_views", 0)
    creators = base_reasons.get("distinct_creators", 0)
    reels_cnt = base_reasons.get("reels_72h", 0)
    growth_pct = base_reasons.get("growth_pct", 0.0)

    # Expansion bonus terms
    exp_creators = expansion.get("expansion_distinct_creators", 0)
    exp_recency_share = expansion.get("recency_share_pct", 0.0) # 0 to 100
    exp_matched_reels = expansion.get("expansion_matched_reels", 0)

    import math
    base_score = (
        (math.log10(max_views + 1) * 15.0)
        + (creators * 20.0)
        + (reels_cnt * 10.0)
        + (min(max_v, 5000.0) * 0.02)
        + (min(growth_pct, 100.0) * 0.5)
    )
    # Expansion bonus: +15 per extra distinct creator discovered, +0.3 per % recency share, +5 per matched reel
    expansion_bonus = (exp_creators * 15.0) + (exp_matched_reels * 5.0) + (exp_recency_share * 0.3)
    return round(base_score + expansion_bonus, 2)

def run_audio_expand():
    load_dotenv("backend/.env")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        logger.error("Supabase credentials not configured.")
        return

    sb = create_client(url, key)
    now_utc = datetime.now(timezone.utc)
    h12_ago = (now_utc - timedelta(hours=12)).isoformat()
    h72_ago = now_utc - timedelta(hours=72)

    # Fetch top active watchlist entries
    wl_res = sb.table("watchlist").select("audio_id, first_reels, first_creators, reasons, status, flagged_at").eq("status", "watching").execute()
    watchlist_entries = wl_res.data or []

    # Filter out entries expanded in last 12h
    candidates = []
    for item in watchlist_entries:
        reasons = item.get("reasons") or {}
        exp = reasons.get("expansion")
        if exp and exp.get("expanded_at") and exp["expanded_at"] >= h12_ago:
            continue
        score = reasons.get("score", 0.0)
        candidates.append((score, item))

    candidates.sort(key=lambda x: x[0], reverse=True)
    targets = [c[1] for c in candidates[:10]] # max 10

    if not targets:
        logger.info("No watchlist audios eligible for expansion in this cycle.")
        return

    logger.info(f"Selected {len(targets)} watchlist audios for sighting-seeded expansion.")

    # Compute stop tokens from database
    stop_tokens = compute_stop_tokens(sb)

    # Fetch titles from reels
    aid_list = [t["audio_id"] for t in targets]
    reels_res = sb.table("reels").select("audio_id, audio_title").in_("audio_id", aid_list).execute()
    title_map = {}
    for r in (reels_res.data or []):
        if r["audio_id"] not in title_map and r.get("audio_title"):
            title_map[r["audio_id"]] = r["audio_title"]

    # Load cookies
    cookies_path = os.path.join(os.path.dirname(__file__), "cookies.json")
    if not os.path.exists(cookies_path):
        cookies_path = "backend/cookies.json"

    cookie_dict = {}
    if os.path.exists(cookies_path):
        with open(cookies_path, "r", encoding="utf-8") as f:
            raw_c = json.load(f)
            cookie_dict = {c["name"]: c["value"] for c in raw_c}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
        "Accept": "*/*",
        "X-IG-App-ID": "936619743392459",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.instagram.com/",
    }

    for idx, target in enumerate(targets):
        aid = target["audio_id"]
        title = title_map.get(aid, "")
        tag = derive_hashtag(title, stop_tokens)

        if not tag:
            logger.info(f"Skipping expansion for audio {aid} ('{title}'): no viable hashtag token.")
            continue

        url = f"https://www.instagram.com/api/v1/tags/web_info/?tag_name={tag}"
        logger.info(f"Expanding audio {aid} ('{title}') via #{tag}...")

        try:
            resp = requests.get(url, headers=headers, cookies=cookie_dict, timeout=15)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                sections = (data.get("top", {}).get("sections", []) + data.get("recent", {}).get("sections", []))

                medias = []
                for sec in sections:
                    for mw in (sec.get("layout_content") or {}).get("medias", []):
                        m = mw.get("media")
                        if m:
                            medias.append(m)

                matching_reels = []
                creators = set()
                recent_reels = 0
                newest_posted = None

                for m in medias:
                    clips = m.get("clips_metadata") or {}
                    music = (clips.get("music_info") or {}).get("music_asset_info") or {}
                    m_aid = str(music.get("audio_cluster_id") or music.get("id") or "")
                    
                    taken_at = m.get("taken_at")
                    dt_taken = datetime.fromtimestamp(taken_at, tz=timezone.utc) if taken_at else None
                    if dt_taken and dt_taken >= h72_ago:
                        recent_reels += 1
                    if dt_taken and (newest_posted is None or dt_taken > newest_posted):
                        newest_posted = dt_taken

                    if m_aid == aid:
                        matching_reels.append(m.get("code"))
                        user = m.get("user") or {}
                        if user.get("username"):
                            creators.add(user["username"])

                total_m = len(medias)
                recency_share = round((recent_reels / total_m * 100.0), 1) if total_m > 0 else 0.0

                expansion_data = {
                    "expanded_at": now_utc.isoformat(),
                    "hashtag": tag,
                    "total_hashtag_medias": total_m,
                    "recency_share_pct": recency_share,
                    "expansion_matched_reels": len(matching_reels),
                    "expansion_distinct_creators": len(creators),
                    "newest_posted_at": newest_posted.isoformat() if newest_posted else None
                }

                # Update reasons and score
                reasons = target.get("reasons") or {}
                reasons["expansion"] = expansion_data
                new_score = calculate_expanded_score(reasons, expansion_data)
                reasons["score"] = new_score

                sb.table("watchlist").update({"reasons": reasons}).eq("audio_id", aid).execute()
                logger.info(f"Audio {aid} expanded: {len(matching_reels)} matched reels, {len(creators)} creators, recency={recency_share}%. New score={new_score:.1f}")

            else:
                logger.warning(f"Hashtag #{tag} fetch returned HTTP {resp.status_code}")

        except Exception as e:
            logger.error(f"Error expanding audio {aid}: {e}")

        if idx < len(targets) - 1:
            time.sleep(random.uniform(8.0, 15.0))

if __name__ == "__main__":
    run_audio_expand()
