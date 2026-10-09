"""
backend/tag_allocator.py
Order 60 Part E: Tag Allocation & Candidate Hashtag Mining (Shadow Mode).
- Evaluates 7-day harvest yield per source_tag in reels
- Mines emergent candidate hashtags from captions (>=3 reels, >=2 creators, <72h)
- Logs dynamic allocation proposal in shadow mode (read-only / advisory)
"""

import os
import re
import sys
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("tag_allocator")

STOP_TAGS = {
    "reels", "reel", "fyp", "foryou", "viral", "explore", "explorepage", "trending", 
    "instagram", "instagood", "love", "like", "share", "follow", "reelsinstagram"
}

def run_tag_allocation():
    load_dotenv("backend/.env")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        logger.error("Supabase credentials not configured.")
        return

    sb = create_client(url, key)
    now_utc = datetime.now(timezone.utc)
    d7_ago = (now_utc - timedelta(days=7)).isoformat()
    h72_ago = (now_utc - timedelta(hours=72)).isoformat()

    print("================================================================================")
    print("               ORDER 60 PART E: TAG ALLOCATION (SHADOW MODE)")
    print("================================================================================\n")

    # 1. Paginate 7-day reels to measure yield per source_tag
    logger.info("Fetching 7-day reels telemetry...")
    tag_stats = defaultdict(lambda: {"reels": 0, "audios": set(), "creators": set()})
    
    # 72h caption mining buckets
    candidate_hashtag_counts = defaultdict(lambda: {"reels": 0, "creators": set(), "audios": set()})

    offset = 0
    PAGE_SIZE = 1000
    total_reels_7d = 0

    while True:
        res = sb.table("reels") \
            .select("source_tag, audio_id, owner_username, caption, created_at") \
            .gte("created_at", d7_ago) \
            .range(offset, offset + PAGE_SIZE - 1) \
            .execute()
        rows = res.data or []
        total_reels_7d += len(rows)

        for r in rows:
            stag = r.get("source_tag") or "untagged"
            aid = r.get("audio_id")
            creator = r.get("owner_username")
            c_at = r.get("created_at")

            tag_stats[stag]["reels"] += 1
            if aid and str(aid) not in ("0", "Unknown"):
                tag_stats[stag]["audios"].add(str(aid))
            if creator:
                tag_stats[stag]["creators"].add(creator)

            # Mine hashtags from 72h captions
            if c_at and c_at >= h72_ago:
                cap = r.get("caption") or ""
                if "#" in cap:
                    found_tags = set(re.findall(r"#([a-zA-Z0-9_]{3,30})", cap.lower()))
                    for ht in found_tags:
                        if ht not in STOP_TAGS and ht != stag.lower():
                            candidate_hashtag_counts[ht]["reels"] += 1
                            if creator:
                                candidate_hashtag_counts[ht]["creators"].add(creator)
                            if aid and str(aid) not in ("0", "Unknown"):
                                candidate_hashtag_counts[ht]["audios"].add(str(aid))

        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    print(f"Total 7-Day Reels Analyzed: {total_reels_7d}\n")
    print("--------------------------------------------------------------------------------")
    print("                    7-DAY YIELD PER SOURCE TAG")
    print("--------------------------------------------------------------------------------")
    print(f"{'Source Tag':<25} | {'Reels':<8} | {'Distinct Audios':<15} | {'Yield (Audios/Reel)':<20} | {'Status'}")
    print("-" * 85)

    sorted_tags = sorted(tag_stats.items(), key=lambda x: len(x[1]["audios"]), reverse=True)
    top_performers = []
    underperformers = []

    for stag, st in sorted_tags:
        r_cnt = st["reels"]
        a_cnt = len(st["audios"])
        yield_ratio = a_cnt / r_cnt if r_cnt > 0 else 0.0

        if yield_ratio >= 0.50 and r_cnt >= 20:
            status = "TOP_PERFORMER"
            top_performers.append(stag)
        elif yield_ratio < 0.25 and r_cnt >= 20:
            status = "LOW_YIELD"
            underperformers.append(stag)
        else:
            status = "STABLE"

        clean_stag = stag.encode("ascii", "replace").decode("ascii")
        print(f"{clean_stag:<25} | {r_cnt:<8} | {a_cnt:<15} | {yield_ratio:<20.2f} | {status}")

    print("\n--------------------------------------------------------------------------------")
    print("        MINED EMERGENT CANDIDATE HASHTAGS (>=3 reels, >=2 creators, <72h)")
    print("--------------------------------------------------------------------------------")
    print(f"{'Candidate Tag':<25} | {'72h Reels':<10} | {'Creators':<10} | {'Distinct Audios':<15} | {'Recommendation'}")
    print("-" * 85)

    viable_candidates = []
    for ht, data in candidate_hashtag_counts.items():
        if data["reels"] >= 3 and len(data["creators"]) >= 2:
            viable_candidates.append((ht, data["reels"], len(data["creators"]), len(data["audios"])))

    viable_candidates.sort(key=lambda x: (x[3], x[1]), reverse=True)

    for ht, r_cnt, c_cnt, a_cnt in viable_candidates[:15]:
        clean_ht = ht.encode("ascii", "replace").decode("ascii")
        print(f"#{clean_ht:<24} | {r_cnt:<10} | {c_cnt:<10} | {a_cnt:<15} | PROPOSE_TRIAL")

    print("\n--------------------------------------------------------------------------------")
    print("                      SHADOW MODE ALLOCATION PROPOSAL")
    print("--------------------------------------------------------------------------------")
    print(f"1. INCREASE ALLOCATION (+20% query weight): {top_performers[:5]}")
    print(f"2. DECREASE / COOLDOWN (-20% query weight): {underperformers[:5]}")
    print(f"3. SHADOW TRIAL ADDITIONS: {[f'#{x[0]}' for x in viable_candidates[:5]]}")
    print("\n================================================================================\n")

if __name__ == "__main__":
    run_tag_allocation()
