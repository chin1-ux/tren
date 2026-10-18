"""
Deck and Explore routes for Trendrop (Order 100)
Provides ultra-slim, edge-cacheable, egress-minimal endpoints for:
- GET /api/deck: Deck card stack (rule B eligibility, deduplication, slim fields)
- GET /api/trends/explore: Cursor-paginated explore feed with stage/niche/mode filters
- POST /api/swipes: Queued batch upsert of user swipes (and target sync)
- GET /api/swipes: Fetch user swipe history
"""

import os
import sys
import math
import time
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Header, Query, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api_globals import (
    supabase,
    limiter,
    _resolve_user,
    require_auth
)

try:
    from audio_title_normalize import normalize_audio_title
except ImportError:
    # Fallback title normalizer
    import re
    def normalize_audio_title(title: str) -> str:
        if not title:
            return ""
        return re.sub(r"\s+", " ", re.sub(r"\(.*?\)", "", title)).strip()

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Deck"])

# Supported Indian languages for India mode per B1
INDIAN_LANGUAGES = {
    "hi", "hindi", "ta", "tamil", "te", "telugu", "ml", "malayalam",
    "kn", "kannada", "pa", "punjabi", "en", "english", "instrumental"
}

# Standard stage mapping per C3
STAGE_LABEL_MAP = {
    "emerging": "Just starting",
    "rising": "Blowing up",
    "peaked": "Everyone's using it",
    "resurging": "Comeback",
    "expired": "Expired"
}

# Slim columns to fetch from DB (total row size <= 350 bytes)
DECK_SELECT_COLS = (
    "id,audio_id,audio_title,audio_artist,status,first_detected_at,"
    "reel_count,audio_use_count,language_final,language,"
    "niche_tag,semantic_niches,used_for_note,why_this_works,"
    "window_hours_remaining,is_voiceover,is_seed_data"
)

# In-memory edge cache for public deck responses (TTL 300s)
_DECK_CACHE: Dict[str, Dict[str, Any]] = {}
_EXPLORE_CACHE: Dict[str, Dict[str, Any]] = {}


class SwipeItem(BaseModel):
    trend_id: int
    action: str = Field(..., pattern="^(use|skip)$")
    reason: Optional[str] = None


class BatchSwipesRequest(BaseModel):
    swipes: List[SwipeItem] = Field(..., max_items=20)


def _format_stage(status: str) -> str:
    """Map DB status to human-readable stage label (per C3)."""
    return STAGE_LABEL_MAP.get((status or "").lower().strip(), "Just starting")


def _resolve_creator_count(row: Dict[str, Any]) -> int:
    """Determine creator count, falling back to reel_count or 1."""
    return int(row.get("creator_count") or row.get("reel_count") or 1)


def _resolve_niche(row: Dict[str, Any]) -> Optional[str]:
    """Extract primary niche tag, excluding 'other' or 'general'."""
    niche = row.get("niche_tag")
    if not niche or niche.lower() in ("other", "general", "none", "null"):
        semantic = row.get("semantic_niches") or []
        for s in semantic:
            if s and s.lower() not in ("other", "general", "none", "null"):
                niche = s
                break
    if niche and niche.lower() not in ("other", "general", "none", "null"):
        return niche
    return None


