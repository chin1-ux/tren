"""
backend/diagnose_miss.py - Order 61 Part F: Miss Diagnosis & Breakout Lead Time Measurement

1. Evaluates the 10 target songs with the unified song_key view (joining split audio IDs).
   Classes: NEVER_SAMPLED, SAMPLED_GATED, SAMPLED_LATE, CAUGHT.
2. Objective Ground Truth Breakout Label:
   audio_count_history reading >= 100,000 OR >= 3x the earliest reading within 72h.
3. --report flag:
   Per day: entries, flagged songs that reached breakout, precision, median lead hours,
   and flagged songs that never broke out.
"""

import os
import sys
import argparse
import statistics
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Set
from dotenv import load_dotenv

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from song_key import compute_song_key, normalize_title, normalize_artist
from supabase import create_client

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


def check_breakout_label(audio_ids: List[str], sb) -> Tuple[bool, Optional[datetime], Optional[int], Optional[str]]:
    """
    Breakout Label (Order 61 Part F1):
    audio_count_history reading >= 100,000 OR >= 3x the earliest reading within 72h.
    Returns: (is_breakout, breakout_time, breakout_count, reason)
    """
    if not audio_ids:
        return False, None, None, None

    res = sb.table("audio_count_history") \
        .select("audio_id, use_count, captured_at") \
        .in_("audio_id", audio_ids) \
        .not_.is_("use_count", "null") \
        .order("captured_at", desc=False) \
        .execute()
    rows = res.data or []
    if not rows:
        return False, None, None, None

    # Check 1: >= 100,000
    for r in rows:
        c = r.get("use_count") or 0
        if c >= 100000:
            dt = datetime.fromisoformat(r["captured_at"].replace("Z", "+00:00"))
            return True, dt, c, "use_count >= 100K"

    # Check 2: >= 3x earliest reading within 72h
    first_dt = datetime.fromisoformat(rows[0]["captured_at"].replace("Z", "+00:00"))
    first_count = rows[0].get("use_count") or 0
    if first_count > 0:
        for r in rows[1:]:
            cur_dt = datetime.fromisoformat(r["captured_at"].replace("Z", "+00:00"))
            cur_count = r.get("use_count") or 0
            if (cur_dt - first_dt).total_seconds() <= 72 * 3600:
                if cur_count >= 3 * first_count:
                    return True, cur_dt, cur_count, f">= 3x in 72h ({first_count} -> {cur_count})"

    return False, None, None, None


def run_diagnose_song_keys(sb):
    """Diagnoses the 10 tracks using the unified song_key view."""
    print("================================================================================")
    print("          ORDER 61 PART F2: MISS DIAGNOSIS (SONG_KEY GROUPED VIEW)")
    print("================================================================================\n")
    print(f"{'Song':<20} | {'Class':<15} | {'Song Key':<30} | {'Reels':<6} | {'Creators':<8} | {'Audio IDs':<10} | {'Trend Status'}")
    print("-" * 115)

    summary_rows = []

    for item in TARGET_SONGS:
        name = item["name"]
        q = item["query"]

        # 1. Fetch matching reels
        reels_res = sb.table("reels") \
            .select("reel_id, audio_id, audio_title, audio_artist, owner_username, like_count, comment_count, view_count, velocity_score, created_at") \
            .ilike("audio_title", f"%{q}%") \
            .order("created_at", desc=False) \
            .execute()
        reels = reels_res.data or []

        # 2. Fetch matching trends
        trends_res = sb.table("trends") \
            .select("id, audio_title, audio_artist, audio_id, status, first_detected_at, peak_velocity") \
            .ilike("audio_title", f"%{q}%") \
            .neq("status", "unqualified") \
            .execute()
        trends = trends_res.data or []

        # Map to song_keys
        s_keys: Set[str] = set()
        a_ids: Set[str] = set()
        creators: Set[str] = set()
        for r in reels:
            sk = compute_song_key(r.get("audio_title"), r.get("audio_artist"))
            if sk:
                s_keys.add(sk)
            if r.get("audio_id"):
                a_ids.add(str(r["audio_id"]))
            if r.get("owner_username"):
                creators.add(r["owner_username"])

        for t in trends:
            sk = compute_song_key(t.get("audio_title"), t.get("audio_artist"))
            if sk:
                s_keys.add(sk)
            if t.get("audio_id"):
                a_ids.add(str(t["audio_id"]))

        primary_sk = list(s_keys)[0] if s_keys else (normalize_title(q) or q)
        earliest_reel = reels[0]["created_at"] if reels else None

        # Classify
        classification = "NEVER_SAMPLED"
        detection_delay_h = None
        trend_status_str = "None"

        if not reels and not trends:
            classification = "NEVER_SAMPLED"
        elif trends:
            trend_status_str = f"id={trends[0]['id']} ({trends[0].get('status')})"
            f_det = trends[0].get("first_detected_at")
            if f_det and earliest_reel:
                t_det = datetime.fromisoformat(f_det.replace("Z", "+00:00"))
                t_reel = datetime.fromisoformat(earliest_reel.replace("Z", "+00:00"))
                detection_delay_h = (t_det - t_reel).total_seconds() / 3600.0
                if detection_delay_h > 48.0:
                    classification = "SAMPLED_LATE"
                else:
                    classification = "CAUGHT"
            else:
                classification = "CAUGHT"
        else:
            # Sampled in reels, but never confirmed as trend
            classification = "SAMPLED_GATED"

        row_info = {
            "name": name,
            "classification": classification,
            "song_key": primary_sk,
            "reels": len(reels),
            "creators": len(creators),
            "audio_ids": len(a_ids),
            "trend_status": trend_status_str,
            "delay_h": detection_delay_h
        }
        summary_rows.append(row_info)
        print(f"{name:<20} | {classification:<15} | {primary_sk:<30} | {len(reels):<6} | {len(creators):<8} | {len(a_ids):<10} | {trend_status_str}")

    print("\nClass Counts Summary:")
    counts = {}
    for r in summary_rows:
        counts[r["classification"]] = counts.get(r["classification"], 0) + 1
    for c_name, cnt in sorted(counts.items()):
        print(f"  {c_name:<16}: {cnt}")
    print()


