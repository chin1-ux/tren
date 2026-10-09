"""
backend/watchlist.py - Watchlist V3 (Order 61 Part E)

Groups by song_key over reels (72h) UNION probe_reels (72h):
- Distinct creators
- Total reels
- Max views
- Newest taken_at
- Count growth (when two exact/K readings exist in audio_count_history for any audio_id in key)

Stores score in watchlist.score and song_key in watchlist.song_key.
Top 30 active. Append to proof_log ONLY on first flag, with run_id.
Supports --no-write for offline testing and replays.
"""

import os
import sys
import math
import logging
import argparse
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Set, Optional, Tuple
from dotenv import load_dotenv

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from song_key import compute_song_key, normalize_title, normalize_artist
from supabase import create_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("watchlist")


def calculate_v3_score(
    max_views: int,
    distinct_creators: int,
    total_reels: int,
    max_velocity: float,
    growth_pct: float
) -> Tuple[float, Dict[str, float]]:
    """
    Watchlist V3 Scoring Formula:
    Score = (log10(max_views + 1) * 15.0)
          + (distinct_creators * 20.0)
          + (total_reels * 10.0)
          + (min(max_velocity, 5000.0) * 0.02)
          + (min(growth_pct, 100.0) * 0.5)
    """
    comp_views = math.log10(max_views + 1) * 15.0
    comp_creators = distinct_creators * 20.0
    comp_reels = total_reels * 10.0
    comp_velocity = min(max_velocity, 5000.0) * 0.02
    comp_growth = min(growth_pct, 100.0) * 0.5

    total = comp_views + comp_creators + comp_reels + comp_velocity + comp_growth
    components = {
        "comp_views": round(comp_views, 2),
        "comp_creators": round(comp_creators, 2),
        "comp_reels": round(comp_reels, 2),
        "comp_velocity": round(comp_velocity, 2),
        "comp_growth": round(comp_growth, 2),
        "total_score": round(total, 2),
    }
    return round(total, 2), components


