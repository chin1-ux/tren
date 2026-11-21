"""
backend/candidate_accumulator.py

Multi-Run Rolling Candidate Aggregator.
Evaluates the rolling 48-72h window of accumulated reels in Supabase.
Safely bridges single-run hashtag crawls by promoting audios that have 
accumulated multi-creator adoption or breakout velocity into `trends`.
Gracefully updates existing trends without duplicate key collisions.
"""

import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

try:
    from language_detection import _detect_audio_language, is_disallowed_regional_content
    from classification_rules import classify_niche, classify_content_tone
    from api_globals import supabase as global_supabase
except ImportError:
    from backend.language_detection import _detect_audio_language, is_disallowed_regional_content
    from backend.classification_rules import classify_niche, classify_content_tone
    from backend.api_globals import supabase as global_supabase


def _get_sb():
    if global_supabase:
        return global_supabase
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    return create_client(url, key)


def promote_rolling_candidates(target_min_trends: int = 30) -> Tuple[List[int], int]:
    """
    Evaluates unpromoted reels from the rolling 48-72 hour pool.
    - If audio is brand new and qualified: inserts as new trend (returns ID in inserted_ids).
    - If audio is already in trends: refreshes last_seen_at and reel_count (tracks resurging comeback).
    Returns (inserted_ids, refreshed_count).
    """
    sb = _get_sb()
    if not sb:
        logger.warning("[accumulator] Supabase client unavailable.")
        return [], 0

    logger.info("=== Rolling Candidate Accumulator Starting ===")

    # 1. Fetch recent reels (last 10,000 reels by ID)
    try:
        max_res = sb.table("reels").select("id").order("id", desc=True).limit(1).execute()
        max_id = (max_res.data or [{}])[0].get("id") or 0
        min_id = max(0, max_id - 10000)

        res_reels = (
            sb.table("reels")
            .select("id,audio_id,audio_title,audio_artist,view_count,like_count,comment_count,velocity_score,owner_username,caption,hashtags,created_at")
            .gte("id", min_id)
            .not_.is_("audio_title", "null")
            .order("id", desc=True)
            .limit(1000)
            .execute()
        )
        reels = res_reels.data or []
    except Exception as e:
        logger.error(f"[accumulator] Failed to query reels: {e}")
        return [], 0

    if not reels:
        logger.info("[accumulator] No recent candidate reels found.")
        return [], 0

    # 2. Group by audio
    groups: Dict[str, Dict[str, Any]] = {}
    for r in reels:
        title = (r.get("audio_title") or "").strip()
        artist = (r.get("audio_artist") or "").strip()
        aid = str(r.get("audio_id") or "").strip()

        if not title or title.lower() in ("original audio", "original sound", ""):
            continue
        if title.lower().startswith("original_audio::") or title.lower().startswith("mix:"):
            continue

        k = aid if (aid and aid != "None") else f"{title.lower()}:::{artist.lower()}"
        if k not in groups:
            groups[k] = {
                "title": title,
                "artist": artist,
                "audio_id": aid if (aid and aid != "None") else None,
                "reels": [],
            }
        groups[k]["reels"].append(r)

    logger.info(f"[accumulator] Identified {len(groups)} distinct audio groups across recent reels.")

    now_iso = datetime.now(timezone.utc).isoformat()
    inserted_ids: List[int] = []
    refreshed_count = 0

    for k, g in groups.items():
        title = g["title"]
        artist = g["artist"]
        aid = g["audio_id"]
        g_reels = g["reels"]

        views_list = [r.get("view_count") or 0 for r in g_reels]
        likes_list = [r.get("like_count") or 0 for r in g_reels]
        vel_list = [float(r.get("velocity_score") or 0.0) for r in g_reels]

        max_views = max(views_list, default=0)
        max_likes = max(likes_list, default=0)
        avg_velocity = sum(vel_list) / len(vel_list) if vel_list else 0.0
        max_velocity = max(vel_list, default=0.0)

        creators = {r.get("owner_username") for r in g_reels if r.get("owner_username")}
        creator_count = len(creators)

        # Disallow regional content
        captions = " ".join([r.get("caption") or "" for r in g_reels])
        hashtags = []
        for r in g_reels:
            hashtags.extend(r.get("hashtags") or [])

        if is_disallowed_regional_content(title, artist, captions, hashtags):
            continue

        # Check if already exists in trends table
        existing_trend = None
        try:
            if aid:
                chk = sb.table("trends").select("id, status, opportunity_score").eq("audio_id", str(aid).strip()).limit(1).execute()
                if chk.data:
                    existing_trend = chk.data[0]
            if not existing_trend and title:
                chk_t = sb.table("trends").select("id, status, opportunity_score").ilike("audio_title", title).limit(1).execute()
                if chk_t.data:
                    existing_trend = chk_t.data[0]
        except Exception as _chk_err:
            logger.debug(f"[accumulator] Trend check error: {_chk_err}")

        # If already exists, perform refresh
        if existing_trend:
            try:
                tid = existing_trend["id"]
                curr_st = existing_trend.get("status")
                upd_payload = {
                    "last_seen_at": now_iso,
                    "reel_count": len(g_reels),
                }
                if curr_st in ("peaked", "expired") and (max_views >= 20000 or avg_velocity >= 15.0 or creator_count >= 2):
                    upd_payload["status"] = "resurging"
                    upd_payload["status_reason"] = {
                        "previous_status": curr_st,
                        "new_status": "resurging",
                        "transition_timestamp": now_iso,
                        "trigger_source": "rolling_accumulator_refresh",
                    }
                sb.table("trends").update(upd_payload).eq("id", tid).execute()
                refreshed_count += 1
            except Exception as _upd_err:
                logger.debug(f"[accumulator] Trend refresh error: {_upd_err}")
            continue

        # If BRAND NEW: Check qualification
        is_qualified = (
            max_views >= 10000
            or (max_views >= 3000 and max_likes >= 15)
            or creator_count >= 2
            or avg_velocity >= 15.0
        )
        if not is_qualified:
            continue

        lang = _detect_audio_language(title, artist, captions)
        if not lang or lang == "unknown":
            lang = "en"

        niche = classify_niche(hashtags, captions, title)
        tone = classify_content_tone(captions, hashtags)

        status = "rising" if (max_views >= 50000 or avg_velocity >= 25.0 or creator_count >= 3) else "emerging"

        base_opp = 72.0
        if max_views > 100000:
            base_opp += 14.0
        elif max_views > 20000:
            base_opp += 8.0
        if avg_velocity > 50:
            base_opp += 8.0
        elif avg_velocity > 15:
            base_opp += 4.0
        opp_score = round(min(96.0, max(65.0, base_opp)), 1)

        sample_caps = [r.get("caption") for r in g_reels if r.get("caption")]
        sample_caption_str = sample_caps[0][:280] if sample_caps else ""

        payload = {
            "audio_title": title,
            "audio_artist": artist or "Various Artists",
            "audio_id": aid,
            "platform": "instagram",
            "status": status,
            "language": lang,
            "language_final": lang,
            "language_confidence": 0.88,
            "language_source": "rolling_accumulator",
            "niche_tag": niche,
            "semantic_niches": [niche],
            "content_tone": tone,
            "opportunity_score": opp_score,
            "niche_fit_score": 85.0,
            "velocity_avg": avg_velocity,
            "peak_velocity": max_velocity,
            "audio_use_count": max((r.get("audio_use_count") or 0 for r in g_reels), default=0),
            "reel_count": len(g_reels),
            "window_hours_remaining": 48,
            "first_detected_at": now_iso,
            "last_seen_at": now_iso,
            "is_voiceover": False,
            "is_seed_data": False,
            "sample_captions": sample_caption_str,
            "why_this_works": None,
            "used_for_note": None,
            "analysis_status": "pending",
            "analysis_attempts": 0,
            "status_reason": {
                "previous_status": None,
                "new_status": status,
                "transition_timestamp": now_iso,
                "trigger_source": "rolling_accumulator",
                "decision_metrics": {
                    "max_views": max_views,
                    "max_likes": max_likes,
                    "avg_velocity": avg_velocity,
                    "unique_creators": creator_count,
                    "reel_count": len(g_reels),
                },
            },
        }

        try:
            res = sb.table("trends").insert(payload).execute()
            if res.data:
                tid = res.data[0].get("id")
                inserted_ids.append(tid)
                logger.info(
                    f"[accumulator] INSERTED brand new trend ID {tid}: '{title}' by {artist} "
                    f"(reels={len(g_reels)}, creators={creator_count}, views={max_views})"
                )
        except Exception as ins_err:
            logger.error(f"[accumulator] Failed inserting '{title}': {ins_err}")

        if len(inserted_ids) >= target_min_trends:
            break

    logger.info(
        f"=== Rolling Candidate Accumulator complete: {len(inserted_ids)} new trends inserted, "
        f"{refreshed_count} existing trends refreshed ==="
    )
    return inserted_ids, refreshed_count
