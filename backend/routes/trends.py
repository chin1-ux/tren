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

@router.get("/api/trends")
@router.get("/api/trends/rising")
@limiter.limit("60/minute")
def get_trends(
    request: Request,
    language: Optional[str] = None,
    sort: Optional[str] = "velocity",
    niche: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """
    Fetch RISING trends from Supabase.
    Optional filters: ?language=hi&sort=velocity|time_left|newest&niche=fitness
    """
    lang_key = language or "all"
    niche_key = niche or "all"
    user_email = current_user if current_user else "guest"
    cache_key = f"trends:{lang_key}:{sort}:{niche_key}:{user_email}"
    
    # Try fetching from Redis cache first
    if standard_queue and standard_queue.connection:
        try:
            cached_data = standard_queue.connection.get(cache_key)
            if cached_data:
                logger.info(f"Serving trends from cache for key: {cache_key}")
                headers = {"Cache-Control": "public, max-age=300"}
                return JSONResponse(content=json.loads(cached_data), headers=headers)
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
                user_data = get_cached_user_profile(current_user)
                if user_data:
                    user_plan = user_data.get("plan") or "free"
                    
                # Query user_preferences DB for personalized feed
                prefs_res = supabase.table("user_preferences").select("niches, languages, regions, state").eq("email", current_user).execute()
                if prefs_res.data:
                    prefs = prefs_res.data[0]
                    # Convert list to string for current logic or use first element
                    if prefs.get("niches") and len(prefs["niches"]) > 0:
                        user_niche = prefs["niches"][0] # Focus on primary niche for sort
                    if prefs.get("languages") and len(prefs["languages"]) > 0:
                        user_lang = prefs["languages"][0]
            except Exception as e:
                logger.warning(f"Error querying user profile/preferences for personalization: {e}")

        # Get delay hours from module-level cached tiers
        delay_hours = get_cached_tier_delay(user_plan)

        q = supabase.table("trends").select("*").eq("status", "rising").eq("is_voiceover", False).eq("is_seed_data", False).in_("llm_classification_status", ["completed", "not_needed", "skipped_local_fallback"]).gt("window_hours_remaining", 0)

        # 7-day retention gate for Rising tab (prevents ancient trends from clogging feed)
        rising_cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        q = q.or_(
            f"first_detected_at.gte.{rising_cutoff},"
            f"and(first_detected_at.is.null,created_at.gte.{rising_cutoff})"
        )

        if language and language != "all":
            q = q.eq("language", language)

        if niche and niche != "all":
            q = q.or_(f"niche_tag.eq.{niche},semantic_niches.cs.{{{niche}}}")

        # Server-side gating data delay filter
        # CRITICAL: first_detected_at may be NULL for older trends (scraper didn't always write it).
        # NULL <= timestamp is FALSE in Postgres, so a pure lte() filter would return 0 rows for free
        # users when the column is unset. Use created_at as a fallback: if first_detected_at IS NULL,
        # gate on created_at instead so free users always see something.
        if delay_hours > 0:
            time_cutoff = (datetime.now(timezone.utc) - timedelta(hours=delay_hours)).isoformat()
            q = q.or_(
                f"first_detected_at.lte.{time_cutoff},"
                f"and(first_detected_at.is.null,created_at.lte.{time_cutoff})"
            )

        if sort == "time_left":
            q = q.order("window_hours_remaining", desc=False)
        elif sort == "newest":
            q = q.order("first_detected_at", desc=True)
        else:
            q = q.order("velocity_avg", desc=True)

        q = q.limit(100)
        res = q.execute()
        trends = _normalize_trends(res.data or [])
        
        # Wire C5: Inject niche adaptations using the engine for personalized feed
        for t in trends:
            if user_niche and user_niche not in ["all", "general"]:
                if not t.get("niche_relevance"):
                    t["niche_relevance"] = niche_relevance_engine.score_signal(t)
                
                score = t["niche_relevance"].get(user_niche, 0.0)
                brief = niche_relevance_engine.generate_adaptation_brief(t, user_niche, score)
                
                if brief:
                    if not t.get("adaptation_briefs"):
                        t["adaptation_briefs"] = {}
                    t["adaptation_briefs"][user_niche] = brief

        trends.sort(key=lambda t: _trend_priority_key(t, user_niche, user_lang), reverse=True)

        # Cache the result in Redis for 5 minutes
        if standard_queue and standard_queue.connection:
            try:
                standard_queue.connection.setex(cache_key, 300, json.dumps(trends))
            except Exception as e:
                logger.error(f"Redis cache write error: {e}")
                
        headers = {"Cache-Control": "public, max-age=300"}
        return JSONResponse(content=trends, headers=headers)
    except Exception as e:
        logger.error(f"Error fetching trends: {e}", exc_info=True)

        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/trends/emerging")
@limiter.limit("60/minute")
def get_emerging_trends(
    request: Request, 
    language: Optional[str] = None, 
    current_user: str = Depends(get_current_user),
    _plan_check: str = Depends(require_feature("early_detection"))
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

        q = supabase.table("trends").select("*").eq("status", "emerging").eq("is_voiceover", False).eq("is_seed_data", False).in_("llm_classification_status", ["completed", "not_needed", "skipped_local_fallback"])
        
        # 48-hour retention gate for Emerging tab (only fresh pre-viral trends)
        emerging_cutoff = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        q = q.or_(
            f"first_detected_at.gte.{emerging_cutoff},"
            f"and(first_detected_at.is.null,created_at.gte.{emerging_cutoff})"
        )

        if language and language != "all":
            q = q.eq("language", language)
        q = q.order("velocity_avg", desc=True)
        q = q.limit(100)
        res = q.execute()
        trends = _normalize_trends(res.data or [])
        trends.sort(key=lambda t: _trend_priority_key(t, user_niche, user_lang), reverse=True)
        
        # Add user watermark ID to each trend for leak tracing
        if user_id:
            for trend in trends:
                trend["user_watermark_id"] = user_id
        
        return trends
    except Exception as e:
        logger.error(f"Error fetching emerging trends: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


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
        res = supabase.table("trends").select("*").in_("status", ["emerging", "rising"]).eq("is_seed_data", False).in_("llm_classification_status", ["completed", "not_needed"]).order("velocity_avg", desc=True).limit(100).execute()
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
    limit: int = 100,
    current_user: str = Depends(get_current_user)
):
    """
    Fetch PEAKED trends — trends that have peaked but still have value.
    These are trends that dropped below 60% of their peak velocity.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
        
    lang_key = language or "all"
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
        q = supabase.table("trends").select("*").eq("status", "peaked").eq("is_seed_data", False).in_("llm_classification_status", ["completed", "not_needed", "skipped_local_fallback"])
        
        # 14-day retention gate for Peaked tab (max 14 days post-peak)
        peaked_cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        q = q.or_(
            f"first_detected_at.gte.{peaked_cutoff},"
            f"and(first_detected_at.is.null,created_at.gte.{peaked_cutoff})"
        )

        if language and language != "all":
            q = q.eq("language", language)
        q = q.order("first_detected_at", desc=True)
        q = q.limit(min(limit, 50))
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


@router.get("/api/trends/expired")
@limiter.limit("60/minute")
def get_expired_trends(
    request: Request, 
    language: Optional[str] = None, 
    limit: int = 50,
    current_user: str = Depends(get_current_user),
):
    """
    Fetch EXPIRED trends — trends that have passed their window or aged out.
    These are trends that are no longer active but may still have historical value.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    try:
        q = supabase.table("trends").select("*").eq("status", "expired").eq("is_seed_data", False).in_("llm_classification_status", ["completed", "not_needed", "skipped_local_fallback"])
        
        # 30-day retention gate for Expired tab (max 30 days historical archive)
        expired_cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        q = q.or_(
            f"first_detected_at.gte.{expired_cutoff},"
            f"and(first_detected_at.is.null,created_at.gte.{expired_cutoff})"
        )

        if language and language != "all":
            q = q.eq("language", language)
        q = q.order("first_detected_at", desc=True)
        q = q.limit(min(limit, 50))
        res = q.execute()
        trends = _normalize_trends(res.data or [])
        trends.sort(key=_trend_priority_key, reverse=True)
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
        res = supabase.table("trends") \
            .select("*") \
            .in_("status", ["emerging", "rising"]) \
            .eq("is_seed_data", False) \
            .in_("llm_classification_status", ["completed", "not_needed"]) \
            .eq("language", lang) \
            .order("velocity_avg", desc=True) \
            .limit(100) \
            .execute()
        trends = _normalize_trends(res.data or [])
        trends.sort(key=_trend_priority_key, reverse=True)
        return trends
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
        trend_res = supabase.table("trends").select("audio_id").eq("id", trend_id).execute()
        if not trend_res.data or not trend_res.data[0].get("audio_id"):
            return []

        audio_id = trend_res.data[0]["audio_id"]
        # Fetch snapshots of the audio count from the last 72 hours
        from datetime import datetime, timedelta, timezone
        time_threshold = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()

        history_res = supabase.table("reel_snapshots") \
            .select("snapshotted_at, audio_use_count") \
            .eq("audio_id", audio_id) \
            .gte("snapshotted_at", time_threshold) \
            .order("snapshotted_at", desc=False) \
            .execute()

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
