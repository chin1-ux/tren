from fastapi import APIRouter, HTTPException, Depends, Request, Header, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import os, json, time, logging, traceback
from api_globals import *
from api_globals import _PEAKED_TRENDS_CACHE, standard_queue, _normalize_trends, _trend_priority_key, _resolve_user
from schemas import *
import niche_relevance_engine
router = APIRouter()

def _apply_languages_filter(q, language: Optional[str] = None, languages: Optional[str] = None):
    lang_list = []
    if languages and languages.strip():
        lang_list = [l.strip().lower() for l in languages.split(",") if l.strip()]
    elif language and language.strip() and language.lower() != "all":
        lang_list = [language.strip().lower()]

    if not lang_list:
        return q

    filter_or = f"language_final.in.({','.join(lang_list)}),and(language_final.is.null,language.in.({','.join(lang_list)}))"
    return q.or_(filter_or)


@router.get("/api/trends")
@router.get("/api/trends/rising")
@limiter.limit("60/minute")
def get_trends(
    request: Request,
    language: Optional[str] = None,
    languages: Optional[str] = None,
    sort: Optional[str] = "newest",
    niche: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """
    Fetch RISING trends from Supabase.
    Optional filters: ?language=hi & ?languages=hi,pa,en & sort=velocity|time_left|newest & niche=fitness
    """
    lang_key = languages or language or "all"
    niche_key = niche or "all"
    user_email = current_user if current_user else "guest"
    cache_key = f"trends:{lang_key}:{sort}:{niche_key}:{user_email}"
    
    # Try fetching from Redis cache first
    if standard_queue and standard_queue.connection:
        try:
            cached_data = standard_queue.connection.get(cache_key)
            parsed_cache = json.loads(cached_data) if cached_data else None
            if parsed_cache and len(parsed_cache) > 0:
                logger.info(f"Serving trends from cache for key: {cache_key}")
                headers = {
                    "Cache-Control": "public, max-age=60",
                    "X-Skipped-Local-Fallback": "true",
                }
                return JSONResponse(content=parsed_cache, headers=headers)
        except Exception as e:
            logger.error(f"Redis fetch error: {e}")


    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    try:
        # Load user configuration for personalization
        user_niche = "all"
        user_lang = "all"
        user_plan = "free"
        
        # Airtight guest bypass guard: Must be valid email containing @ and not default guest
        if current_user and isinstance(current_user, str) and "@" in current_user and current_user != "guest@trendrop.app":
            try:
                user_plan = PlanEnforcement.get_user_plan(current_user)
                user_data = get_cached_user_profile(current_user)
                    
                # Query user_preferences DB for personalized feed
                prefs_res = supabase.table("user_preferences").select("niches, languages, preferred_languages, regions, state").eq("email", current_user).execute()
                if prefs_res.data:
                    prefs = prefs_res.data[0]
                    if prefs.get("niches") and len(prefs["niches"]) > 0:
                        user_niche = prefs["niches"][0]
                    pref_langs = prefs.get("preferred_languages") or prefs.get("languages")
                    if not languages and not language and pref_langs and len(pref_langs) > 0:
                        languages = ",".join(pref_langs)
            except Exception as e:
                logger.warning(f"Error querying user profile/preferences for personalization: {e}")

        # Get delay hours from module-level cached tiers
        delay_hours = get_cached_tier_delay(user_plan)

        _VALID_LLM = "llm_classification_status.in.(completed,not_needed,skipped_local_fallback,pending,failed,verified),llm_classification_status.is.null"
        q = supabase.table("trends").select("*").eq("status", "rising").eq("is_voiceover", False).eq("is_seed_data", False).or_(_VALID_LLM).gt("window_hours_remaining", 0)

        # 7-day retention gate for Rising tab (prevents ancient trends from clogging feed)
        rising_cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        q = q.gte("created_at", rising_cutoff)

        q = _apply_languages_filter(q, language, languages)

        if niche and niche != "all":
            q = q.or_(f"niche_tag.eq.{niche},semantic_niches.cs.{{{niche}}}")

        # Server-side gating data delay filter: Only apply if user is on free plan and we have sufficient trends
        if delay_hours > 0:
            time_cutoff = (datetime.now(timezone.utc) - timedelta(hours=delay_hours)).isoformat()
            q_delayed = q.lte("created_at", time_cutoff)
            res_delayed = execute_supabase_get(q_delayed)
            if res_delayed.data and len(res_delayed.data) > 0:
                q = q_delayed

        if sort == "time_left":
            q = q.order("window_hours_remaining", desc=False)
        elif sort == "velocity":
            q = q.order("velocity_avg", desc=True)
        else:
            # Default: newest audio detected by Trendrop pipeline on top
            q = q.order("first_detected_at", desc=True)

        skipped_local_fallback = True
        res = execute_supabase_get(q)
        trends = _normalize_trends(res.data or [])

        # Fallback: If delay_hours or strict rising filter returns 0 trends (e.g. fresh breakout trends detected <24h ago),
        # fallback to querying active (rising + emerging) trends so free/guest users never see an empty rail.
        if not trends:
            skipped_local_fallback = False
            q_fb = supabase.table("trends").select("*").in_("status", ["rising", "emerging"]).eq("is_voiceover", False).eq("is_seed_data", False).or_(_VALID_LLM).gt("window_hours_remaining", 0)
            if language and language != "all":
                q_fb = q_fb.or_(f"language_final.eq.{language},and(language_final.is.null,language.eq.{language})")
            res_fb = execute_supabase_get(q_fb)
            trends = _normalize_trends(res_fb.data or [])


        # --- 70/30 Distribution: Indian/regional first, English/global after ---
        # Prioritise local trends but keep global variety.
        # Only applied when no specific language filter is active.
        if not language or language == "all":
            _INDIAN_LANGS = {"hi", "ta", "te", "mr", "kn", "bn", "pa", "bho", "hne", "mai", "or", "", None}
            indian = [t for t in trends if (t.get("language") or "") in _INDIAN_LANGS
                      or (t.get("discovery_source") or "regional") != "global"]
            english = [t for t in trends if t not in indian]
            trends = indian + english

        # Wire C5: Inject niche adaptations using the engine for personalized feed
        for t in trends:
            if user_niche and user_niche not in ["all", "general"]:
                if not t.get("niche_relevance"):
                    t["niche_relevance"] = niche_relevance_engine.compute_niche_relevance(t)
                
                score = t["niche_relevance"].get(user_niche, 0.0)
                brief = niche_relevance_engine.generate_adaptation_brief(t, user_niche, score)
                
                if brief:
                    if not t.get("adaptation_briefs"):
                        t["adaptation_briefs"] = {}
                    t["adaptation_briefs"][user_niche] = brief

        if sort == "opportunity":
            trends.sort(key=lambda t: _trend_priority_key(t, user_niche, user_lang), reverse=True)
        elif sort == "time_left":
            trends.sort(key=lambda t: t.get("window_hours_remaining") or 0)
        elif sort == "velocity":
            trends.sort(key=lambda t: t.get("velocity_avg") or 0.0, reverse=True)
        else:
            # Default or sort=="newest": strictly newest audio detected on top
            trends.sort(key=lambda t: t.get("first_detected_at") or "", reverse=True)

        # Cache the result in Redis for 5 minutes
        if standard_queue and standard_queue.connection:
            try:
                standard_queue.connection.setex(cache_key, 300, json.dumps(trends))
            except Exception as e:
                logger.error(f"Redis cache write error: {e}")
                
        headers = {
            "Cache-Control": "public, max-age=300",
            "X-Skipped-Local-Fallback": "true" if skipped_local_fallback else "false",
        }
        return JSONResponse(content=trends, headers=headers)
    except Exception as e:
        logger.error(f"Error fetching trends: {e}", exc_info=True)

        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/trends/emerging")
@limiter.limit("60/minute")
def get_emerging_trends(
    request: Request, 
    language: Optional[str] = None,
    languages: Optional[str] = None, 
    current_user: str = Depends(get_current_user)
):
    """
    Fetch EMERGING trends — the early access feed (pre-viral, 0–6h window).
    Pro/Agency feature only.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    try:
        # Load user config for personalization
        user_niche = "all"
        user_lang = "all"
        user_id = None
        if current_user and current_user != "guest@trendrop.app":
            try:
                user_data = get_cached_user_profile(current_user)
                if user_data:
                    user_niche = user_data.get("niche") or "all"
                    user_lang = user_data.get("language_preference") or "all"
                    user_id = user_data.get("user_id")
            except Exception as e:
                logger.warning(f"Error querying user profile: {e}")

        _VALID_LLM = "llm_classification_status.in.(completed,not_needed,skipped_local_fallback,pending,failed,verified),llm_classification_status.is.null"
        q = supabase.table("trends").select("*").eq("status", "emerging").eq("is_voiceover", False).eq("is_seed_data", False).or_(_VALID_LLM)
        
        # 48-hour retention gate for Emerging tab (only fresh pre-viral trends)
        emerging_cutoff = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        q = q.or_(
            f"first_detected_at.gte.{emerging_cutoff},"
            f"and(first_detected_at.is.null,created_at.gte.{emerging_cutoff})"
        )

        q = _apply_languages_filter(q, language, languages)
        q = q.order("velocity_avg", desc=True)
        res = q.execute()
        trends = _normalize_trends(res.data or [])

        # Fallback blending: if emerging count is below 5, blend in fresh rising/resurging trends detected in last 48h
        if len(trends) < 5:
            try:
                q_blend = supabase.table("trends").select("*").in_("status", ["rising", "resurging"]).eq("is_voiceover", False).eq("is_seed_data", False).gte("first_detected_at", emerging_cutoff)
                q_blend = _apply_languages_filter(q_blend, language, languages)
                res_blend = q_blend.order("first_detected_at", desc=True).limit(10 - len(trends)).execute()
                blended = _normalize_trends(res_blend.data or [])
                existing_ids = {t.get("id") for t in trends}
                for b in blended:
                    if b.get("id") not in existing_ids:
                        b["is_recently_promoted_fallback"] = True
                        trends.append(b)
            except Exception as _blend_err:
                logger.warning(f"Emerging fallback blending error: {_blend_err}")

        # --- 70/30 Distribution for Emerging tab ---
        if not language or language == "all":
            _INDIAN_LANGS = {"hi", "ta", "te", "mr", "kn", "bn", "pa", "bho", "hne", "mai", "or"}
            indian = [t for t in trends if (t.get("language") or "") in _INDIAN_LANGS
                      or (t.get("discovery_source") or "") == "regional"]
            english = [t for t in trends if t not in indian]
            trends = indian + english

        trends.sort(key=lambda t: _trend_priority_key(t, user_niche, user_lang), reverse=True)
        
        # Add user watermark ID to each trend for leak tracing
        if user_id:
            for trend in trends:
                trend["user_watermark_id"] = user_id
        
        return trends
    except Exception as e:
        logger.error(f"Error fetching emerging trends: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")



def _get_db_audio_trends_fallback() -> list:
    """
    Fallback query when Spotify API is unconfigured or unavailable.
    Fetches high-quality active audio trends from Supabase DB, filtered by:
    - status IN ('emerging', 'rising')
    - is_seed_data = False
    - llm_classification_status IN ('completed', 'not_needed', 'skipped_local_fallback')
    - saturation_penalty < 0.7 (filters out over-saturated tracks)
    Returns formatted SpotifyTrack-compatible dicts with prediction scores.
    """
    if not supabase:
        return []
    try:
        res = (
            supabase.table("trends")
            .select("id, audio_title, audio_artist, status, velocity_avg, creator_fit_score, hook_retention_score, saturation_penalty, window_hours_remaining, optimal_post_hour_ist, created_at, first_detected_at")
            .in_("status", ["emerging", "rising"])
            .eq("is_seed_data", False)
            .in_("llm_classification_status", ["completed", "not_needed", "skipped_local_fallback", "verified"])
            .order("velocity_avg", desc=True)
            .limit(30)
            .execute()
        )
        data = res.data or []
        fallback_tracks = []
        for idx, t in enumerate(data):
            fit = t.get("creator_fit_score") if isinstance(t.get("creator_fit_score"), (int, float)) else 0.8
            hook = t.get("hook_retention_score") if isinstance(t.get("hook_retention_score"), (int, float)) else 0.75
            sat = t.get("saturation_penalty") if isinstance(t.get("saturation_penalty"), (int, float)) else 0.2
            
            # Recency / Saturation Filter: filter out over-saturated tracks
            if sat >= 0.7:
                continue

            score = int(100 * min(1.0, max(0.0, 0.4 * fit + 0.35 * hook + 0.25 * (1.0 - sat))))
            hours_left = t.get("window_hours_remaining")
            post_hour = t.get("optimal_post_hour_ist") or (16 + (idx % 6))
            timing = f"{int(post_hour):02d}:00 IST" if post_hour else "18:00 IST"

            rec_action = (
                "WINDOW CLOSED" if hours_left is not None and hours_left <= 0
                else "CREATE CONTENT NOW" if score >= 80
                else "POST SOON" if score >= 65
                else "EARLY ENTRY WINDOW"
            )

            fallback_tracks.append({
                "id": t.get("id"),
                "audio_title": t.get("audio_title") or "Emerging Audio",
                "audio_artist": t.get("audio_artist") or "Creator Sound",
                "spotify_id": None,
                "market": "IN",
                "market_label": "🇮🇳 India",
                "rank": idx + 1,
                "popularity": score,
                "release_date": None,
                "data_source": "supabase_cache",
                "prediction": {
                    "combined_score": score,
                    "prediction": f"Emerging {t.get('status', 'rising').capitalize()}",
                    "optimal_timing": timing,
                    "reach_multiplier": f"{score}%",
                    "recommended_action": rec_action,
                }
            })
        return fallback_tracks
    except Exception as e:
        logger.error(f"Error executing _get_db_audio_trends_fallback: {e}", exc_info=True)
        return []


def _canonical_spotify_key(title: str, artist: str) -> str:
    import re
    t = re.sub(r'[^\w]', '', (title or "").lower(), flags=re.UNICODE).strip()
    a = re.sub(r'[^\w]', '', (artist or "").lower(), flags=re.UNICODE).strip()
    if not t and not a:
        return f"raw:{title}:{artist}"
    return f"{t}:{a}"


@router.get("/api/spotify/viral")
@limiter.limit("60/minute")
def get_spotify_viral_trends(
    request: Request,
    country: Optional[str] = "all",
    current_user: str = Depends(get_current_user)
):
    """
    Fetch Spotify Viral trends split into two distinct sections:
    1. already_trending: Active Instagram audio trends (max 8) with delay gating for free tier.
    2. new_on_spotify: Fresh search-ingested tracks from Spotify search cache (max 25).
    Guarantees strict ZERO OVERLAP between the two sections.
    """
    user_plan = "free"
    if current_user and isinstance(current_user, str) and "@" in current_user and current_user != "guest@trendrop.app":
        try:
            user_plan = PlanEnforcement.get_user_plan(current_user)
        except Exception as e:
            logger.warning(f"Error querying user profile for Spotify viral gating: {e}")

    delay_hours = get_cached_tier_delay(user_plan)

    if not supabase:
        return JSONResponse(
            content={"already_trending": [], "new_on_spotify": []},
            headers={"X-Fallback-Reason": "supabase_not_configured", "X-Data-Source": "none"}
        )

    try:
        # --- Section 1: Already Trending on Instagram (max 8) ---
        q_trending = supabase.table("trends").select("*") \
            .in_("status", ["rising", "emerging", "resurging", "peaked"]) \
            .eq("is_voiceover", False) \
            .eq("is_seed_data", False) \
            .gt("window_hours_remaining", 0)

        if delay_hours > 0:
            time_cutoff = (datetime.now(timezone.utc) - timedelta(hours=delay_hours)).isoformat()
            q_trending_delayed = q_trending.lte("created_at", time_cutoff)
            res_delayed = execute_supabase_get(q_trending_delayed) if 'execute_supabase_get' in globals() else q_trending_delayed.execute()
            if res_delayed.data and len(res_delayed.data) > 0:
                q_trending = q_trending_delayed

        q_trending = q_trending.order("velocity_avg", desc=True).limit(8)
        res_trending = execute_supabase_get(q_trending) if 'execute_supabase_get' in globals() else q_trending.execute()
        raw_trending = res_trending.data or []

        already_trending = []
        trending_keys = set()

        for item in raw_trending:
            title = item.get("audio_title") or item.get("title") or "Emerging Sound"
            artist = item.get("audio_artist") or item.get("artist") or "Creator Sound"
            key = _canonical_spotify_key(title, artist)
            if key != ":":
                trending_keys.add(key)

            aid = item.get("instagram_audio_id") or item.get("audio_id") or item.get("id")
            already_trending.append({
                "id": item.get("id"),
                "audio_title": title,
                "audio_artist": artist,
                "instagram_audio_id": aid,
                "instagram_audio_url": item.get("instagram_audio_url") or (f"https://www.instagram.com/reels/audio/{aid}/" if aid else None),
                "status": item.get("status") or "rising",
                "velocity_avg": item.get("velocity_avg"),
                "window_hours_remaining": item.get("window_hours_remaining"),
                "language": item.get("language_final") or item.get("language"),
                "data_source": "ig_trends"
            })

        # --- Section 2: New on Spotify (max 25) ---
        q_sp = supabase.table("spotify_feed_cache").select("*").eq("data_source", "spotify_search").order("release_date", desc=True).limit(60)
        res_sp = execute_supabase_get(q_sp) if 'execute_supabase_get' in globals() else q_sp.execute()
        sp_items = res_sp.data or []
        if not sp_items:
            q_sp_fallback = supabase.table("spotify_feed_cache").select("*").order("release_date", desc=True).limit(60)
            res_sp = execute_supabase_get(q_sp_fallback) if 'execute_supabase_get' in globals() else q_sp_fallback.execute()
            sp_items = res_sp.data or []

        new_on_spotify = []
        for item in sp_items:
            title = item.get("title") or item.get("audio_title") or ""
            artist = item.get("artist") or item.get("audio_artist") or ""
            key = _canonical_spotify_key(title, artist)

            # ZERO OVERLAP ENFORCEMENT: Skip any track already in Instagram trending!
            if key in trending_keys:
                continue

            sp_id = item.get("spotify_id")
            new_on_spotify.append({
                "id": item.get("id") or sp_id,
                "audio_title": title,
                "audio_artist": artist,
                "spotify_id": sp_id,
                "spotify_url": item.get("spotify_url") or (f"https://open.spotify.com/track/{sp_id}" if sp_id else None),
                "cover_art_url": item.get("image_url") or item.get("cover_art_url"),
                "release_date": item.get("release_date"),
                "ig_reel_count": item.get("ig_reel_count") or 0,
                "popularity": item.get("popularity") or 0,
                "data_source": item.get("data_source") or "spotify_search"
            })

            if len(new_on_spotify) >= 25:
                break

        return JSONResponse(
            content={
                "already_trending": already_trending,
                "new_on_spotify": new_on_spotify
            },
            headers={
                "X-Already-Trending-Count": str(len(already_trending)),
                "X-New-Spotify-Count": str(len(new_on_spotify)),
                "X-User-Plan": user_plan
            }
        )

    except Exception as e:
        logger.error(f"spotify/viral: unexpected error — {e}", exc_info=True)
        return JSONResponse(
            content={"already_trending": [], "new_on_spotify": []},
            headers={"X-Fallback-Reason": f"error:{type(e).__name__}", "X-Data-Source": "none"}
        )



@router.get("/api/trends/all-active")
@limiter.limit("60/minute")
def get_all_active_trends(
    request: Request, 
    current_user: str = Depends(get_current_user),
    _phone_check: str = Depends(require_phone_verified),
    _plan_check: str = Depends(require_feature("unlimited_trends")),
    _usage_log: str = Depends(log_endpoint_usage("unlimited_trends"))
):
    """Returns both emerging + rising trends merged. Pro/Agency feature only."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    try:
        res = supabase.table("trends").select("*").in_("status", ["emerging", "rising"]).eq("is_seed_data", False).in_("llm_classification_status", ["completed", "not_needed", "skipped_local_fallback", "verified"]).order("velocity_avg", desc=True).execute()
        trends = _normalize_trends(res.data or [])
        trends.sort(key=_trend_priority_key, reverse=True)
        return trends
    except Exception as e:
        logger.exception(f"Error fetching all-active trends: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/trends/peaked")
@limiter.limit("60/minute")
def get_peaked_trends(
    request: Request, 
    language: Optional[str] = None, 
    languages: Optional[str] = None,
    limit: Optional[int] = None,
    current_user: str = Depends(get_current_user)
):
    """
    Fetch PEAKED trends — trends that have peaked but still have value.
    These are trends that dropped below 60% of their peak velocity.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
        
    lang_key = languages or language or "all"
    cache_key = f"peaked:{lang_key}:{limit}"
    
    # Check in-memory cache (5 minute TTL)
    now = datetime.now().timestamp()
    if cache_key in _PEAKED_TRENDS_CACHE:
        entry = _PEAKED_TRENDS_CACHE[cache_key]
        if now - entry['time'] < 300:
            logger.info(f"Serving peaked trends from in-memory cache for key: {cache_key}")
            headers = {"X-Cache": "HIT", "Cache-Control": "public, max-age=300"}
            return JSONResponse(content=entry['data'], headers=headers)
            
    try:
        q = supabase.table("trends").select("*").eq("status", "peaked").eq("is_seed_data", False).in_("llm_classification_status", ["completed", "not_needed", "skipped_local_fallback", "verified"])
        
        # 14-day retention gate for Peaked tab (max 14 days post-peak)
        peaked_cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        q = q.or_(
            f"first_detected_at.gte.{peaked_cutoff},"
            f"and(first_detected_at.is.null,created_at.gte.{peaked_cutoff})"
        )

        q = _apply_languages_filter(q, language, languages)
        q = q.order("first_detected_at", desc=True)
        if limit:
            q = q.limit(limit)
        res = q.execute()
        trends = _normalize_trends(res.data or [])
        trends.sort(key=_trend_priority_key, reverse=True)
        
        # Save to cache
        _PEAKED_TRENDS_CACHE[cache_key] = {'time': now, 'data': trends}
        
        headers = {"X-Cache": "MISS", "Cache-Control": "public, max-age=300"}
        return JSONResponse(content=trends, headers=headers)
    except Exception as e:
        logger.error(f"Error fetching peaked trends: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/trends/resurging")
@limiter.limit("60/minute")
def get_resurging_trends(
    request: Request,
    language: Optional[str] = None,
    languages: Optional[str] = None,
    limit: Optional[int] = None,
    current_user: str = Depends(get_current_user)
):
    """
    Fetch RESURGING trends — audio that previously peaked or expired and has
    come back with sustained new signal. Sorted by status_changed_at DESC (most recent resurgence on top).
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    try:
        resurging_cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        valid_llm_statuses = ["completed", "not_needed", "skipped_local_fallback", "pending", "failed", "verified"]
        date_filter = (
            f"first_detected_at.gte.{resurging_cutoff},"
            f"and(first_detected_at.is.null,created_at.gte.{resurging_cutoff})"
        )
        q = (
            supabase.table("trends")
            .select("*")
            .eq("status", "resurging")
            .eq("is_seed_data", False)
            .gte("reel_count", 3)
            .or_(
                f"llm_classification_status.in.({','.join(valid_llm_statuses)}),llm_classification_status.is.null"
            )
            .or_(date_filter)
        )
        q = _apply_languages_filter(q, language, languages)
        q = q.order("status_changed_at", desc=True)
        limit_val = min(limit or 50, 50)
        q = q.limit(limit_val)
        res = q.execute()
        trends = _normalize_trends(res.data or [])
        trends.sort(key=lambda t: t.get("status_changed_at") or t.get("created_at") or "", reverse=True)
        headers = {"Cache-Control": "public, max-age=120", "X-Status-Filter": "resurging"}
        return JSONResponse(content=trends, headers=headers)
    except Exception as e:
        logger.error(f"Error fetching resurging trends: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/trends/expired")
@limiter.limit("60/minute")
def get_expired_trends(
    request: Request, 
    language: Optional[str] = None, 
    limit: Optional[int] = None,
    current_user: str = Depends(get_current_user),
):
    """
    Fetch EXPIRED trends — trends that have passed their window or aged out.
    These are trends that are no longer active but may still have historical value.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    try:
        q = supabase.table("trends").select("*").eq("status", "expired").eq("is_seed_data", False).in_("llm_classification_status", ["completed", "not_needed", "skipped_local_fallback", "verified"])
        
        # 30-day retention gate for Expired tab (max 30 days historical archive)
        expired_cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        q = q.or_(
            f"first_detected_at.gte.{expired_cutoff},"
            f"and(first_detected_at.is.null,created_at.gte.{expired_cutoff})"
        )
        if language and language != "all":
            q = q.eq("language", language)
        q = q.order("first_detected_at", desc=True)
        if limit:
            q = q.limit(limit)
        res = q.execute()
        trends = _normalize_trends(res.data or [])
        return trends
    except Exception as e:
        logger.error(f"Error fetching expired trends: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/trends/audio-scores")
@limiter.limit("60/minute")
def get_audio_trend_scores_api(
    request: Request,
    current_user: str = Depends(get_current_user),
    _plan_check: str = Depends(require_feature("advanced_analytics")),
    _usage_log: str = Depends(log_endpoint_usage("advanced_analytics"))
):
    """Returns the latest audio trend scores, excluding INSUFFICIENT_DATA. Pro/Agency feature only."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    try:
        latest_res = supabase.table("audio_trend_scores") \
            .select("scrape_cycle_at") \
            .order("scrape_cycle_at", desc=True) \
            .limit(1) \
            .execute()
        if not latest_res.data:
            return []
        
        latest_cycle = latest_res.data[0]["scrape_cycle_at"]
        
        res = supabase.table("audio_trend_scores") \
            .select("*") \
            .eq("scrape_cycle_at", latest_cycle) \
            .neq("lifecycle_stage", "INSUFFICIENT_DATA") \
            .limit(100) \
            .execute()
        
        # Sort in memory since None values for velocities could exist
        data = res.data or []
        sorted_data = sorted(
            data, 
            key=lambda x: x.get("creator_velocity") if x.get("creator_velocity") is not None else -99999.0, 
            reverse=True
        )
        return sorted_data
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/trends/by-language/{lang}")
@limiter.limit("60/minute")
def get_trends_by_language(
    request: Request, 
    lang: str, 
    current_user: str = Depends(get_current_user),
    _plan_check: str = Depends(require_feature("unlimited_trends"))
):
    """Returns trends filtered by specific language code (hi, kn, ta, te, en, ...)."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    try:
        skipped_local_fallback = True
        res = supabase.table("trends") \
            .select("*") \
            .in_("status", ["emerging", "rising"]) \
            .eq("is_seed_data", False) \
            .in_("llm_classification_status", ["completed", "not_needed", "skipped_local_fallback", "verified"]) \
            .eq("language", lang) \
            .order("velocity_avg", desc=True) \
            .limit(100) \
            .execute()
        trends = _normalize_trends(res.data or [])
        if not trends:
            skipped_local_fallback = False
            res_fb = supabase.table("trends") \
                .select("*") \
                .eq("language", lang) \
                .order("velocity_avg", desc=True) \
                .limit(100) \
                .execute()
            trends = _normalize_trends(res_fb.data or [])

        trends.sort(key=_trend_priority_key, reverse=True)
        headers = {"X-Skipped-Local-Fallback": "true" if skipped_local_fallback else "false"}
        return JSONResponse(content=trends, headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/trends/peaking")
@limiter.limit("60/minute")
def get_peaking_trends(
    request: Request, 
    limit: int = 10, 
    current_user: str = Depends(get_current_user),
    _plan_check: str = Depends(require_feature("advanced_analytics"))
):
    """
    Get trends that are currently peaking based on real metrics
    Uses velocity acceleration, window efficiency, and creator count
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    
    try:
        from datetime import timedelta
        
        # Get active trends with velocity data
        time_threshold = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        
        trends_res = supabase.table('trends') \
            .select('*') \
            .in_('status', ['emerging', 'rising']) \
            .eq('is_seed_data', False) \
            .gte('first_detected_at', time_threshold) \
            .order('velocity_avg', desc=True) \
            .limit(limit * 2) \
            .execute()
        
        trends = trends_res.data or []
        
        # BATCH QUERY: Get all snapshots in one query to avoid N+1 problem
        trend_ids = [t['id'] for t in trends]
        snapshots_res = supabase.table('trend_snapshots') \
            .select('trend_id, velocity_avg, captured_at') \
            .in_('trend_id', trend_ids) \
            .order('captured_at', desc=True) \
            .execute()
        
        # Group snapshots by trend_id
        snapshots_by_trend = {}
        for snap in snapshots_res.data or []:
            trend_id = snap['trend_id']
            if trend_id not in snapshots_by_trend:
                snapshots_by_trend[trend_id] = []
            snapshots_by_trend[trend_id].append(snap)
        
        # Calculate peaking score using real data only
        peaking_trends = []
        for trend in trends:
            snapshots = snapshots_by_trend.get(trend['id'], [])
            if calculate_realistic_peaking_score:
                peaking_score = calculate_realistic_peaking_score(trend, snapshots)
                if peaking_score >= 70:  # Peaking threshold
                    trend['peaking_score'] = peaking_score
                    peaking_trends.append(trend)
        
        # Sort by peaking score and return top N
        peaking_trends.sort(key=lambda x: x['peaking_score'], reverse=True)
        return peaking_trends[:limit]
    except Exception as e:
        logger.exception(f"Error getting peaking trends: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/trends/{trend_id}/timeline")
@limiter.limit("60/minute")
def get_trend_timeline(
    request: Request, 
    trend_id: int, 
    current_user: str = Depends(get_current_user),
    _plan_check: str = Depends(require_feature("advanced_analytics")),
    _usage_log: str = Depends(log_endpoint_usage("advanced_analytics"))
):
    """
    Get trend timeline proof using existing trend_snapshots data
    Returns velocity history, timestamps, and peak detection. Pro/Agency feature only.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    
    try:
        from datetime import timedelta
        
        # Get trend basic info
        trend_res = supabase.table('trends').select('*').eq('id', trend_id).single().execute()
        trend = trend_res.data
        
        if not trend:
            raise HTTPException(status_code=404, detail=f"Trend {trend_id} not found")
        
        # Get existing snapshots (this IS the proof trail)
        snapshots_res = supabase.table('trend_snapshots') \
            .select('*') \
            .eq('trend_id', trend_id) \
            .order('captured_at', desc=True) \
            .execute()
        
        snapshots = snapshots_res.data or []
        
        # Calculate velocity acceleration from snapshots
        velocity_data = []
        for i, snap in enumerate(snapshots):
            velocity_data.append({
                'timestamp': snap['captured_at'],
                'velocity': snap['velocity_avg'],
                'creator_count': snap['creator_count']
            })
        
        # Calculate acceleration (recent vs older)
        acceleration = 0
        if len(velocity_data) >= 2:
            recent_avg = velocity_data[0]['velocity']
            older_avg = velocity_data[-1]['velocity']
            if older_avg > 0:
                acceleration = ((recent_avg - older_avg) / older_avg) * 100
        
        # Calculate trend age dynamically (not from stale DB column)
        first_detected = trend.get('first_detected_at')
        if first_detected:
            if first_detected.endswith('Z'):
                first_detected = first_detected[:-1] + '+00:00'
            detected_dt = datetime.fromisoformat(first_detected)
            # Defensive timezone handling
            if detected_dt.tzinfo is None:
                detected_dt = detected_dt.replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - detected_dt).total_seconds() / 3600
        else:
            age_hours = trend.get('trend_age_hours', 0)  # Fallback to DB value
        
        return {
            'trend_id': trend_id,
            'first_detected_at': trend.get('first_detected_at'),
            'created_at': trend.get('created_at'),
            'peak_velocity': trend.get('peak_velocity'),
            'trend_age_hours': round(age_hours, 2),  # Dynamically computed
            'window_hours_remaining': trend.get('window_hours_remaining'),
            'velocity_history': velocity_data,
            'velocity_acceleration_pct': round(acceleration, 2),
            'snapshot_count': len(snapshots)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching trend timeline: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/trends/targeted")
def get_targeted_trends(authorization: Optional[str] = Header(None)):
    """Fetch all trends currently targeted by the authenticated user. Returns [] for guests."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    try:
        user_id = _resolve_user(authorization)
        if not user_id:
            return []  # Guests see an empty workspace — no error

        actions_res = supabase.table("trend_actions").select("trend_id").eq("user_id", user_id).eq("action_type", "target").execute()
        trend_ids = [a["trend_id"] for a in actions_res.data or []]
        if not trend_ids:
            return []

        trends_res = supabase.table("trends").select("*").in_("id", trend_ids).execute()
        return _normalize_trends(trends_res.data or [])
    except Exception as e:
        logger.error(f"Error fetching targeted trends: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/trends/{trend_id}")
@limiter.limit("60/minute")
def get_trend(request: Request, trend_id: int, current_user: str = Depends(get_current_user)):
    """Fetch single trend by ID."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    try:
        res = supabase.table("trends").select("*").eq("id", trend_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail=f"Trend {trend_id} not found")
        trend = res.data[0]
        trend["song"] = trend.get("audio_title")
        trend["artist"] = trend.get("audio_artist")
        return trend
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/trends/{trend_id}/audio-history")
@limiter.limit("300/minute")
def get_trend_audio_history(request: Request, trend_id: int, current_user: str = Depends(get_current_user)):
    """Fetch 72h historical snapshot points for sparkline growth charting."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    try:
        # Get trend representative audio_id
        q_tr = supabase.table("trends").select("audio_id").eq("id", trend_id)
        trend_res = execute_supabase_get(q_tr)
        if not trend_res.data or not trend_res.data[0].get("audio_id"):
            return []

        audio_id = trend_res.data[0]["audio_id"]
        # Fetch snapshots of the audio count from the last 72 hours
        from datetime import datetime, timedelta, timezone
        time_threshold = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()

        q_hist = supabase.table("reel_snapshots") \
            .select("snapshotted_at, audio_use_count") \
            .eq("audio_id", audio_id) \
            .gte("snapshotted_at", time_threshold) \
            .order("snapshotted_at", desc=False)
        history_res = execute_supabase_get(q_hist)

        return history_res.data or []
    except Exception as e:
        logger.exception(f"Error fetching audio history for trend {trend_id}: {e}")
        # Return empty array instead of 500 error to prevent UI breaking
        return []


@router.get("/api/trends/{trend_id}/reels")
@limiter.limit("60/minute")
def get_trend_reels(
    request: Request, 
    trend_id: int, 
    current_user: str = Depends(get_current_user),
    _plan_check: str = Depends(require_feature("unlimited_trends")),
    _usage_log: str = Depends(log_endpoint_usage("unlimited_trends"))
):
    """Fetch reels linked to a trend (by matching audio_title + audio_artist). Pro/Agency feature only."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    try:
        trend_res = supabase.table("trends") \
            .select("audio_title, audio_artist") \
            .eq("id", trend_id) \
            .execute()
        if not trend_res.data:
            raise HTTPException(status_code=404, detail=f"Trend {trend_id} not found")
        t = trend_res.data[0]
        title, artist = t.get("audio_title"), t.get("audio_artist")
        reels_res = supabase.table("reels") \
            .select("*") \
            .eq("audio_title", title) \
            .eq("audio_artist", artist) \
            .order("velocity_score", desc=True) \
            .limit(20) \
            .execute()
        return reels_res.data or []
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching similar trends for trend {trend_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/trends/{trend_id}/caption")
@limiter.limit("20/minute")
def get_trend_caption(request: Request, trend_id: int, current_user: str = Depends(get_current_user)):
    """
    Returns AI-generated caption kit for a trend.
    Includes: 3 caption variants, 15 hashtags, audio cue, posting strategy.
    Results are cached in trend_captions table.
    """
    if not CaptionEngine:
        raise HTTPException(status_code=503, detail="Caption generation service unavailable")
    try:
        engine = CaptionEngine()
        caption_kit = engine.get_caption_kit(trend_id)
        return caption_kit
    except ValueError as ve:
        logger.warning(f"Validation error in caption generation for trend {trend_id}: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception(f"Error generating caption for trend {trend_id}: {e}")
        raise HTTPException(status_code=500, detail="Caption generation failed")


@router.get("/api/algorithm/analyze")
@limiter.limit("30/minute")
def analyze_content_for_virality(
    request: Request,
    views: int = 0,
    likes: int = 0,
    comments: int = 0,
    shares: int = 0,
    saves: int = 0,
    duration: int = 0,
    niche: str = "general",
    uses_trending_audio: bool = False,
    current_user: str = Depends(get_current_user),
    _plan_check: str = Depends(require_feature("algorithm_insights")),
    _usage_log: str = Depends(log_endpoint_usage("algorithm_insights"))
):
    """
    Analyze content metrics and provide Instagram algorithm insights for virality optimization.
    Returns overall virality score, factor analysis, and actionable recommendations.
    """
    if not InstagramAlgorithmInsights:
        raise HTTPException(status_code=500, detail="Instagram Algorithm Insights module not configured.")
    
    try:
        insights = InstagramAlgorithmInsights()
        
        content_data = {
            'views': views,
            'likes': likes,
            'comments': comments,
            'shares': shares,
            'saves': saves,
            'duration': duration,
            'niche': niche,
            'uses_trending_audio': uses_trending_audio
        }
        
        analysis = insights.analyze_content_for_virality(content_data)
        
        return {
            'virality_score': analysis['overall_virality_score'],
            'viral_potential': analysis['viral_potential'],
            'factor_scores': analysis['factor_scores'],
            'engagement_metrics': analysis['engagement_metrics'],
            'recommendations': [
                {
                    'category': rec.category,
                    'priority': rec.priority,
                    'title': rec.title,
                    'description': rec.description,
                    'expected_impact': rec.expected_impact,
                    'difficulty': rec.implementation_difficulty
                }
                for rec in analysis['recommendations']
            ],
            'algorithm_explanation': analysis['algorithm_explanation']
        }
    except Exception as e:
        logger.exception(f"Error in algorithm analysis: {e}")
        raise HTTPException(status_code=500, detail="Algorithm analysis failed")


@router.get("/api/algorithm/posting-times")
@limiter.limit("60/minute")
def get_optimal_posting_times(
    request: Request,
    niche: str = "general",
    target_audience: str = "india",
    current_user: str = Depends(get_current_user),
    _plan_check: str = Depends(require_feature("algorithm_insights")),
    _usage_log: str = Depends(log_endpoint_usage("algorithm_insights"))
):
    """Get optimal posting times based on niche and target audience."""
    if not InstagramAlgorithmInsights:
        raise HTTPException(status_code=500, detail="Instagram Algorithm Insights module not configured.")
    
    try:
        insights = InstagramAlgorithmInsights()
        times = insights.get_optimal_posting_times(niche, target_audience)
        return {'niche': niche, 'target_audience': target_audience, 'optimal_times': times}
    except Exception as e:
        logger.exception(f"Error getting posting times: {e}")
        raise HTTPException(status_code=500, detail="Failed to get posting times")


@router.get("/api/algorithm/hashtag-strategy")
@limiter.limit("60/minute")
def get_hashtag_strategy(
    request: Request,
    niche: str = "general",
    content_type: str = "reel",
    current_user: str = Depends(get_current_user),
    _plan_check: str = Depends(require_feature("algorithm_insights")),
    _usage_log: str = Depends(log_endpoint_usage("algorithm_insights"))
):
    """Get hashtag strategy recommendations based on niche and content type."""
    if not InstagramAlgorithmInsights:
        raise HTTPException(status_code=500, detail="Instagram Algorithm Insights module not configured.")
    
    try:
        insights = InstagramAlgorithmInsights()
        strategy = insights.get_hashtag_strategy(niche, content_type)
        return {'niche': niche, 'content_type': content_type, 'hashtag_strategy': strategy}
    except Exception as e:
        logger.exception(f"Error getting hashtag strategy: {e}")
        raise HTTPException(status_code=500, detail="Failed to get hashtag strategy")
        kit = engine.get_caption_kit(trend_id)
        return kit
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Caption generation failed for trend {trend_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/trends/{trend_id}/similar")
@limiter.limit("60/minute")
def get_similar_trends(
    request: Request, 
    trend_id: int, 
    current_user: str = Depends(get_current_user),
    _plan_check: str = Depends(require_feature("unlimited_trends")),
    _usage_log: str = Depends(log_endpoint_usage("unlimited_trends"))
):
    """Returns past trends with the same content_type and language (peaked or expired, showing history). Pro/Agency feature only."""
    try:
        trend_res = supabase.table("trends") \
            .select("content_type, language") \
            .eq("id", trend_id) \
            .execute()
        if not trend_res.data:
            raise HTTPException(status_code=404, detail=f"Trend {trend_id} not found")
        t = trend_res.data[0]
        content_type = t.get("content_type")
        language = t.get("language")
        q = supabase.table("trends").select("*").eq("is_seed_data", False).neq("id", trend_id)
        if content_type:
            q = q.eq("content_type", content_type)
        if language:
            q = q.eq("language", language)
        q = q.order("velocity_avg", desc=True).limit(5)
        res = q.execute()
        similar = res.data or []
        for s in similar:
            s["song"] = s.get("audio_title")
            s["artist"] = s.get("audio_artist")
        return similar
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error computing trend decision for trend {trend_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/trends/{trend_id}/decision")
@limiter.limit("60/minute")
def get_trend_decision(
    request: Request, 
    trend_id: int, 
    creator_niche: Optional[str] = None, 
    creator_language: Optional[str] = None, 
    current_user: str = Depends(get_current_user),
    _plan_check: str = Depends(require_feature("unlimited_trends")),
    _usage_log: str = Depends(log_endpoint_usage("unlimited_trends"))
):
    """
    Returns a simple creator decision layer for the trend:
    post it, trial it, or skip it. Pro/Agency feature only.
    """

    try:
        res = supabase.table("trends").select("*").eq("id", trend_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail=f"Trend {trend_id} not found")
        t = res.data[0]

        fit = float(t.get("creator_fit_score") or 0)
        hook = float(t.get("hook_retention_score") or 0)
        crowd = 1.0 - float(t.get("saturation_penalty") or 0)
        composite = float(t.get("composite_score") or 0)
        confidence = float(t.get("confidence") or 0)

        score = (fit * 0.35) + (hook * 0.25) + (crowd * 0.2) + (min(1.0, confidence) * 0.2)
        if creator_niche and creator_niche.lower() in (t.get("content_type") or "").lower():
            score += 0.05
        if creator_language and creator_language.lower() == (t.get("language") or "").lower():
            score += 0.05

        if score >= 0.72 and composite >= 3.0:
            decision = "post"
        elif score >= 0.55:
            decision = "trial"
        else:
            decision = "skip"

        test_hook = t.get("text_overlay_template") or f"POV: you just found {t.get('audio_title')}"
        public_hook = f"Would you use this sound for {t.get('content_type') or 'your niche'}?"

        rationale = (
            f"Fit {int(fit * 100)}%, hook {int(hook * 100)}%, crowd {int(crowd * 100)}%, "
            f"confidence {int(confidence * 100)}%."
        )

        return {
            "decision": decision,
            "score": round(score, 3),
            "rationale": rationale,
            "test_hook": test_hook,
            "public_hook": public_hook,
            "trend": {
                "creator_fit_score": fit,
                "hook_retention_score": hook,
                "saturation_penalty": float(t.get("saturation_penalty") or 0),
                "composite_score": composite,
                "confidence": confidence,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting trend decision: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/api/trends/{trend_id}/memory")
@limiter.limit("30/minute")
def save_trend_memory(request: Request, trend_id: int, req: MemoryRequest, current_user_email: str = Depends(require_auth)):
    try:
        memory = {
            "user_email": current_user_email,
            "trend_id": trend_id,
            "format_name": req.format_name,
            "hook_variant": req.hook_variant,
            "planned_mode": req.planned_mode,
            "outcome_score": req.outcome_score,
            "notes": req.notes,
        }
        supabase.table("creator_trend_memory").insert(memory).execute()
        return {"success": True}
    except Exception as e:
        logger.error(f"Error saving trend memory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/api/trends/{trend_id}/target")
@limiter.limit("30/minute")
def toggle_trend_target(request: Request, trend_id: int, req: TargetRequest, authorization: Optional[str] = Header(None)):
    """Add or remove a trend from the user's targeted list, updating saturation."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    try:
        user_id = _resolve_user(authorization)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required to target trends")

        if req.action == "target":
            supabase.table("trend_actions").upsert({
                "user_id": user_id,
                "trend_id": trend_id,
                "action_type": "target"
            }, on_conflict="user_id,trend_id,action_type").execute()
            count_res = supabase.table("trend_actions").select("id", count="exact").eq("trend_id", trend_id).eq("action_type", "target").execute()
            sat_count = count_res.count or 0
            supabase.table("trends").update({"saturation_count": sat_count}).eq("id", trend_id).execute()
            return {"success": True, "action": "target", "saturation_count": sat_count}

        elif req.action == "untarget":
            supabase.table("trend_actions").delete().eq("user_id", user_id).eq("trend_id", trend_id).eq("action_type", "target").execute()
            count_res = supabase.table("trend_actions").select("id", count="exact").eq("trend_id", trend_id).eq("action_type", "target").execute()
            sat_count = count_res.count or 0
            supabase.table("trends").update({"saturation_count": sat_count}).eq("id", trend_id).execute()
            return {"success": True, "action": "untarget", "saturation_count": sat_count}
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling target: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/hashtags/velocity")
@limiter.limit("30/minute")
def get_hashtag_velocity(
    request: Request,
    hours_window: int = 24,
    current_user: str = Depends(get_current_user)
):
    """Get hashtag velocity data for trending hashtags."""
    if not HashtagVelocityTracker:
        raise HTTPException(status_code=500, detail="Hashtag velocity tracker not configured.")
    
    try:
        tracker = HashtagVelocityTracker()
        velocities = tracker.track_hashtag_velocity(hours_window=hours_window)
        
        return {
            'hashtag_velocities': [
                {
                    'hashtag': hv.hashtag,
                    'current_count': hv.current_count,
                    'previous_count': hv.previous_count,
                    'velocity_score': hv.velocity_score,
                    'trend_direction': hv.trend_direction,
                    'acceleration': hv.acceleration,
                    'usage_frequency': hv.usage_frequency,
                    'niche_relevance': hv.niche_relevance,
                    'estimated_total_creators': hv.estimated_total_creators,
                    'peak_24h_usage': hv.peak_24h_usage,
                    'discovered_at': hv.discovered_at.isoformat()
                }
                for hv in velocities
            ],
            'total_hashtags': len(velocities),
            'hours_window': hours_window
        }
    except Exception as e:
        logger.exception(f"Error getting hashtag velocity: {e}")
        raise HTTPException(status_code=500, detail="Failed to get hashtag velocity")


@router.get("/api/hashtags/trending")
@limiter.limit("30/minute")
def get_trending_hashtags(
    request: Request,
    hours_window: int = 24,
    min_velocity: float = 20.0,
    current_user: str = Depends(get_current_user)
):
    """Get trending hashtags with detailed trend analysis."""
    if not HashtagVelocityTracker:
        raise HTTPException(status_code=500, detail="Hashtag velocity tracker not configured.")
    
    try:
        tracker = HashtagVelocityTracker()
        trends = tracker.get_trending_hashtags(hours_window=hours_window, min_velocity=min_velocity)
        
        return {
            'trending_hashtags': [
                {
                    'hashtag': trend.hashtag,
                    'velocity_score': trend.velocity_score,
                    'trend_direction': trend.trend_direction,
                    'related_hashtags': trend.related_hashtags,
                    'content_themes': trend.content_themes,
                    'target_audiences': trend.target_audiences,
                    'optimal_content_types': trend.optimal_content_types,
                    'estimated_lifespan_hours': trend.estimated_lifespan,
                    'competition_level': trend.competition_level,
                    'platform_performance': trend.platform_performance
                }
                for trend in trends
            ],
            'total_trending': len(trends),
            'query_params': {'hours_window': hours_window, 'min_velocity': min_velocity}
        }
    except Exception as e:
        logger.exception(f"Error getting trending hashtags: {e}")
        raise HTTPException(status_code=500, detail="Failed to get trending hashtags")


@router.get("/api/trends/niche/{niche_name}")
@limiter.limit("60/minute")
def get_niche_trends(
    request: Request,
    niche_name: str,
    limit: int = 50,
    current_user: str = Depends(get_current_user)
):
    """
    Fetch trends combined from audio trends and content trends,
    filtered and sorted by relevance to a specific creator niche.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
        
    try:
        # Fetch audio trends (status emerging or rising)
        audio_res = supabase.table("trends") \
            .select("*") \
            .in_("status", ["emerging", "rising"]) \
            .eq("is_seed_data", False) \
            .order("velocity_avg", desc=True) \
            .limit(100) \
            .execute()
        audio_trends = audio_res.data or []
        
        # Fetch content trends (status emerging or rising)
        content_res = supabase.table("content_trends") \
            .select("*") \
            .in_("status", ["emerging", "rising"]) \
            .order("velocity_avg", desc=True) \
            .limit(50) \
            .execute()
        content_trends = content_res.data or []
        
        # Combine
        combined_trends = audio_trends + content_trends
        
        # Filter and score
        enriched = niche_relevance_engine.enrich_trends_with_niche_relevance(combined_trends, top_n_niches=3)
        niche_feed = niche_relevance_engine.filter_trends_for_niche(enriched, niche_name, min_relevance=0.15)
        
        return niche_feed[:limit]
        
    except Exception as e:
        logger.exception(f"Error fetching niche trends: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/trends/watchlist")
def get_watchlist(limit: int = 30):
    """
    Order 65 Part 7.1: Active watchlist songs ordered by score desc.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        res = supabase.table("watchlist") \
            .select("song_key, audio_id, score, status, first_reels, first_creators, reasons, flagged_at, run_id") \
            .in_("status", ["active", "watching"]) \
            .order("score", desc=True) \
            .limit(limit) \
            .execute()
        return res.data or []
    except Exception as e:
        logger.exception(f"Error fetching watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/trends/proof")
def get_proof_log(limit: int = 50):
    """
    Order 65 Part 7.1: Proof log entries where run_id is not null.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        res = supabase.table("proof_log") \
            .select("id, audio_id, flagged_at, reasons, snapshot, run_id") \
            .not_.is_("run_id", "null") \
            .order("flagged_at", desc=True) \
            .limit(limit) \
            .execute()
        return res.data or []
    except Exception as e:
        logger.exception(f"Error fetching proof_log: {e}")
        raise HTTPException(status_code=500, detail=str(e))

