"""
backend/diagnose_miss.py
Order 60 Part D: Miss Diagnosis & Detection Delay Analysis.
Analyzes why target tracks were missed or caught late, and evaluates
14-day detection delays across all detected trends.
"""

import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("diagnose_miss")

TARGET_SONGS = [
    {"name": "Khalouni Neich", "query": "khalouni"},
    {"name": "Hideaway", "query": "hideaway"},
    {"name": "12 Ladke", "query": "12 ladke"},
    {"name": "Chadariya Jhini", "query": "chadariya"},
    {"name": "Tauba Tauba", "query": "tauba tauba"},
    {"name": "Big Dawgs", "query": "big dawgs"},
    {"name": "Sahiba", "query": "sahiba"},
    {"name": "Millionaire", "query": "millionaire"},
    {"name": "Aayi Nai", "query": "aayi nai"},
    {"name": "Illuminati", "query": "illuminati"},
]

def run_diagnose():
    load_dotenv("backend/.env")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        logger.error("Supabase credentials not configured.")
        return

    sb = create_client(url, key)
    now_utc = datetime.now(timezone.utc)

    print("================================================================================")
    print("                     ORDER 60 PART D: MISS DIAGNOSIS")
    print("================================================================================\n")

    # 1. Diagnose the 10 Target Tracks
    for item in TARGET_SONGS:
        name = item["name"]
        q = item["query"]

        # Search in reels
        reels_res = sb.table("reels") \
            .select("reel_id, audio_id, audio_title, owner_username, like_count, comment_count, view_count, velocity_score, created_at") \
            .ilike("audio_title", f"%{q}%") \
            .order("created_at", desc=False) \
            .execute()
        reels = reels_res.data or []

        # Search in trends
        trends_res = sb.table("trends") \
            .select("id, audio_title, audio_id, status, first_detected_at, peak_velocity") \
            .ilike("audio_title", f"%{q}%") \
            .execute()
        trends = trends_res.data or []

        total_reels = len(reels)
        distinct_creators = len(set(r.get("owner_username") for r in reels if r.get("owner_username")))
        audio_ids = list(set(r.get("audio_id") for r in reels if r.get("audio_id")))

        # Check gate conditions on reels
        earliest_reel = reels[0]["created_at"] if reels else None
        latest_reel = reels[-1]["created_at"] if reels else None

        has_engagement_pass = False
        time_span_hours = 0.0
        if reels:
            has_engagement_pass = any(
                (r.get("like_count") or 0) >= 10 or 
                (r.get("comment_count") or 0) >= 2 or 
                (r.get("view_count") or 0) >= 5000 
                for r in reels
            )
            t0 = datetime.fromisoformat(earliest_reel.replace("Z", "+00:00"))
            t1 = datetime.fromisoformat(latest_reel.replace("Z", "+00:00"))
            time_span_hours = (t1 - t0).total_seconds() / 3600.0

        # Classification
        classification = "NEVER_SAMPLED"
        detection_delay_hours = None

        if not reels and not trends:
            classification = "NEVER_SAMPLED"
        elif trends:
            first_detected = trends[0].get("first_detected_at")
            if first_detected and earliest_reel:
                t_det = datetime.fromisoformat(first_detected.replace("Z", "+00:00"))
                t_reel = datetime.fromisoformat(earliest_reel.replace("Z", "+00:00"))
                detection_delay_hours = round((t_det - t_reel).total_seconds() / 3600.0, 1)
                if detection_delay_hours > 48.0:
                    classification = "SAMPLED_LATE"
                else:
                    classification = "CAUGHT"
            else:
                classification = "CAUGHT"
        else:
            # Sampled but not in trends
            classification = "SAMPLED_GATED"

        print(f"TRACK: {name} (Query: '{q}')")
        print(f"  Classification   : {classification}")
        print(f"  Total Reels      : {total_reels}")
        print(f"  Distinct Creators: {distinct_creators}")
        print(f"  Audio IDs        : {audio_ids[:3]}")
        print(f"  Earliest Reel    : {earliest_reel}")
        print(f"  Latest Reel      : {latest_reel} (Span: {time_span_hours:.1f}h)")
        print(f"  Engagement Gate  : {'PASS' if has_engagement_pass else 'FAIL'}")
        if trends:
            print(f"  Trend ID / Status: {trends[0]['id']} / {trends[0].get('status')}")
            print(f"  First Detected At: {trends[0].get('first_detected_at')}")
            print(f"  Detection Delay  : {detection_delay_hours} hours")
        else:
            print(f"  In Trends Table  : NO")
        print()

    # 2. 14-Day Detection Delay Distribution
    print("--------------------------------------------------------------------------------")
    print("           14-DAY DETECTION DELAY DISTRIBUTION (ALL CAUGHT TRENDS)")
    print("--------------------------------------------------------------------------------")
    d14_ago = (now_utc - timedelta(days=14)).isoformat()
    trends_14d_res = sb.table("trends") \
        .select("id, audio_title, audio_id, first_detected_at") \
        .gte("first_detected_at", d14_ago) \
        .order("first_detected_at", desc=False) \
        .execute()
    trends_14d = trends_14d_res.data or []

    delays = []
    trend_delays = []

    for t in trends_14d:
        aid = t.get("audio_id")
        f_det = t.get("first_detected_at")
        if not aid or not f_det:
            continue
        # Find earliest reel for this audio
        r_res = sb.table("reels").select("created_at").eq("audio_id", aid).order("created_at", desc=False).limit(1).execute()
        r_data = r_res.data or []
        if r_data and r_data[0].get("created_at"):
            t_det = datetime.fromisoformat(f_det.replace("Z", "+00:00"))
            t_reel = datetime.fromisoformat(r_data[0]["created_at"].replace("Z", "+00:00"))
            delay_h = max(0.0, (t_det - t_reel).total_seconds() / 3600.0)
            delays.append(delay_h)
            trend_delays.append((delay_h, t.get("audio_title") or "Unknown", aid, f_det, r_data[0]["created_at"]))

    if delays:
        delays.sort()
        n = len(delays)
        p25 = delays[int(n * 0.25)]
        median = delays[int(n * 0.50)]
        p75 = delays[int(n * 0.75)]

        print(f"Total Evaluated Trends (14d): {n}")
        print(f"  P25 Detection Delay       : {p25:.1f} hours")
        print(f"  Median Detection Delay    : {median:.1f} hours")
        print(f"  P75 Detection Delay       : {p75:.1f} hours\n")

        trend_delays.sort(key=lambda x: x[0], reverse=True)
        print("TOP 10 SLOWEST DETECTIONS:")
        for idx, (dh, tname, aid, tdet, treel) in enumerate(trend_delays[:10]):
            clean_name = tname.encode("ascii", "replace").decode("ascii")
            print(f"  {idx+1}. {clean_name} (Audio {aid}): {dh:.1f}h delay (First Reel: {treel[:16]} -> Detected: {tdet[:16]})")
    else:
        print("No trends with linked reels found in 14d window.")
    print("\n================================================================================\n")

if __name__ == "__main__":
    run_diagnose()
