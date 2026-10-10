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
import re
import argparse
import statistics
import random
import asyncio
import json
import base64
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
from dotenv import load_dotenv

try:
    from camoufox.async_api import AsyncCamoufox
except ImportError:
    AsyncCamoufox = None

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

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


def trend_for_song(song_key: str, audio_ids: Optional[List[str]] = None, trends_cache: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
    """
    Order 65 Part 3.2: Match trends by audio_id OR compute_song_key(audio_title, audio_artist).
    """
    if not trends_cache:
        return None
    aids = set(str(a) for a in (audio_ids or []) if a)
    for t in trends_cache:
        t_aid = str(t.get("audio_id") or "")
        if t_aid and t_aid in aids:
            return t
    if song_key:
        for t in trends_cache:
            t_sk = t.get("song_key") or compute_song_key(t.get("audio_title"), t.get("audio_artist"))
            if t_sk and t_sk == song_key:
                return t
    return None


def run_song_level_trends_report(sb):
    """
    Order 65 Part 3.2:
    Recompute for the last 14 days:
    - flagged watchlist songs
    - share with a song-level trend row
    - lead hours (flag time vs trends.first_detected_at)
    - 20 flagged songs with no song-level trend (title, creators, reels, max views, audio_ids)
    """
    print("================================================================================")
    print("      ORDER 65 PART 3.2: SONG-LEVEL TREND MATCHING (LAST 14 DAYS)")
    print("================================================================================\n")

    # Fetch active trends
    t_res = sb.table("trends").select("id, audio_id, audio_title, audio_artist, status, first_detected_at").neq("status", "unqualified").execute()
    all_trends = t_res.data or []
    for t in all_trends:
        t["song_key"] = compute_song_key(t.get("audio_title"), t.get("audio_artist"))

    # Fetch proof_log (14 days)
    now_utc = datetime.now(timezone.utc)
    d14_ago = (now_utc - timedelta(days=14)).isoformat()
    pl_res = sb.table("proof_log").select("id, audio_id, flagged_at, reasons, snapshot, run_id").gte("flagged_at", d14_ago).order("flagged_at", desc=False).execute()
    proof_rows = pl_res.data or []

    total_flagged = len(proof_rows)
    matched_songs = []
    unmatched_songs = []
    lead_hours_list = []

    matched_details = []
    for p in proof_rows:
        reasons = p.get("reasons") or {}
        sk = reasons.get("song_key") or p.get("snapshot", {}).get("song_key")
        if not sk:
            sk = compute_song_key(reasons.get("title"), reasons.get("artist"))
        aids = reasons.get("audio_ids") or ([str(p["audio_id"])] if p.get("audio_id") else [])

        t = trend_for_song(sk, aids, all_trends)
        f_at = p.get("flagged_at")

        if t:
            t_dt = t.get("first_detected_at")
            lead_h = 0.0
            if t_dt and f_at:
                f_datetime = datetime.fromisoformat(f_at.replace("Z", "+00:00"))
                if not f_datetime.tzinfo:
                    f_datetime = f_datetime.replace(tzinfo=timezone.utc)
                t_datetime = datetime.fromisoformat(t_dt.replace("Z", "+00:00"))
                if not t_datetime.tzinfo:
                    t_datetime = t_datetime.replace(tzinfo=timezone.utc)
                # Sign convention: positive hours = flagged before the trend (lead), negative = flagged after (lag)
                lead_h = (t_datetime - f_datetime).total_seconds() / 3600.0
                lead_hours_list.append(lead_h)
            matched_songs.append((p, t))
            matched_details.append((p, t, lead_h))
        else:
            title = reasons.get("title")
            artist = reasons.get("artist")
            creators = reasons.get("distinct_creators") or 0
            reels_cnt = reasons.get("total_reels") or 0
            max_v = reasons.get("max_views") or 0
            if (not title or creators == 0) and aids:
                try:
                    r_res = sb.table("reels").select("audio_title, audio_artist, owner_username, view_count").in_("audio_id", aids).execute()
                    r_data = r_res.data or []
                    if r_data:
                        if not title:
                            title = r_data[0].get("audio_title") or sk
                        if not artist:
                            artist = r_data[0].get("audio_artist")
                        if creators == 0:
                            creators = len({x.get("owner_username") for x in r_data if x.get("owner_username")})
                        if reels_cnt == 0:
                            reels_cnt = len(r_data)
                        if max_v == 0:
                            max_v = max([x.get("view_count") or 0 for x in r_data] or [0])
                except Exception:
                    pass

            unmatched_songs.append({
                "title": title or sk or p.get("audio_id"),
                "artist": artist,
                "creators": creators,
                "reels": reels_cnt,
                "max_views": max_v,
                "audio_ids": aids,
            })

    share_with_trend = (len(matched_songs) / total_flagged * 100.0) if total_flagged else 0.0
    med_lead = statistics.median(lead_hours_list) if lead_hours_list else 0.0
    mean_lead = statistics.mean(lead_hours_list) if lead_hours_list else 0.0

    print(f"Total flagged watchlist songs (14d): {total_flagged}")
    print(f"Share with song-level trend row: {len(matched_songs)}/{total_flagged} ({share_with_trend:.1f}%)")
    print(f"Lead hours (trends.first_detected_at - flag_time): Median={med_lead:.1f}h, Mean={mean_lead:.1f}h\n")

    print(f"--- MATCHED SONGS WITH TRENDS ({len(matched_details)}) ---")
    print(f"{'Title':<30} | {'Flagged At':<22} | {'First Detected At':<22} | {'Lead (h)'}")
    print("-" * 88)
    for p, t, lead_h in matched_details:
        f_str = str(p.get('flagged_at', ''))[:19]
        t_str = str(t.get('first_detected_at', ''))[:19]
        t_name = str(p.get('reasons', {}).get('title') or t.get('audio_title') or '')[:28]
        sign_str = f"+{lead_h:.1f}h" if lead_h >= 0 else f"{lead_h:.1f}h"
        print(f"{t_name:<30} | {f_str:<22} | {t_str:<22} | {sign_str}")

    print(f"\n--- 20 FLAGGED SONGS WITH NO SONG-LEVEL TREND ---")
    print(f"{'Title':<30} | {'Creators':<8} | {'Reels':<6} | {'Max Views':<10} | {'Audio IDs'}")
    print("-" * 88)
    for u in unmatched_songs[:20]:
        t_str = str(u['title'])[:28]
        aids_str = ",".join(str(a) for a in u['audio_ids'][:2])
        print(f"{t_str:<30} | {u['creators']:<8} | {u['reels']:<6} | {u['max_views']:<10} | {aids_str}")
    print("================================================================================\n")


def run_scoreboard(sb):
    """
    Order 65 Part 6.1 & Order 66 Part 5.2:
    --scoreboard: per day, flagged songs, breakout label, lead hours,
    breakouts with no prior flag, number of readings available.
    - No interpolation.
    - Breakout requires >= 2 real audio_count_history readings.
    """
    print("================================================================================")
    print("                ORDER 66 PART 5.2: DETECTION SCOREBOARD")
    print("================================================================================\n")

    now_utc = datetime.now(timezone.utc)
    d14_ago = (now_utc - timedelta(days=14)).isoformat()

    # Load proof_log
    pl_res = sb.table("proof_log").select("id, audio_id, flagged_at, reasons, snapshot, run_id").gte("flagged_at", d14_ago).order("flagged_at", desc=False).execute()
    proof_rows = pl_res.data or []

    # Load audio_count_history
    ach_res = sb.table("audio_count_history").select("audio_id, use_count, precision, captured_at").gte("captured_at", d14_ago).order("captured_at", desc=False).execute()
    ach_rows = ach_res.data or []

    history_by_aid: Dict[str, List[Dict[str, Any]]] = {}
    readings_by_day: Dict[str, int] = {}
    for r in ach_rows:
        aid = str(r["audio_id"])
        history_by_aid.setdefault(aid, []).append(r)
        d_str = r["captured_at"][:10]
        readings_by_day[d_str] = readings_by_day.get(d_str, 0) + 1

    # Breakout label: Requires >= 2 real audio_count_history readings
    breakouts_by_aid: Dict[str, Tuple[datetime, int, str]] = {}
    for aid, h_list in history_by_aid.items():
        if len(h_list) < 2:
            continue
        first_dt = datetime.fromisoformat(h_list[0]["captured_at"].replace("Z", "+00:00"))
        first_c = h_list[0].get("use_count") or 0
        for row in h_list[1:]:
            cnt = row.get("use_count") or 0
            dt = datetime.fromisoformat(row["captured_at"].replace("Z", "+00:00"))
            if cnt >= 100000:
                if aid not in breakouts_by_aid or dt < breakouts_by_aid[aid][0]:
                    breakouts_by_aid[aid] = (dt, cnt, ">=100K")
            if first_c > 0 and (dt - first_dt).total_seconds() <= 72 * 3600:
                if cnt >= 3 * first_c:
                    if aid not in breakouts_by_aid or dt < breakouts_by_aid[aid][0]:
                        breakouts_by_aid[aid] = (dt, cnt, ">=3x in 72h")

    proof_by_day: Dict[str, List[Dict[str, Any]]] = {}
    all_flagged_aids: Set[str] = set()
    for p in proof_rows:
        d_str = p["flagged_at"][:10]
        proof_by_day.setdefault(d_str, []).append(p)
        reasons = p.get("reasons") or {}
        for a in (reasons.get("audio_ids") or [str(p["audio_id"])]):
            all_flagged_aids.add(str(a))

    all_days = sorted(set(list(proof_by_day.keys()) + list(readings_by_day.keys())))
    print(f"{'Date':<12} | {'Flagged':<8} | {'Breakouts':<10} | {'Median Lead (h)':<16} | {'Unflagged Breakouts':<20} | {'Readings Available'}")
    print("-" * 95)
    for d in all_days:
        day_flags = proof_by_day.get(d, [])
        flagged_cnt = len(day_flags)
        day_breakouts = 0
        lead_list = []
        for p in day_flags:
            reasons = p.get("reasons") or {}
            aids = reasons.get("audio_ids") or [str(p["audio_id"])]
            for a in aids:
                if str(a) in breakouts_by_aid:
                    b_dt, b_cnt, b_r = breakouts_by_aid[str(a)]
                    f_dt = datetime.fromisoformat(p["flagged_at"].replace("Z", "+00:00"))
                    day_breakouts += 1
                    lead_list.append((b_dt - f_dt).total_seconds() / 3600.0)
                    break

        med_l = f"{statistics.median(lead_list):+.1f}h" if lead_list else "N/A"

        unflagged_bo = 0
        for aid, (b_dt, b_cnt, b_r) in breakouts_by_aid.items():
            b_d = b_dt.strftime("%Y-%m-%d")
            if b_d == d and aid not in all_flagged_aids:
                unflagged_bo += 1

        readings_cnt = readings_by_day.get(d, 0)
        # Order 68 Part 2.3: Breakout requires >=2 real audio_count_history readings. If 0 readings, breakouts must be 0 / N/A.
        if readings_cnt == 0:
            day_breakouts = 0
            med_l = "N/A"
            unflagged_bo = 0

        print(f"{d:<12} | {flagged_cnt:<8} | {day_breakouts:<10} | {med_l:<16} | {unflagged_bo:<20} | {readings_cnt}")

    print("\n* Note on numbers: Readings on 2026-10-09/10 represent new initial baseline captures (<24h history).")
    print("  Growth-based breakouts (>=3x in 72h) will become meaningful once >=72h of continuous CI captures accumulate.")
    print("================================================================================\n")
    run_groundtruth_report(sb)


def run_groundtruth_report(sb):
    """
    Order 68 Part 4.2: Ground truth audit from DB values.
    Classes: NEVER_SAMPLED | SAMPLED_NOT_FLAGGED | FLAGGED_NO_TREND | FLAGGED_THEN_TREND | TREND_THEN_FLAGGED | CAUGHT_FIRST_BY_TREND
    """
    print("================================================================================")
    print("                ORDER 68 PART 4.2: GROUND TRUTH AUDIT")
    print("================================================================================\n")

    def parse_dt(s):
        if not s:
            return None
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    gt_rows = sb.table("ground_truth").select("*").order("id", desc=False).execute().data or []
    if not gt_rows:
        print("No ground truth rows found in database.")
        return

    pl_res = sb.table("proof_log").select("flagged_at, run_id, audio_id, snapshot").execute()
    all_proof = pl_res.data or []

    classes = {}
    print(f"{'Song':<22} | {'Class':<22} | {'Reels':<5} | {'Creators':<8} | {'Max Views':<10} | {'Trend Status':<24} | {'Lead'}")
    print("-" * 105)

    for g in gt_rows:
        title = g.get("title") or ""
        artist = g.get("artist") or ""
        sk = g.get("song_key") or compute_song_key(title, artist)
        q_title = title.split("/")[0].strip()

        q_token = q_title.split()[0] if q_title else ""
        norm_t = (normalize_title(title) or "").strip()

        r_query = sb.table("reels").select("id, audio_id, owner_username, view_count, posted_at, created_at, audio_title, audio_artist, scraped_at")
        if q_token:
            r_query = r_query.ilike("audio_title", f"%{q_token}%")
        all_reels_raw = r_query.execute().data or []
        
        reels = []
        for r in all_reels_raw:
            r_title = r.get("audio_title") or ""
            r_artist = r.get("audio_artist") or ""
            r_sk = compute_song_key(r_title, r_artist)
            r_norm = (normalize_title(r_title) or "").strip()
            if (sk and r_sk == sk) or (norm_t and r_norm and (norm_t == r_norm or norm_t in r_norm or r_norm in norm_t)):
                reels.append(r)

        aids = list({str(r["audio_id"]) for r in reels if r.get("audio_id")})
        creators = list({r["owner_username"] for r in reels if r.get("owner_username")})
        scraped_dates = sorted([r.get("scraped_at") or r.get("created_at") for r in reels if r.get("scraped_at") or r.get("created_at")])
        first_scraped = scraped_dates[0][:16] if scraped_dates else "None"
        last_scraped = scraped_dates[-1][:16] if scraped_dates else "None"
        scrape_range = f"{first_scraped}..{last_scraped}" if scraped_dates else "None"

        # Match trends by audio_id OR song_key OR normalized title
        t_query = sb.table("trends").select("id, status, first_detected_at, audio_title, audio_artist, audio_id")
        if q_token:
            t_query = t_query.ilike("audio_title", f"%{q_token}%")
        all_trends_raw = t_query.execute().data or []
        trends = []
        for tr in all_trends_raw:
            tr_aid = str(tr.get("audio_id") or "")
            tr_title = tr.get("audio_title") or ""
            tr_artist = tr.get("audio_artist") or ""
            tr_sk = compute_song_key(tr_title, tr_artist)
            tr_norm = (normalize_title(tr_title) or "").strip()
            if (tr_aid and tr_aid in aids) or (sk and tr_sk == sk) or (norm_t and tr_norm and (norm_t == tr_norm or norm_t in tr_norm or tr_norm in norm_t)):
                trends.append(tr)

        matched_pl = []
        for p in all_proof:
            p_sk = (p.get("snapshot") or {}).get("song_key")
            p_aid = str(p.get("audio_id") or "")
            if (sk and p_sk == sk) or (p_aid and p_aid in aids):
                matched_pl.append(p)

        t_first = trends[0].get("first_detected_at") if trends else None
        p_first = matched_pl[0].get("flagged_at") if matched_pl else None
        lead_h = "N/A"

        if not reels and not trends:
            cls = "NEVER_SAMPLED"
        elif trends:
            if matched_pl:
                t_dt = parse_dt(t_first)
                p_dt = parse_dt(p_first)
                lead_val = (t_dt - p_dt).total_seconds() / 3600.0
                lead_h = f"{lead_val:+.1f}h"
                cls = "FLAGGED_THEN_TREND" if lead_val >= 0 else "TREND_THEN_FLAGGED"
            else:
                cls = "CAUGHT_FIRST_BY_TREND"
        else: # no trend
            if matched_pl:
                cls = "FLAGGED_NO_TREND"
            else:
                cls = "SAMPLED_NOT_FLAGGED"

        classes[cls] = classes.get(cls, 0) + 1
        tid = trends[0]["id"] if trends else 0
        tst = trends[0].get("status") if trends else ""
        t_det = trends[0].get("first_detected_at")[:16] if trends and trends[0].get("first_detected_at") else ""
        t_info = f"#{tid} ({tst}, {t_det})" if trends else "None"
        pl_info = f"{matched_pl[0]['flagged_at'][:16]} (run:{matched_pl[0].get('run_id')})" if matched_pl else "None"
        aids_str = ",".join(aids[:2]) + (f"(+{len(aids)-2})" if len(aids) > 2 else "") if aids else "None"

        print(f"\n[{title}] by [{artist or 'NULL'}]")
        print(f"  Class       : {cls} (Lead: {lead_h})")
        print(f"  Audio IDs   : {aids_str}")
        print(f"  Reels/Creat.: {len(reels)} reels / {len(creators)} creators")
        print(f"  Scraped At  : {scrape_range}")
        print(f"  Trend       : {t_info}")
        print(f"  Proof Log   : {pl_info}")

    print("\n" + "=" * 80)
    print("Summary Counts per Class:")
    for c, cnt in sorted(classes.items()):
        print(f"  {c:<24}: {cnt}")
    print("================================================================================\n")


def run_coverage_report(sb):
    """
    Order 70 Part 6: Coverage measurement pipeline.
    (a) Ground truth recall for songs older than 72h
    (b) Breakout recall from audio_count_history
    (c) Out-of-pool coverage from 6 random caption-mined tags
    """
    import asyncio
    from camoufox.async_api import AsyncCamoufox

    now = datetime.now(timezone.utc)
    week_start = (now - timedelta(days=now.weekday())).date().isoformat()

    def parse_dt(s):
        if not s:
            return None
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    print("=" * 80)
    print("             COVERAGE MEASUREMENT PIPELINE (ORDER 70 PART 6)")
    print("=" * 80)

    # (a) Ground Truth Recall
    print("\n--- (a) GROUND TRUTH RECALL ---")
    gt_rows = sb.table("ground_truth").select("*").order("id", desc=False).execute().data or []
    pl_res = sb.table("proof_log").select("flagged_at, audio_id, snapshot").execute()
    all_proof = pl_res.data or []

    cutoff_72h = (now - timedelta(hours=72)).date().isoformat()
    eligible_gt = [g for g in gt_rows if g.get("first_noticed") and g.get("first_noticed") <= cutoff_72h]
    n_gt = len(eligible_gt)
    print(f"Total ground truth songs: {len(gt_rows)}, older than 72h: {n_gt}")

    before_cnt = 0
    within_72h_cnt = 0
    missed_cnt = 0

    for g in eligible_gt:
        title = g.get("title") or ""
        artist = g.get("artist") or ""
        sk = g.get("song_key") or compute_song_key(title, artist)
        q_token = title.split("/")[0].strip().split()[0] if title else ""
        norm_t = (normalize_title(title) or "").strip()
        fn_str = g.get("first_noticed")
        reported_dt = datetime.fromisoformat(f"{fn_str}T00:00:00+00:00")

        t_query = sb.table("trends").select("id, status, first_detected_at, audio_title, audio_artist, audio_id")
        if q_token:
            t_query = t_query.ilike("audio_title", f"%{q_token}%")
        trends = []
        for tr in (t_query.execute().data or []):
            tr_aid = str(tr.get("audio_id") or "")
            tr_title = tr.get("audio_title") or ""
            tr_artist = tr.get("audio_artist") or ""
            tr_sk = compute_song_key(tr_title, tr_artist)
            tr_norm = (normalize_title(tr_title) or "").strip()
            if (sk and tr_sk == sk) or (norm_t and tr_norm and (norm_t == tr_norm or norm_t in tr_norm or tr_norm in norm_t)):
                trends.append(tr)

        matched_pl = []
        for p in all_proof:
            p_sk = (p.get("snapshot") or {}).get("song_key")
            if sk and p_sk == sk:
                matched_pl.append(p)

        first_t = parse_dt(trends[0]["first_detected_at"]) if trends and trends[0].get("first_detected_at") else None
        first_p = parse_dt(matched_pl[0]["flagged_at"]) if matched_pl and matched_pl[0].get("flagged_at") else None

        detection_candidates = [d for d in [first_t, first_p] if d is not None]
        if not detection_candidates:
            missed_cnt += 1
            status = "MISSED"
        else:
            earliest_d = min(detection_candidates)
            if earliest_d < reported_dt:
                before_cnt += 1
                status = f"BEFORE ({earliest_d.isoformat()[:10]} < {fn_str})"
            elif earliest_d <= reported_dt + timedelta(hours=72):
                within_72h_cnt += 1
                status = f"WITHIN_72H ({earliest_d.isoformat()[:10]})"
            else:
                missed_cnt += 1
                status = f"MISSED (caught later at {earliest_d.isoformat()[:10]})"
        print(f"  {title:<22} | Reported: {fn_str} | Result: {status}")

    share_before = (before_cnt / n_gt) if n_gt > 0 else 0.0
    share_within_72h = (within_72h_cnt / n_gt) if n_gt > 0 else 0.0
    share_missed = (missed_cnt / n_gt) if n_gt > 0 else 0.0

    print(f"Ground Truth Recall: Before: {share_before:.1%} ({before_cnt}/{n_gt}) | Within 72h: {share_within_72h:.1%} ({within_72h_cnt}/{n_gt}) | Missed: {share_missed:.1%} ({missed_cnt}/{n_gt})")

    # (b) Breakout Recall (Order 71 Part B1)
    print("\n--- (b) BREAKOUT RECALL (survivorship-biased, strict 3x in 72h, base >= 1000) ---")
    ach_res = sb.table("audio_count_history").select("audio_id, use_count, captured_at").order("captured_at", desc=False).limit(3000).execute()
    by_aid = {}
    for r in (ach_res.data or []):
        aid = str(r["audio_id"])
        by_aid.setdefault(aid, []).append(r)

    breakouts = []
    for aid, hist in by_aid.items():
        if len(hist) < 2:
            continue
        hist_sorted = sorted(hist, key=lambda x: parse_dt(x["captured_at"]))
        f_dt = parse_dt(hist_sorted[0]["captured_at"])
        f_c = hist_sorted[0].get("use_count") or 0
        if f_c < 1000:
            continue  # Initial reading must be >= 1000
        for r in hist_sorted[1:]:
            cur_dt = parse_dt(r["captured_at"])
            cur_c = r.get("use_count") or 0
            if (cur_dt - f_dt).total_seconds() <= 72 * 3600 and cur_c >= 3 * f_c:
                breakouts.append((aid, cur_dt, cur_c, f">=3x ({f_c}->{cur_c})"))
                break

    n_bo = len(breakouts)
    print(f"Total breakout audios found: {n_bo}")
    lead_hours_list = []
    caught_before_bo = 0

    for aid, bo_dt, bo_c, bo_reason in breakouts:
        p_matches = [parse_dt(p["flagged_at"]) for p in all_proof if str(p.get("audio_id") or "") == aid and parse_dt(p.get("flagged_at"))]
        t_matches = [parse_dt(tr["first_detected_at"]) for tr in sb.table("trends").select("first_detected_at").eq("audio_id", aid).execute().data or [] if parse_dt(tr.get("first_detected_at"))]
        det_candidates = [d for d in (p_matches + t_matches) if d is not None and d < bo_dt]
        if det_candidates:
            earliest_det = min(det_candidates)
            lead_h = (bo_dt - earliest_det).total_seconds() / 3600.0
            lead_hours_list.append(lead_h)
            caught_before_bo += 1

    share_bo_before = (caught_before_bo / n_bo) if n_bo > 0 else 0.0
    median_lead_h = statistics.median(lead_hours_list) if lead_hours_list else 0.0
    print(f"Breakout Recall: Caught before breakout: {share_bo_before:.1%} ({caught_before_bo}/{n_bo}) | Median Lead: {median_lead_h:+.1f}h")

    # (c) Out-of-pool Coverage
    print("\n--- (c) OUT-OF-POOL COVERAGE ---")
    generic_stoplist = {
        "explore", "explorepage", "viral", "fyp", "reels", "trending", "foryou",
        "instagood", "instagram", "love", "like", "follow", "video", "reelsinstagram",
        "trend", "reel", "viralvideo", "viralreels", "trendingreels", "foryoupage"
    }
    reg_res = sb.table("tag_registry").select("tag").execute()
    registered_tags = {r["tag"].lower().lstrip("#") for r in (reg_res.data or []) if r.get("tag")}

    reels_res = sb.table("reels").select("hashtags").not_.is_("hashtags", "null").limit(500).execute()
    candidate_tags = set()
    for r in (reels_res.data or []):
        for h in (r.get("hashtags") or []):
            t = str(h).lower().strip().lstrip("#")
            if t and len(t) >= 4 and t not in registered_tags and t not in generic_stoplist:
                candidate_tags.add(t)

    random.seed(71)
    sampled_tags = random.sample(sorted(candidate_tags), min(8, len(candidate_tags)))
    print(f"Chosen 8 out-of-pool tags (seed=71): {sampled_tags}")

    cookies_path = os.path.join(backend_dir, "cookies.json")
    raw_cookies = []
    if os.path.exists(cookies_path):
        with open(cookies_path, "r", encoding="utf-8") as f:
            raw_cookies = json.load(f)
    elif os.environ.get("INSTAGRAM_COOKIES_B64"):
        try:
            b64_val = os.environ["INSTAGRAM_COOKIES_B64"]
            decoded = base64.b64decode(b64_val).decode("utf-8")
            raw_cookies = json.loads(decoded)
        except Exception as e:
            print(f"Notice: Failed to decode INSTAGRAM_COOKIES_B64: {e}")

    formatted_cookies = [
        {"name": c["name"], "value": c["value"], "domain": c.get("domain", ".instagram.com"), "path": c.get("path", "/")}
        for c in raw_cookies if isinstance(c, dict) and "name" in c and "value" in c
    ]

    audio_counts_in_sample = {}

    async def fetch_oop_tags():
        async with AsyncCamoufox(headless=True) as browser:
            ctx = await browser.new_context(no_viewport=True)
            if formatted_cookies:
                await ctx.add_cookies(formatted_cookies)
            page = await ctx.new_page()

            try:
                await page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_timeout(3000)
            except Exception:
                pass

            eval_script = """
            async (tagName) => {
                try {
                    const url = `https://www.instagram.com/api/v1/tags/web_info/?tag_name=${encodeURIComponent(tagName)}`;
                    const resp = await fetch(url, {
                        headers: {
                            'X-IG-App-ID': '936619743392459',
                            'X-Requested-With': 'XMLHttpRequest',
                            'Accept': '*/*'
                        }
                    });
                    const status = resp.status;
                    const data = await resp.json().catch(() => null);
                    return { status, data };
                } catch (err) {
                    return { status: -1, error: err.toString() };
                }
            }
            """

            cutoff_media = now - timedelta(hours=72)
            for idx, tag in enumerate(sampled_tags, start=1):
                jitter = random.uniform(3.0, 8.0)
                print(f"Loading tag #{tag} ({idx}/6, jitter {jitter:.1f}s)...")
                await asyncio.sleep(jitter)

                t0 = time.time()
                res = await page.evaluate(eval_script, tag)
                status = res.get("status")
                dur = time.time() - t0
                print(f"  HTTP status: {status} ({dur:.2f}s)")
                if status == 429:
                    print("FAIL: Instagram returned 429 Rate Limited.")
                    raise RuntimeError("Instagram 429 Rate Limited")
                if status != 200:
                    continue

                data = res.get("data") or {}
                sections = (data.get("data") or {}).get("recent", {}).get("sections") or (data.get("data") or {}).get("top", {}).get("sections") or []
                medias = []
                for s in sections:
                    for lay in s.get("layout_content", {}).get("medias", []):
                        m = lay.get("media")
                        if m:
                            medias.append(m)

                for m in medias:
                    taken_at = m.get("taken_at")
                    if taken_at:
                        dt = datetime.fromtimestamp(taken_at, tz=timezone.utc)
                        if dt < cutoff_media:
                            continue
                    music = m.get("music_metadata") or {}
                    aud = m.get("audio") or {}
                    is_orig = music.get("is_original_sound", True) and not music.get("music_info")
                    aid = str(music.get("music_canonical_id") or aud.get("audio_id") or "")
                    if aid and not is_orig:
                        audio_counts_in_sample[aid] = audio_counts_in_sample.get(aid, 0) + 1

    try:
        asyncio.run(fetch_oop_tags())
    except Exception as e:
        print(f"Out-of-pool fetch notice: {e}")

    popular_oop_aids = list(audio_counts_in_sample.keys())
    n_oop = len(popular_oop_aids)
    present_cnt = 0
    if popular_oop_aids:
        cutoff_7d = (now - timedelta(days=7)).isoformat()
        our_reels = sb.table("reels").select("audio_id").in_("audio_id", popular_oop_aids).gte("scraped_at", cutoff_7d).execute().data or []
        our_aids = {str(r["audio_id"]) for r in our_reels}
        present_cnt = sum(1 for aid in popular_oop_aids if aid in our_aids)

    share_oop = (present_cnt / n_oop) if n_oop > 0 else 0.0
    print(f"Out-of-pool coverage: {share_oop:.1%} ({present_cnt}/{n_oop}) present in our last 7 days reels")

    # Store in coverage_report
    report_rows = [
        {"week_start": week_start, "metric": "ground_truth_before", "value": float(share_before), "n": n_gt, "note": "share flagged/trended before reported_at"},
        {"week_start": week_start, "metric": "ground_truth_within_72h", "value": float(share_within_72h), "n": n_gt, "note": "share caught within 72h after reported_at"},
        {"week_start": week_start, "metric": "ground_truth_missed", "value": float(share_missed), "n": n_gt, "note": "share missed"},
        {"week_start": week_start, "metric": "breakout_recall_before", "value": float(share_bo_before), "n": n_bo, "note": "survivorship-biased: only tracked audios"},
        {"week_start": week_start, "metric": "breakout_lead_hours", "value": float(median_lead_h), "n": len(lead_hours_list), "note": "median lead hours before breakout"},
        {"week_start": week_start, "metric": "out_of_pool_coverage", "value": float(share_oop), "n": n_oop, "note": "8 caption-mined tags (seed=71)"},
    ]

    try:
        sb.table("coverage_report").insert(report_rows).execute()
        print("Inserted coverage_report rows successfully.")
    except Exception as ie:
        print(f"Error inserting coverage_report rows: {ie}")

    print("\n" + "=" * 80)
    print("                     PART 6.3: COVERAGE METRICS SUMMARY")
    print("=" * 80)
    for r in report_rows:
        val_str = f"{r['value']:.1%}" if "hours" not in r["metric"] else f"{r['value']:+.1f}h"
        thin_str = " (TOO THIN TO QUOTE: n < 30)" if r["n"] < 30 else " (VALID: n >= 30)"
        print(f"  {r['metric']:<26}: {val_str:<8} (n={r['n']}){thin_str}")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Order 61/65/70 Miss Diagnosis & Scoreboard")
    parser.add_argument("--report", action="store_true", help="Generate daily watchlist breakout conversion report")
    parser.add_argument("--scoreboard", action="store_true", help="Generate Order 65 detection scoreboard")
    parser.add_argument("--song-trends", action="store_true", help="Generate Order 65 Part 3.2 song-level trends report")
    parser.add_argument("--groundtruth", action="store_true", help="Generate Order 68 Part 4.2 ground truth audit")
    parser.add_argument("--coverage", action="store_true", help="Generate Order 70 Part 6 coverage report")
    args = parser.parse_args()

    load_dotenv(os.path.join(backend_dir, ".env"))
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("Supabase credentials not configured.")
    sb = create_client(url, key)

    if args.scoreboard:
        run_scoreboard(sb)
    elif args.groundtruth:
        run_groundtruth_report(sb)
    elif args.coverage:
        run_coverage_report(sb)
    elif args.song_trends:
        run_song_level_trends_report(sb)
    elif args.report:
        run_breakout_report(sb)
    else:
        run_diagnose_song_keys(sb)


if __name__ == "__main__":
    main()