def evaluate_watchlist(dry_run: bool = False, target_time: Optional[datetime] = None):
    load_dotenv(os.path.join(backend_dir, ".env"))
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("Supabase credentials not configured.")

    sb = create_client(url, key)
    ref_time = target_time or datetime.now(timezone.utc)
    h72_ago = (ref_time - timedelta(hours=72)).isoformat()
    ref_iso = ref_time.isoformat()

    # 1. Fetch audios in active trends detected ON OR BEFORE ref_iso (to exclude)
    t_query = sb.table("trends").select("audio_id, audio_title, audio_artist").neq("status", "unqualified")
    if target_time:
        t_query = t_query.lte("first_detected_at", ref_iso)
    trends_res = t_query.execute()
    trend_keys: Set[str] = set()
    trend_audio_ids: Set[str] = set()
    for t in (trends_res.data or []):
        if t.get("audio_id"):
            trend_audio_ids.add(str(t["audio_id"]))
        sk = compute_song_key(t.get("audio_title"), t.get("audio_artist"))
        if sk:
            trend_keys.add(sk)

    # 2. Existing watchlist & proof_log entries
    existing_wl_keys: Set[str] = set()
    try:
        wl_ex = sb.table("watchlist").select("song_key, audio_id").execute()
        for w in (wl_ex.data or []):
            if w.get("song_key"):
                existing_wl_keys.add(w["song_key"])
            elif w.get("audio_id"):
                existing_wl_keys.add(str(w["audio_id"]))
    except Exception as e:
        logger.warning(f"Error fetching existing watchlist: {e}")

    existing_proof_keys: Set[str] = set()
    try:
        pl_ex = sb.table("proof_log").select("audio_id, snapshot").execute()
        for p in (pl_ex.data or []):
            snap = p.get("snapshot") or {}
            sk = snap.get("song_key")
            if sk:
                existing_proof_keys.add(sk)
            elif p.get("audio_id"):
                existing_proof_keys.add(str(p["audio_id"]))
    except Exception as e:
        logger.warning(f"Error fetching existing proof_log: {e}")

    # 3. Pull 72h reels from 'reels' (paginated)
    song_groups: Dict[str, Dict[str, Any]] = {}
    offset = 0
    PAGE_SIZE = 1000

    while True:
        try:
            res = sb.table("reels") \
                .select("reel_id, audio_id, audio_title, audio_artist, owner_username, is_original_audio, velocity_score, view_count, created_at") \
                .gte("created_at", h72_ago) \
                .lte("created_at", ref_iso) \
                .not_.is_("audio_title", "null") \
                .order("id", desc=False) \
                .range(offset, offset + PAGE_SIZE - 1) \
                .execute()
            data = res.data or []
        except Exception as e:
            logger.warning(f"Error fetching reels at offset {offset}: {e}")
            break
        for r in data:
            if r.get("is_original_audio"):
                continue
            sk = compute_song_key(r.get("audio_title"), r.get("audio_artist"))
            if not sk or sk in trend_keys:
                continue

            aid = str(r.get("audio_id") or "").strip()
            if aid and aid in trend_audio_ids:
                continue

            if sk not in song_groups:
                song_groups[sk] = {
                    "song_key": sk,
                    "title": r.get("audio_title"),
                    "artist": r.get("audio_artist"),
                    "primary_audio_id": aid if aid and aid not in ("None", "0") else None,
                    "audio_ids": set(),
                    "creators": set(),
                    "reel_ids": set(),
                    "max_views": 0,
                    "max_velocity": 0.0,
                    "newest_taken_at": None,
                    "probe_matched_count": 0,
                }

            sg = song_groups[sk]
            if aid and aid not in ("None", "0"):
                sg["audio_ids"].add(aid)
                if not sg["primary_audio_id"]:
                    sg["primary_audio_id"] = aid

            u = r.get("owner_username")
            if u:
                sg["creators"].add(u)
            rid = r.get("reel_id")
            if rid:
                sg["reel_ids"].add(rid)

            v_cnt = int(r.get("view_count") or 0)
            if v_cnt > sg["max_views"]:
                sg["max_views"] = v_cnt

            v_score = float(r.get("velocity_score") or 0.0)
            if v_score > sg["max_velocity"]:
                sg["max_velocity"] = v_score

            c_at = r.get("created_at")
            if c_at and (sg["newest_taken_at"] is None or c_at > sg["newest_taken_at"]):
                sg["newest_taken_at"] = c_at

        if len(data) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    # 4. Pull 72h reels from 'probe_reels' (UNION)
    try:
        pr_res = sb.table("probe_reels") \
            .select("reel_code, audio_id, song_key, creator, taken_at, views") \
            .gte("taken_at", h72_ago) \
            .lte("taken_at", ref_iso) \
            .execute()
        pr_data = pr_res.data or []
        for pr in pr_data:
            sk = pr.get("song_key")
            if not sk or sk in trend_keys:
                continue

            if sk not in song_groups:
                title_part = sk.split("|")[0]
                artist_part = sk.split("|")[1] if "|" in sk else None
                aid = str(pr.get("audio_id") or "").strip()
                song_groups[sk] = {
                    "song_key": sk,
                    "title": title_part,
                    "artist": artist_part,
                    "primary_audio_id": aid if aid and aid not in ("None", "0") else None,
                    "audio_ids": set(),
                    "creators": set(),
                    "reel_ids": set(),
                    "max_views": 0,
                    "max_velocity": 0.0,
                    "newest_taken_at": None,
                    "probe_matched_count": 0,
                }

            sg = song_groups[sk]
            sg["probe_matched_count"] += 1
            aid = str(pr.get("audio_id") or "").strip()
            if aid and aid not in ("None", "0"):
                sg["audio_ids"].add(aid)
                if not sg["primary_audio_id"]:
                    sg["primary_audio_id"] = aid

            u = pr.get("creator")
            if u:
                sg["creators"].add(u)
            code = pr.get("reel_code")
            if code:
                sg["reel_ids"].add(code)

            views = int(pr.get("views") or 0)
            if views > sg["max_views"]:
                sg["max_views"] = views

            t_at = pr.get("taken_at")
            if t_at and (sg["newest_taken_at"] is None or t_at > sg["newest_taken_at"]):
                sg["newest_taken_at"] = t_at
    except Exception as pre:
        logger.warning(f"Error fetching probe_reels: {pre}")

    # 5. Fetch count history in 72h window for growth scoring
    all_target_aids = [aid for sg in song_groups.values() for aid in sg["audio_ids"] if aid]
    history_by_aid: Dict[str, List[Dict[str, Any]]] = {}
    if all_target_aids:
        # Batch in chunks of 50
        for i in range(0, len(all_target_aids), 50):
            chunk = all_target_aids[i:i+50]
            ach_res = sb.table("audio_count_history") \
                .select("audio_id, use_count, precision, captured_at") \
                .in_("audio_id", chunk) \
                .in_("precision", ["exact", "K"]) \
                .gte("captured_at", h72_ago) \
                .lte("captured_at", ref_iso) \
                .order("captured_at", desc=False) \
                .execute()
            for row in (ach_res.data or []):
                aid = str(row["audio_id"])
                history_by_aid.setdefault(aid, []).append(row)

    # 6. Score each song_key
    scored_candidates = []
    for sk, sg in song_groups.items():
        creators_cnt = len(sg["creators"])
        reels_cnt = len(sg["reel_ids"])

        # Candidate gate: at least 2 reels or 2 creators
        if reels_cnt < 2 and creators_cnt < 2:
            continue

        # Compute growth across any audio_id in the key
        best_growth = 0.0
        for aid in sg["audio_ids"]:
            h_rows = history_by_aid.get(aid, [])
            if len(h_rows) >= 2:
                c_first = h_rows[0].get("use_count")
                c_last = h_rows[-1].get("use_count")
                if c_first and c_last and c_first > 0:
                    g = max(0.0, ((c_last - c_first) / c_first) * 100.0)
                    if g > best_growth:
                        best_growth = g

        score, components = calculate_v3_score(
            max_views=sg["max_views"],
            distinct_creators=creators_cnt,
            total_reels=reels_cnt,
            max_velocity=sg["max_velocity"],
            growth_pct=best_growth
        )

        reasons = {
            "score": score,
            "components": components,
            "song_key": sk,
            "title": sg["title"],
            "artist": sg["artist"],
            "distinct_creators": creators_cnt,
            "total_reels": reels_cnt,
            "max_views": sg["max_views"],
            "max_velocity": round(sg["max_velocity"], 2),
            "growth_pct": round(best_growth, 2),
            "newest_taken_at": sg["newest_taken_at"],
            "probe_matched_count": sg["probe_matched_count"],
            "audio_ids": list(sg["audio_ids"]),
        }

        scored_candidates.append({
            "song_key": sk,
            "audio_id": sg["primary_audio_id"] or list(sg["audio_ids"])[0] if sg["audio_ids"] else sk,
            "score": score,
            "reasons": reasons,
            "creators": creators_cnt,
            "reels": reels_cnt,
            "probe_matches": sg["probe_matched_count"],
            "title": sg["title"],
            "artist": sg["artist"],
            "snapshot": {
                "rule": "watchlist_v3_song_key",
                "song_key": sk,
                "score": score,
                "creators": list(sg["creators"])[:5],
                "sample_reels": list(sg["reel_ids"])[:3],
            }
        })

    # Sort by score desc, pick top 30
    scored_candidates.sort(key=lambda x: x["score"], reverse=True)
    top_30 = scored_candidates[:30]

    logger.info(f"Watchlist V3 Evaluation Complete: {len(scored_candidates)} candidates -> Top {len(top_30)} selected")
    if top_30:
        top_1 = top_30[0]
        logger.info(
            f"Top Rank #1: '{top_1['song_key']}' | Score: {top_1['score']} | "
            f"Formula: views={top_1['reasons']['components']['comp_views']} + "
            f"creators={top_1['reasons']['components']['comp_creators']} + "
            f"reels={top_1['reasons']['components']['comp_reels']} + "
            f"velo={top_1['reasons']['components']['comp_velocity']} + "
            f"growth={top_1['reasons']['components']['comp_growth']}"
        )

    # 7. Persistence (skip if dry_run)
    run_id = os.getenv("GITHUB_RUN_ID")
    if not dry_run and top_30:
        for cand in top_30:
            sk = cand["song_key"]
            aid = cand["audio_id"]

            wl_row = {
                "audio_id": aid,
                "song_key": sk,
                "score": cand["score"],
                "status": "watching",
                "first_reels": cand["reels"],
                "first_creators": cand["creators"],
                "reasons": cand["reasons"],
                "flagged_at": ref_iso,
                "run_id": run_id
            }

            try:
                # Upsert watchlist row by audio_id
                sb.table("watchlist").upsert(wl_row, on_conflict="audio_id").execute()
            except Exception as we:
                logger.warning(f"Error upserting watchlist row for {sk}: {we}")

            # Append to proof_log ONLY on first flag (if song_key not already logged)
            if sk not in existing_proof_keys and aid not in existing_proof_keys:
                proof_row = {
                    "audio_id": aid,
                    "flagged_at": ref_iso,
                    "reasons": cand["reasons"],
                    "snapshot": cand["snapshot"],
                    "run_id": run_id
                }
                try:
                    sb.table("proof_log").insert(proof_row).execute()
                    existing_proof_keys.add(sk)
                    logger.info(f"Proof log recorded new breakout candidate: {sk} (score={cand['score']})")
                except Exception as pe:
                    logger.warning(f"Error inserting proof_log row for {sk}: {pe}")

    return top_30, scored_candidates


def main():
    parser = argparse.ArgumentParser(description="Watchlist V3 Evaluator (Order 61 Part E)")
    parser.add_argument("--no-write", action="store_true", help="Dry run: evaluate without writing to database")
    args = parser.parse_args()

    top_30, _ = evaluate_watchlist(dry_run=args.no_write)
    print("\n=== TOP 10 WATCHLIST V3 SONGS ===")
    for idx, c in enumerate(top_30[:10], 1):
        print(f"#{idx:02d} | Song: {c['song_key']:<35} | Score: {c['score']:<6.1f} | Creators: {c['creators']:<3} | Reels: {c['reels']:<3} | Probe Matches: {c['probe_matches']}")


if __name__ == "__main__":
    main()
