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
import urllib.request
from fastapi import APIRouter, HTTPException, Header, Query, Request, Depends
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

import re
from api_globals import (
    supabase,
    limiter,
    _resolve_user,
    require_auth,
    sanitize_postgrest_value
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

# Strict Indian languages for India mode (English is NEVER an Indian language per specification)
INDIAN_LANGUAGES = {
    "hi", "hindi", "ta", "tamil", "te", "telugu", "ml", "malayalam",
    "kn", "kannada", "pa", "punjabi", "mr", "marathi", "bn", "bengali",
    "gu", "gujarati", "ne", "nepali"
}

# Strict Global languages for Global mode
GLOBAL_LANGUAGES = {
    "en", "english", "es", "spanish", "pt", "portuguese",
    "ko", "korean", "ja", "japanese", "ru", "russian",
    "fr", "french", "de", "german", "it", "italian"
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
    "id,audio_id,audio_title,audio_artist,status,first_detected_at,last_seen_at,"
    "reel_count,audio_use_count,language_final,language,trend_origin,"
    "niche_tag,semantic_niches,used_for_note,why_this_works,ideal_content_description,hook_brief,optimal_post_hour_ist,"
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
    limit: int = Query(120, le=200),
    include_expired: Optional[bool] = Query(False, description="Whether to include expired audios in deck pool"),
    fresh: Optional[bool] = Query(False, description="Bypass all caching and sync latest live data"),
    authorization: Optional[str] = Header(None)
):
    """
    Public, edge-cacheable deck trends pool.
    When filters (niches or langs or include_expired) are active, includes expired audios.
    Deduplicates one card per normalized title+artist (keeps highest creator/reel count).
    Slim response <= 300 bytes/row, <= 40 KB total.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")

    mode_clean = (mode or "india").lower().strip()
    has_filters = bool((niches and niches.strip() and niches != "all") or (langs and langs.strip() and langs != "all") or include_expired)
    cache_key = f"{mode_clean}:{langs or ''}:{niches or ''}:{has_filters}:{limit}"
    now_ts = time.time()

    # Public caching: bypass if Authorization provided or fresh sync requested
    is_auth = bool(authorization and authorization.strip().startswith("Bearer "))
    is_cache_bypassed = is_auth or fresh or request.headers.get("Cache-Control") == "no-cache"

    if not is_cache_bypassed and cache_key in _DECK_CACHE:
        entry = _DECK_CACHE[cache_key]
        if now_ts - entry["time"] < 30:
            headers = {
                "Cache-Control": "public, s-maxage=15, stale-while-revalidate=45, stale-if-error=86400",
                "X-Cache": "HIT"
            }
            return JSONResponse(content=entry["data"], headers=headers)

    try:
        # Base DB query: if filters active or include_expired, include all stages including expired
        query = supabase.table("trends").select(DECK_SELECT_COLS)\
            .eq("is_voiceover", False)\
            .eq("is_seed_data", False)\
            .neq("language_final", "bhojpuri")

        if has_filters:
            query = query.in_("status", ["emerging", "rising", "resurging", "peaked", "expired"])
        else:
            query = query.in_("status", ["emerging", "rising", "resurging"])

        # Parse requested language and niche filters if supplied
        selected_langs = set([l.strip().lower() for l in langs.split(",") if l.strip() and l.strip().lower() != "all"]) if langs else None
        selected_niches = set([n.strip().lower() for n in niches.split(",") if n.strip() and n.strip().lower() != "all"]) if niches else None

        if selected_niches:
            niche_clauses = [f"semantic_niches.cs.{{{n}}},niche_tag.eq.{n}" for n in selected_niches]
            query = query.or_(",".join(niche_clauses))

        if selected_langs:
            lang_clauses = [f"language_final.eq.{l},language.eq.{l}" for l in selected_langs]
            query = query.or_(",".join(lang_clauses))

        query = query.order("id", desc=True).limit(300)

        res = query.execute()
        rows = res.data or []

        filtered = []
        for r in rows:
            lang = (r.get("language_final") or r.get("language") or "").strip().lower()
            if lang in ("bhojpuri", "bho"):
                continue

            # Strict Mode filter: India strictly includes only Indian languages; Global strictly includes Global languages
            trend_origin_val = (r.get("trend_origin") or "").strip().upper()
            if mode_clean == "india":
                # Must be an Indian language AND origin must not be GLOBAL
                if not lang or lang not in INDIAN_LANGUAGES or lang in GLOBAL_LANGUAGES:
                    continue
                if trend_origin_val in ("GLOBAL", "KR", "BR", "ES", "RU"):
                    continue
            elif mode_clean == "global":
                # Must be a Global language AND origin must not be IN
                if not lang or lang not in GLOBAL_LANGUAGES or lang in INDIAN_LANGUAGES:
                    continue
                if trend_origin_val == "IN":
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

            # Quality Gate: Exclude single-user personal audio clips with no creator replication
            norm_t = (r.get("audio_title") or "").strip().lower()
            reel_cnt = r.get("reel_count") or 0
            use_cnt = r.get("audio_use_count") or 0
            if "original audio" in norm_t and reel_cnt <= 1 and use_cnt <= 1:
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

        # Sort deduped strictly newest to oldest (by discovery/created timestamp, and id descending)
        deduped.sort(
            key=lambda x: (
                max(str(x.get("first_detected_at") or ""), str(x.get("created_at") or "")),
                x.get("id") or 0
            ),
            reverse=True
        )

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

            used_for = (r.get("used_for_note") or "").strip()
            why_this_works = (r.get("why_this_works") or "").strip()
            ideal_desc = (r.get("ideal_content_description") or "").strip()

            # Filter out canned automated fallback classification strings & synthetic templates
            canned_needles = [
                "currently driving high engagement",
                "adapt the visual style of",
                "automated fallback classification",
                "creators consistently use this sound",
                "used sporadically across unrelated",
                "audio is used sporadically",
                "sporadic usage across mixed",
                "film a high-retention",
                "popular audio for creator other reels",
                "popular in general creator reels",
                "used for fast-paced visual storytelling",
                "resonates with",
                "positive content during these times",
                "current emotional state",
                "cultural and emotional climate",
                "sentiments about life",
                "evokes positive emotions",
                "positive and encouraging tone",
                "popular choice for content creators",
                "is spreading right now because",
                "insufficient reel data",
                "no indexed reel evidence",
                "sampled reels show completely discordant themes",
                "strong algorithmic audio momentum",
                "short creator clips that match",
                "post aesthetic clips or photos matching",
                "do not use this track expecting",
            ]
            for needle in canned_needles:
                if needle in why_this_works.lower():
                    why_this_works = ""
                if needle in used_for.lower():
                    used_for = ""
                if needle in ideal_desc.lower():
                    ideal_desc = ""

            items.append({
                "id": r["id"],
                "audio_id": r.get("audio_id"),
                "audio_title": r.get("audio_title") or "Unknown Audio",
                "audio_artist": r.get("audio_artist") or "Unknown Artist",
                "status": r.get("status") or "emerging",
                "stage_label": _format_stage(r.get("status")),
                "first_detected_at": fd_str,
                "last_seen_at": r.get("last_seen_at"),
                "age_hours": round(age_hours, 1),
                "is_new_today": age_hours < 24.0,
                "creator_count": _resolve_creator_count(r),
                "reel_count": int(r.get("reel_count") or 0),
                "audio_use_count": int(r.get("audio_use_count") or 0),
                "language": (r.get("language_final") or r.get("language") or "").strip(),
                "niche": _resolve_niche(r),
                "used_for": used_for if used_for else None,
                "why_this_works": why_this_works if why_this_works else None,
                "ideal_content_description": ideal_desc if ideal_desc else None,
                "hook_brief": r.get("hook_brief") or None,
                "optimal_post_hour_ist": r.get("optimal_post_hour_ist"),
            })

        payload = {
            "mode": mode_clean,
            "count": len(items),
            "trends": items
        }

        # Cache public results only when not fresh bypass
        if not is_cache_bypassed:
            _DECK_CACHE[cache_key] = {"data": payload, "time": now_ts}

        if is_cache_bypassed:
            headers = {
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "X-Cache": "BYPASS"
            }
        else:
            headers = {
                "Cache-Control": "public, s-maxage=300, stale-while-revalidate=600, stale-if-error=86400",
                "X-Cache": "MISS"
            }
        return JSONResponse(content=payload, headers=headers)

    except Exception as e:
        logger.error(f"Error serving /api/deck: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/deck/{trend_id}/reels")
def get_deck_trend_reels(trend_id: int):
    """
    Public endpoint returning top reels (up to 6) associated with a deck trend.
    Queries by indexed audio_id, falls back to audio_title.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")

    try:
        t_res = supabase.table("trends").select("id, audio_id, audio_title, audio_artist").eq("id", trend_id).limit(1).execute()
        if not t_res.data:
            return JSONResponse(content={"reels": []})

        trend = t_res.data[0]
        audio_id = trend.get("audio_id")
        title = trend.get("audio_title")

        candidates = []
        seen_ids = set()

        # 1. Fetch candidates by audio_id (primary index)
        if audio_id:
            r_res = supabase.table("reels")\
                .select("id, reel_id, owner_username, view_count, like_count, thumbnail_url, video_url, created_at, scraped_at, posted_at")\
                .eq("audio_id", str(audio_id))\
                .order("view_count", desc=True)\
                .limit(40)\
                .execute()
            for r in (r_res.data or []):
                if r["id"] not in seen_ids:
                    seen_ids.add(r["id"])
                    candidates.append(r)

        # 2. Also pool candidates by audio_title to catch reels scraped under matching title
        if title:
            r_res2 = supabase.table("reels")\
                .select("id, reel_id, owner_username, view_count, like_count, thumbnail_url, video_url, created_at, scraped_at, posted_at")\
                .eq("audio_title", title)\
                .order("view_count", desc=True)\
                .limit(40)\
                .execute()
            for r in (r_res2.data or []):
                if r["id"] not in seen_ids:
                    seen_ids.add(r["id"])
                    candidates.append(r)

        # 3. Sort candidates by engagement (views + 3 * likes)
        def _reel_score(r):
            views = int(r.get("view_count") or 0)
            likes = int(r.get("like_count") or 0)
            return views + 3 * likes

        candidates.sort(key=_reel_score, reverse=True)

        # 4. Creator Deduplication: keep only the single best reel per creator account
        # Prevents one account from dominating all 6 preview slots
        deduped_by_creator = []
        seen_creators = set()
        for r in candidates:
            creator = (r.get("owner_username") or "").lower().strip()
            if creator and creator not in {"creator", "unknown", "none", ""}:
                if creator in seen_creators:
                    continue
                seen_creators.add(creator)
            deduped_by_creator.append(r)

        # 5. Quality Filter (Anti-Trash Gate):
        # Exclude zero-view empty placeholders if valid reels exist, keeping up to 6 top reels
        valid_reels = [r for r in deduped_by_creator if int(r.get("view_count") or 0) > 0]
        final_reels = (valid_reels if valid_reels else deduped_by_creator)[:6]

        items = []
        for r in final_reels:
            rid = r.get("reel_id")
            views = int(r.get("view_count") or 0)
            likes = int(r.get("like_count") or 0)
            thumb = f"/api/deck/thumb/{rid}" if rid else r.get("thumbnail_url")
            video_url = r.get("video_url")
            # Only valid, unexpired MP4 CDN streams
            is_valid_mp4 = bool(video_url and (".mp4" in video_url or "cdninstagram" in video_url) and _is_safe_unexpired_video_url(video_url))

            items.append({
                "id": r["id"],
                "reel_id": rid,
                "owner_username": r.get("owner_username") or "creator",
                "view_count": views,
                "like_count": likes,
                "is_high_engagement": views >= 25000,
                "thumbnail_url": thumb,
                "video_url": video_url if is_valid_mp4 else None,
                "instagram_url": f"https://www.instagram.com/reel/{rid}/" if rid else None,
                "embed_url": f"https://www.instagram.com/p/{rid}/embed/" if rid else None
            })

        return JSONResponse(content={"reels": items})
    except Exception as e:
        logger.error(f"Error fetching reels for trend {trend_id}: {e}", exc_info=True)
        return JSONResponse(content={"reels": []})


def _is_safe_unexpired_video_url(url: Optional[str]) -> bool:
    """Check if video_url is valid and not an expired Instagram CDN URL."""
    if not url or not isinstance(url, str):
        return False
    if "cdninstagram.com" in url or "fbcdn.net" in url:
        m = re.search(r"[?&]oe=([0-9a-fA-F]+)", url)
        if m:
            try:
                expiry = int(m.group(1), 16)
                if time.time() >= expiry - 60:
                    return False
            except Exception:
                return False
    return True


def _is_safe_audio_stream_url(url: Optional[str]) -> bool:
    """Check if URL is a genuine audio stream (e.g. mp3/m4a/aac) and not an Instagram CDN video URL."""
    if not url or not isinstance(url, str):
        return False
    u = url.lower()
    if "cdninstagram.com" in u or "fbcdn.net" in u or ".mp4" in u:
        return False
    return u.endswith((".m4a", ".mp3", ".aac", ".ogg")) or "audio-ssl.itunes.apple.com" in u or "mzstatic.com" in u


@router.get("/api/deck/{trend_id}/stream")
def get_deck_trend_audio_stream(trend_id: int):
    """
    Public audio stream resolver for deck cards: returns verified public stream URL.
    Strictly filters out Instagram CDN video URLs to prevent client 403 errors.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")

    try:
        t_res = supabase.table("trends").select("id, audio_id, audio_title").eq("id", trend_id).limit(1).execute()
        if not t_res.data:
            return JSONResponse(content={"audio_url": None})

        trend = t_res.data[0]
        audio_id = trend.get("audio_id")
        title = trend.get("audio_title")

        if audio_id:
            r_res = supabase.table("reels").select("video_url").eq("audio_id", str(audio_id)).not_.is_("video_url", "null").limit(5).execute()
            for r in (r_res.data or []):
                v_url = r.get("video_url")
                if v_url and _is_safe_audio_stream_url(v_url):
                    return JSONResponse(content={"audio_url": v_url})

        if title:
            r_res = supabase.table("reels").select("video_url").eq("audio_title", title).not_.is_("video_url", "null").limit(5).execute()
            for r in (r_res.data or []):
                v_url = r.get("video_url")
                if v_url and _is_safe_audio_stream_url(v_url):
                    return JSONResponse(content={"audio_url": v_url})

        return JSONResponse(content={"audio_url": None})
    except Exception as e:
        logger.error(f"Error fetching audio stream for trend {trend_id}: {e}", exc_info=True)
        return JSONResponse(content={"audio_url": None})


_THUMBNAIL_CACHE: Dict[str, bytes] = {}


@router.get("/api/deck/thumb/{reel_id}")
def get_reel_thumbnail_image(reel_id: str):
    """
    Returns real, fresh JPEG thumbnail image for an Instagram reel.
    Caches in memory with 24-hour public client cache headers.
    """
    clean_id = (reel_id or "").strip()
    if not clean_id or not re.match(r"^[a-zA-Z0-9_-]{3,40}$", clean_id):
        raise HTTPException(status_code=400, detail="Invalid reel_id format")

    if clean_id in _THUMBNAIL_CACHE:
        return Response(
            content=_THUMBNAIL_CACHE[clean_id],
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400, s-maxage=86400"}
        )

    url = f"https://www.instagram.com/p/{clean_id}/media/?size=m"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read()
            if len(data) > 500:
                if len(_THUMBNAIL_CACHE) > 1000:
                    _THUMBNAIL_CACHE.pop(next(iter(_THUMBNAIL_CACHE)))
                _THUMBNAIL_CACHE[clean_id] = data
                return Response(
                    content=data,
                    media_type="image/jpeg",
                    headers={"Cache-Control": "public, max-age=86400, s-maxage=86400"}
                )
    except Exception as e:
        logger.warning(f"Failed to fetch reel thumbnail for {clean_id}: {e}")

    raise HTTPException(status_code=404, detail="Thumbnail not available")


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

    # In-memory edge cache lookup for explore
    cache_k = f"{mode}:{cursor or 0}:{limit}:{stage or ''}:{include_expired}:{language or ''}:{niche or ''}:{search or ''}"
    now_ts = time.time()
    if cache_k in _EXPLORE_CACHE:
        entry = _EXPLORE_CACHE[cache_k]
        if now_ts - entry.get("time", 0) < 60:
            return JSONResponse(content=entry["data"], headers={"X-Cache": "HIT-MEM", "Cache-Control": "public, max-age=60"})

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
        elif include_expired or (niche and niche.lower() != "all") or (language and language.lower() != "all") or (search and search.strip()):
            # When any filter is applied or include_expired is true, include expired audios
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

        if language and language.lower() != "all":
            l_clean = sanitize_postgrest_value(language).lower()
            if l_clean:
                q = q.or_(f"language_final.eq.{l_clean},language.eq.{l_clean}")

        if niche and niche.lower() != "all":
            n_clean = sanitize_postgrest_value(niche).lower()
            if n_clean:
                q = q.or_(f"semantic_niches.cs.{{{n_clean}}},niche_tag.eq.{n_clean}")

        if search and search.strip():
            s_term = sanitize_postgrest_value(search)
            if s_term:
                q = q.or_(f"audio_title.ilike.%{s_term}%,audio_artist.ilike.%{s_term}%")

        if cursor:
            q = q.lt("id", cursor)

        # Over-fetch candidate pool to ensure mode filtering leaves full limit
        fetch_limit = min(max(limit * 3, 60), 200)
        q = q.order("id", desc=True).limit(fetch_limit)
        res = q.execute()

        total_count = res.count or 0
        rows = res.data or []

        # Filter mode in memory strictly (language + origin double-gate)
        if mode.lower() == "india":
            rows = [
                r for r in rows
                if (r.get("language_final") or r.get("language") or "").strip().lower() in INDIAN_LANGUAGES
                and (r.get("language_final") or r.get("language") or "").strip().lower() not in GLOBAL_LANGUAGES
                and (r.get("trend_origin") or "").strip().upper() not in ("GLOBAL", "KR", "BR", "ES", "RU")
            ]
        elif mode.lower() == "global":
            rows = [
                r for r in rows
                if (r.get("language_final") or r.get("language") or "").strip().lower() in GLOBAL_LANGUAGES
                and (r.get("language_final") or r.get("language") or "").strip().lower() not in INDIAN_LANGUAGES
                and (r.get("trend_origin") or "").strip().upper() != "IN"
            ]

        # Slice to requested limit after mode filtering
        rows = rows[:limit]

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
                "used_for": used_for if used_for else None,
                "used_for_note": r.get("used_for_note") or None,
                "why_this_works": r.get("why_this_works") or None
            })

        next_cursor = items[-1]["id"] if items and len(items) == limit else None

        response_payload = {
            "total": total_count,
            "next_cursor": next_cursor,
            "trends": items
        }

        # Save to memory cache
        _EXPLORE_CACHE[cache_k] = {"time": time.time(), "data": response_payload}
        if len(_EXPLORE_CACHE) > 300:
            oldest = min(_EXPLORE_CACHE.keys(), key=lambda k: _EXPLORE_CACHE[k].get("time", 0))
            _EXPLORE_CACHE.pop(oldest, None)

        return JSONResponse(content=response_payload, headers={"X-Cache": "MISS", "Cache-Control": "public, max-age=60"})

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