def run_breakout_report(sb):
    """
    --report mode:
    Per day: entries, flagged songs that reached breakout, precision, median lead hours,
    and flagged songs that never broke out.
    """
    print("================================================================================")
    print("          ORDER 61 PART F1: WATCHLIST BREAKOUT CONVERSION REPORT")
    print("================================================================================\n")

    # Fetch proof_log entries
    pl_res = sb.table("proof_log").select("id, audio_id, flagged_at, reasons, snapshot, run_id").execute()
    pl_rows = pl_res.data or []

    if not pl_rows:
        print("No proof_log entries found in database.")
        return

    # Group by calendar day (UTC)
    by_day: Dict[str, List[Dict[str, Any]]] = {}
    for r in pl_rows:
        f_at = r.get("flagged_at")
        if not f_at:
            continue
        day_str = f_at[:10]
        by_day.setdefault(day_str, []).append(r)

    print(f"{'Date':<12} | {'Entries':<8} | {'Breakouts':<10} | {'Precision':<10} | {'Median Lead (h)':<16} | {'Never Broke Out Songs'}")
    print("-" * 105)

    for day_str in sorted(by_day.keys()):
        day_entries = by_day[day_str]
        entries_cnt = len(day_entries)
        reached_breakout_cnt = 0
        lead_hours_list = []
        never_broke_out_titles = []

        for entry in day_entries:
            aid = entry.get("audio_id")
            f_dt = datetime.fromisoformat(entry["flagged_at"].replace("Z", "+00:00"))
            reasons = entry.get("reasons") or {}
            title = reasons.get("title") or entry.get("snapshot", {}).get("song_key") or aid

            is_bo, bo_dt, bo_cnt, bo_reason = check_breakout_label([aid], sb)
            if is_bo and bo_dt:
                reached_breakout_cnt += 1
                lead_h = max(0.0, (bo_dt - f_dt).total_seconds() / 3600.0)
                lead_hours_list.append(lead_h)
            else:
                never_broke_out_titles.append(title[:25])

        precision = round((reached_breakout_cnt / entries_cnt * 100.0), 1) if entries_cnt > 0 else 0.0
        med_lead = round(statistics.median(lead_hours_list), 1) if lead_hours_list else 0.0
        never_str = ", ".join(never_broke_out_titles[:3])
        if len(never_broke_out_titles) > 3:
            never_str += f" (+{len(never_broke_out_titles)-3} more)"
        if not never_str:
            never_str = "None (100% conversion)"

        print(f"{day_str:<12} | {entries_cnt:<8} | {reached_breakout_cnt:<10} | {precision:<9}% | {med_lead:<16.1f} | {never_str}")

    print("\nBreakout Definition: audio_count_history use_count >= 100K OR >= 3x earliest reading within 72h.")
    print("================================================================================\n")


def main():
    parser = argparse.ArgumentParser(description="Order 61 Part F: Miss Diagnosis & Breakout Report")
    parser.add_argument("--report", action="store_true", help="Generate daily watchlist breakout conversion report")
    args = parser.parse_args()

    load_dotenv(os.path.join(backend_dir, ".env"))
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("Supabase credentials not configured.")
    sb = create_client(url, key)

    if args.report:
        run_breakout_report(sb)
    else:
        run_diagnose_song_keys(sb)


if __name__ == "__main__":
    main()