@router.get("/api/deck")
def get_deck_trends(
    request: Request,
    mode: str = Query("india", description="'india' or 'global'"),
    langs: Optional[str] = Query(None, description="Comma-separated language list"),
    niches: Optional[str] = Query(None, description="Comma-separated niche list"),
    limit: int = Query(120, le=120),
    authorization: Optional[str] = Header(None)
):
    """
    Public, edge-cacheable deck trends pool.
    Implements Rule B eligibility (reel_count >= 2 OR audio_use_count >= 50000).
    Deduplicates one card per normalized title+artist (keeps highest creator/reel count).
    Slim response <= 300 bytes/row, <= 40 KB total.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")

    mode_clean = (mode or "india").lower().strip()
    cache_key = f"{mode_clean}:{langs or ''}:{niches or ''}:{limit}"
    now_ts = time.time()

    # Public caching: bypass if Authorization provided
    is_auth = bool(authorization and authorization.strip().startswith("Bearer "))
    if not is_auth and cache_key in _DECK_CACHE:
        entry = _DECK_CACHE[cache_key]
        if now_ts - entry["time"] < 300:
            headers = {
                "Cache-Control": "public, s-maxage=300, stale-while-revalidate=600, stale-if-error=86400",
                "X-Cache": "HIT"
            }
            return JSONResponse(content=entry["data"], headers=headers)

    try:
        # Base DB query: emerging & rising, positive window, not voiceover, not seed, not bhojpuri
        query = supabase.table("trends").select(DECK_SELECT_COLS)\
            .in_("status", ["emerging", "rising"])\
            .gt("window_hours_remaining", 0)\
            .eq("is_voiceover", False)\
            .eq("is_seed_data", False)\
            .neq("language_final", "bhojpuri")\
            .or_("reel_count.gte.2,audio_use_count.gte.50000")\
            .order("first_detected_at", desc=True)\
            .limit(300)

        res = query.execute()
        rows = res.data or []

        # Parse requested language filter if supplied
        selected_langs = set([l.strip().lower() for l in langs.split(",") if l.strip()]) if langs else None
        selected_niches = set([n.strip().lower() for n in niches.split(",") if n.strip()]) if niches else None

        filtered = []
        for r in rows:
            lang = (r.get("language_final") or r.get("language") or "").strip().lower()
            if lang in ("bhojpuri", "bho"):
                continue

            # Mode filter
            if mode_clean == "india":
                if lang and lang not in INDIAN_LANGUAGES:
                    continue

            # Explicit language filter
            if selected_langs:
                if lang not in selected_langs:
                    continue

            # Explicit niche filter
            if selected_niches:
                row_niches = set()
                if r.get("niche_tag"):
                    row_niches.add(r.get("niche_tag").lower().strip())
                for s in (r.get("semantic_niches") or []):
                    if s:
                        row_niches.add(s.lower().strip())
                if not (row_niches & selected_niches):
                    continue

            filtered.append(r)

        # Deduplicate: one card per normalized title+artist, keeping highest creator/reel count
        groups: Dict[tuple, List[Dict[str, Any]]] = {}
        for r in filtered:
            norm_title = normalize_audio_title(r.get("audio_title") or "").strip().lower()
            norm_artist = (r.get("audio_artist") or "").strip().lower()
            key = (norm_title, norm_artist)
            if key not in groups:
                groups[key] = []
            groups[key].append(r)

        deduped = []
        for key, items in groups.items():
            best = max(
                items,
                key=lambda x: (
                    _resolve_creator_count(x),
                    x.get("reel_count") or 0,
                    x.get("audio_use_count") or 0
                )
            )
            deduped.append(best)

        # Limit to requested pool size (e.g. 120)
        final_pool = deduped[:limit]

        # Format slim payload for client
        now_dt = datetime.now(timezone.utc)
        items = []
        for r in final_pool:
            fd_str = r.get("first_detected_at")
            age_hours = 0.0
            if fd_str:
                try:
                    dt = datetime.fromisoformat(fd_str.replace("Z", "+00:00"))
                    age_hours = max(0.0, (now_dt - dt).total_seconds() / 3600.0)
                except Exception:
                    pass

            used_for = (r.get("used_for_note") or r.get("why_this_works") or "").strip()
            items.append({
                "id": r["id"],
                "audio_id": r.get("audio_id"),
                "audio_title": r.get("audio_title") or "Unknown Audio",
                "audio_artist": r.get("audio_artist") or "Unknown Artist",
                "status": r.get("status") or "emerging",
                "stage_label": _format_stage(r.get("status")),
                "first_detected_at": fd_str,
                "age_hours": round(age_hours, 1),
                "is_new_today": age_hours < 24.0,
                "creator_count": _resolve_creator_count(r),
                "reel_count": int(r.get("reel_count") or 0),
                "audio_use_count": int(r.get("audio_use_count") or 0),
                "language": (r.get("language_final") or r.get("language") or "").strip(),
                "niche": _resolve_niche(r),
                "used_for": used_for if used_for else None
            })

        payload = {
            "mode": mode_clean,
            "count": len(items),
            "trends": items
        }

        # Cache public results
        if not is_auth:
            _DECK_CACHE[cache_key] = {"data": payload, "time": now_ts}

        headers = {
            "Cache-Control": "private, no-cache" if is_auth else "public, s-maxage=300, stale-while-revalidate=600, stale-if-error=86400",
            "X-Cache": "MISS"
        }
        return JSONResponse(content=payload, headers=headers)

    except Exception as e:
        logger.error(f"Error serving /api/deck: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/trends/explore")
def get_explore_trends(
    request: Request,
    cursor: Optional[int] = Query(None, description="Cursor pagination: last seen trend ID"),
    limit: int = Query(20, le=50),
    stage: Optional[str] = Query(None, description="Filter stage: just_starting, blowing_up, everyones_using_it, comeback, expired"),
    include_expired: bool = Query(False, description="Whether to include expired trends"),
    mode: str = Query("india", description="'india' or 'global'"),
    language: Optional[str] = Query(None),
    niche: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """
    Cursor-paginated explore feed for B4 screen.
    Stages:
      - 'Just starting' (emerging)
      - 'Blowing up' (rising)
      - 'Everyone's using it' (peaked)
      - 'Comeback' (resurging, reel_count >= 3, cap 50)
      - 'Expired' (expired)
    Total count returned from COUNT.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")

    try:
        # Build stage status list
        stage_status_map = {
            "just_starting": ["emerging"],
            "blowing_up": ["rising"],
            "everyones_using_it": ["peaked"],
            "comeback": ["resurging"],
            "expired": ["expired"]
        }

        if stage and stage.lower() in stage_status_map:
            target_statuses = stage_status_map[stage.lower()]
        elif include_expired:
            target_statuses = ["emerging", "rising", "peaked", "resurging", "expired"]
        else:
            target_statuses = ["emerging", "rising", "peaked", "resurging"]

        # Base query for items
        q = supabase.table("trends").select(DECK_SELECT_COLS, count="exact")\
            .in_("status", target_statuses)\
            .eq("is_voiceover", False)\
            .eq("is_seed_data", False)\
            .neq("language_final", "bhojpuri")

        # Resurging comeback filter: floor reel_count >= 3
        if stage and stage.lower() == "comeback":
            q = q.gte("reel_count", 3)

        # Mode language filter
        if mode.lower() == "india":
            # Handled in memory or query if feasible
            pass

        if language:
            q = q.eq("language_final", language.lower().strip())

        if niche:
            q = q.contains("semantic_niches", [niche.lower().strip()])

        if search and search.strip():
            s_term = search.strip()
            q = q.or_(f"audio_title.ilike.%{s_term}%,audio_artist.ilike.%{s_term}%")

        if cursor:
            q = q.lt("id", cursor)

        q = q.order("id", desc=True).limit(limit)
        res = q.execute()

        total_count = res.count or 0
        rows = res.data or []

        # Filter mode in memory if india
        if mode.lower() == "india":
            rows = [
                r for r in rows
                if (r.get("language_final") or r.get("language") or "").strip().lower() in INDIAN_LANGUAGES
            ]

        now_dt = datetime.now(timezone.utc)
        items = []
        for r in rows:
            fd_str = r.get("first_detected_at")
            age_hours = 0.0
            if fd_str:
                try:
                    dt = datetime.fromisoformat(fd_str.replace("Z", "+00:00"))
                    age_hours = max(0.0, (now_dt - dt).total_seconds() / 3600.0)
                except Exception:
                    pass

            used_for = (r.get("used_for_note") or r.get("why_this_works") or "").strip()
            items.append({
                "id": r["id"],
                "audio_id": r.get("audio_id"),
                "audio_title": r.get("audio_title") or "Unknown Audio",
                "audio_artist": r.get("audio_artist") or "Unknown Artist",
                "status": r.get("status") or "emerging",
                "stage_label": _format_stage(r.get("status")),
                "first_detected_at": fd_str,
                "age_hours": round(age_hours, 1),
                "is_new_today": age_hours < 24.0,
                "creator_count": _resolve_creator_count(r),
                "reel_count": int(r.get("reel_count") or 0),
                "audio_use_count": int(r.get("audio_use_count") or 0),
                "language": (r.get("language_final") or r.get("language") or "").strip(),
                "niche": _resolve_niche(r),
                "used_for": used_for if used_for else None
            })

        next_cursor = items[-1]["id"] if items and len(items) == limit else None

        return {
            "total": total_count,
            "next_cursor": next_cursor,
            "trends": items
        }

    except Exception as e:
        logger.error(f"Error in /api/trends/explore: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/api/swipes")
