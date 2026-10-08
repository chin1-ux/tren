"""
backend/watchlist.py
Watchlist V2 (Order 58 Part D).
- Excludes audio_id null, '0', 'Unknown', and audios already in trends.
- Scored ranking based on:
  1) max_velocity
  2) max_views
  3) distinct_creators
  4) reels_72h
  5) count growth (>=20%/24h from audio_count_history with exact/K precision)
- Keeps top 30 active per day.
- Logs to proof_log idempotently.
- Summary-level logging.
"""

import os
import sys
import math
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("watchlist")

def evaluate_watchlist():
    load_dotenv("backend/.env")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        logger.error("Supabase credentials not configured.")
        return

    sb = create_client(url, key)
    now_utc = datetime.now(timezone.utc)
    h72_ago = (now_utc - timedelta(hours=72)).isoformat()

    # 1. Fetch audios already in trends
    trends_res = sb.table("trends").select("audio_id").execute()
    trend_audio_ids = set(r["audio_id"] for r in (trends_res.data or []) if r.get("audio_id"))

    # 2. Fetch existing watchlist IDs
    existing_res = sb.table("watchlist").select("audio_id").execute()
    existing_watchlist = set(r["audio_id"] for r in (existing_res.data or []))

    # 3. Fetch candidate reels from last 72 hours
    offset = 0
    PAGE_SIZE = 1000
    audios_reels = {}

    while True:
        res = sb.table("reels") \
            .select("audio_id, audio_title, audio_artist, owner_username, is_original_audio, velocity_score, view_count, created_at") \
            .gte("created_at", h72_ago) \
            .not_.is_("audio_id", "null") \
            .range(offset, offset + PAGE_SIZE - 1) \
            .execute()
        data = res.data or []
        for r in data:
            if r.get("is_original_audio") is True:
                continue
            aid = str(r["audio_id"]).strip()
            if not aid or aid in ("0", "Unknown") or aid in trend_audio_ids:
                continue
            audios_reels.setdefault(aid, []).append(r)

        if len(data) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    # 4. Fetch 24h count history for growth scoring
    h24_ago = (now_utc - timedelta(hours=24)).isoformat()
    history_res = sb.table("audio_count_history") \
        .select("audio_id, use_count, precision, captured_at") \
        .gte("captured_at", h24_ago) \
        .in_("precision", ["exact", "K"]) \
        .order("captured_at", desc=False) \
        .execute()
    history_by_audio = {}
    for h in (history_res.data or []):
        history_by_audio.setdefault(h["audio_id"], []).append(h)

    scored_candidates = []
    for aid, r_list in audios_reels.items():
        creators = set(r["owner_username"] for r in r_list if r.get("owner_username"))
        reels_cnt = len(r_list)
        if reels_cnt < 2 and len(creators) < 2:
            continue

        max_v = max((r.get("velocity_score") or 0.0 for r in r_list), default=0.0)
        max_views = max((r.get("view_count") or 0 for r in r_list), default=0)

        # Check growth
        growth_pct = 0.0
        h_entries = history_by_audio.get(aid, [])
        if len(h_entries) >= 2:
            first_c = h_entries[0]["use_count"]
            last_c = h_entries[-1]["use_count"]
            if first_c and last_c and first_c > 0:
                growth_pct = max(0.0, ((last_c - first_c) / first_c) * 100.0)

        # Score formula
        score = (math.log10(max_views + 1) * 15.0) + (len(creators) * 20.0) + (reels_cnt * 10.0) + (min(max_v, 5000.0) * 0.02) + (min(growth_pct, 100.0) * 0.5)

        reasons = {
            "score": round(score, 2),
            "max_velocity": round(max_v, 2),
            "max_views": max_views,
            "distinct_creators": len(creators),
            "reels_72h": reels_cnt,
            "growth_pct": round(growth_pct, 2)
        }

        scored_candidates.append({
            "audio_id": aid,
            "first_reels": reels_cnt,
            "first_creators": len(creators),
            "reasons": reasons,
            "score": score,
            "title": r_list[0].get("audio_title"),
            "artist": r_list[0].get("audio_artist"),
            "snapshot": {
                "rule": "watchlist_v2_ranked",
                "score": round(score, 2),
                "creators": list(creators)[:5],
                "sample_reels": [r.get("reel_id") for r in r_list[:3]]
            }
        })

    scored_candidates.sort(key=lambda x: x["score"], reverse=True)
    top_30 = scored_candidates[:30]

    logger.info(f"Watchlist evaluation complete: {len(scored_candidates)} eligible -> top {len(top_30)} selected")

    # Insert into watchlist & proof_log
    for cand in top_30:
        aid = cand["audio_id"]
        if aid not in existing_watchlist:
            try:
                sb.table("watchlist").upsert({
                    "audio_id": aid,
                    "flagged_at": now_utc.isoformat(),
                    "first_reels": cand["first_reels"],
                    "first_creators": cand["first_creators"],
                    "reasons": cand["reasons"],
                    "status": "watching"
                }).execute()
                sb.table("proof_log").insert({
                    "audio_id": aid,
                    "flagged_at": now_utc.isoformat(),
                    "reasons": cand["reasons"],
                    "snapshot": cand["snapshot"]
                }).execute()
                logger.info(f"Watchlist flagged: {aid} (Score: {cand['score']:.1f})")
            except Exception as e:
                logger.warning(f"Error persisting watchlist entry {aid}: {e}")

if __name__ == "__main__":
    evaluate_watchlist()