def record_user_swipes(
    req: BatchSwipesRequest,
    authorization: Optional[str] = Header(None)
):
    """
    POST /api/swipes: Queued batch upsert of user swipes (up to 20).
    Requires authentication.
    Syncs 'use' action to trend_actions so Studio/Dashboard keep working.
    Returns minimal confirmation response.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")

    user_id = _resolve_user(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required to record swipes")

    now_iso = datetime.now(timezone.utc).isoformat()
    swipe_rows = []
    target_sync_trend_ids = []

    for s in req.swipes:
        swipe_rows.append({
            "user_id": user_id,
            "trend_id": s.trend_id,
            "action": s.action,
            "reason": s.reason,
            "updated_at": now_iso
        })
        if s.action == "use":
            target_sync_trend_ids.append(s.trend_id)

    try:
        # Upsert into user_swipes table
        res = supabase.table("user_swipes").upsert(
            swipe_rows,
            on_conflict="user_id,trend_id"
        ).execute()

        # If 'use' action recorded, sync to trend_actions for backwards compatibility
        if target_sync_trend_ids:
            for tid in target_sync_trend_ids:
                try:
                    supabase.table("trend_actions").upsert({
                        "user_id": user_id,
                        "trend_id": tid,
                        "action_type": "target"
                    }, on_conflict="user_id,trend_id,action_type").execute()
                except Exception as sync_err:
                    logger.warning(f"Failed to sync trend_actions target for trend {tid}: {sync_err}")

        return {"success": True, "recorded": len(swipe_rows)}

    except Exception as e:
        logger.error(f"Error recording swipes for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/swipes")
def get_user_swipes(
    limit: int = Query(300, le=300),
    authorization: Optional[str] = Header(None)
):
    """
    GET /api/swipes: Fetch user's swipe history for taste learning and Picks.
    Requires authentication. Returns up to 300 swipes ordered by updated_at desc.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")

    user_id = _resolve_user(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required to fetch swipes")

    try:
        res = supabase.table("user_swipes").select("trend_id, action, reason, updated_at")\
            .eq("user_id", user_id)\
            .order("updated_at", desc=True)\
            .limit(limit)\
            .execute()

        return {
            "success": True,
            "swipes": res.data or []
        }
    except Exception as e:
        logger.error(f"Error fetching swipes for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
