from fastapi import APIRouter, HTTPException, Depends, Request, Header, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import os, json, time, logging, traceback
from datetime import datetime, timezone, timedelta
from api_globals import *
from api_globals import _PEAKED_TRENDS_CACHE, standard_queue, _normalize_trends, _trend_priority_key, _resolve_user
from schemas import *
import niche_relevance_engine
router = APIRouter()

_TRENDS_FEED_CACHE: dict = {}
_EMERGING_TRENDS_CACHE: dict = {}
_RESURGING_TRENDS_CACHE: dict = {}
_EXPIRED_TRENDS_CACHE: dict = {}
_DATA_FRESHNESS_CACHE: dict = {"time": 0, "data": None}

def _get_data_freshness() -> dict:
    """
    Computes per-source last_success_at (instagram, spotify) derived from cron_runs/reels.
    Returns overall last_updated, is_stale (>12h), and breakdown by source.
    Cached for 60s to avoid unnecessary DB load.
    """
    now_ts = time.time()
    if _DATA_FRESHNESS_CACHE.get("data") and (now_ts - _DATA_FRESHNESS_CACHE.get("time", 0) < 60):
        return _DATA_FRESHNESS_CACHE["data"]

    now_dt = datetime.now(timezone.utc)
    res_data = {
        "last_updated": None,
        "is_stale": False,
        "staleness_threshold_hours": 12.0,
        "sources": {
            "instagram": {"last_success_at": None, "age_hours": None, "is_stale": False},
            "spotify": {"last_success_at": None, "age_hours": None, "is_stale": False},
        }
    }

    if not supabase:
        return res_data

    try:
        # 1. Instagram: Check latest reels scraped_at, or latest cron_runs with reels_scraped > 0
        ig_dt = None
        try:
            r_reels = supabase.table("reels").select("scraped_at").order("scraped_at", desc=True).limit(1).execute()
            if r_reels.data and r_reels.data[0].get("scraped_at"):
                val = r_reels.data[0]["scraped_at"].replace("Z", "+00:00")
                ig_dt = datetime.fromisoformat(val)
                if ig_dt.tzinfo is None:
                    ig_dt = ig_dt.replace(tzinfo=timezone.utc)
        except Exception as e_ig1:
            logger.warning(f"Error querying reels for IG freshness: {e_ig1}")

        try:
            r_cron = supabase.table("cron_runs") \
                .select("completed_at, run_at, created_at, reels_scraped, new_reels_count") \
                .or_("reels_scraped.gt.0,new_reels_count.gt.0") \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()
            if r_cron.data and r_cron.data[0]:
                c_item = r_cron.data[0]
                c_val = c_item.get("completed_at") or c_item.get("run_at") or c_item.get("created_at")
                if c_val:
                    c_dt = datetime.fromisoformat(c_val.replace("Z", "+00:00"))
                    if c_dt.tzinfo is None:
                        c_dt = c_dt.replace(tzinfo=timezone.utc)
                    if ig_dt is None or c_dt > ig_dt:
                        ig_dt = c_dt
        except Exception as e_ig2:
            logger.warning(f"Error querying cron_runs for IG freshness: {e_ig2}")

        if ig_dt:
            ig_age = max(0.0, (now_dt - ig_dt).total_seconds() / 3600.0)
            res_data["sources"]["instagram"]["last_success_at"] = ig_dt.isoformat()
            res_data["sources"]["instagram"]["age_hours"] = round(ig_age, 2)
            res_data["sources"]["instagram"]["is_stale"] = (ig_age > 12.0)

        # 2. Spotify: Check spotify_feed_cache or content_trends
        sp_dt = None
        try:
            r_sp = supabase.table("spotify_feed_cache").select("created_at, trend_created_at").order("created_at", desc=True).limit(1).execute()
            if r_sp.data and r_sp.data[0]:
                sp_val = r_sp.data[0].get("created_at") or r_sp.data[0].get("trend_created_at")
                if sp_val:
                    sp_dt = datetime.fromisoformat(sp_val.replace("Z", "+00:00"))
                    if sp_dt.tzinfo is None:
                        sp_dt = sp_dt.replace(tzinfo=timezone.utc)
        except Exception as e_sp:
            logger.warning(f"Error querying spotify_feed_cache for Spotify freshness: {e_sp}")

        if not sp_dt:
            try:
                r_ct = supabase.table("content_trends").select("created_at").eq("trend_type", "audio").order("created_at", desc=True).limit(1).execute()
                if r_ct.data and r_ct.data[0].get("created_at"):
                    sp_dt = datetime.fromisoformat(r_ct.data[0]["created_at"].replace("Z", "+00:00"))
                    if sp_dt.tzinfo is None:
                        sp_dt = sp_dt.replace(tzinfo=timezone.utc)
            except Exception as e_ct:
                logger.warning(f"Error querying content_trends for Spotify freshness: {e_ct}")

        if sp_dt:
            sp_age = max(0.0, (now_dt - sp_dt).total_seconds() / 3600.0)
            res_data["sources"]["spotify"]["last_success_at"] = sp_dt.isoformat()
            res_data["sources"]["spotify"]["age_hours"] = round(sp_age, 2)
            res_data["sources"]["spotify"]["is_stale"] = (sp_age > 12.0)

        # Overall freshness: derived from newest successful ingest timestamp
        newest_dt = max([d for d in (ig_dt, sp_dt) if d is not None], default=None)
        if newest_dt:
            overall_age = max(0.0, (now_dt - newest_dt).total_seconds() / 3600.0)
            res_data["last_updated"] = newest_dt.isoformat()
            res_data["age_hours"] = round(overall_age, 2)
            res_data["is_stale"] = (overall_age > 12.0)
            # If IG specifically is older than 12h, mark as stale
            if ig_dt and ((now_dt - ig_dt).total_seconds() / 3600.0 > 12.0):
                res_data["is_stale"] = True
        else:
            res_data["is_stale"] = True

        _DATA_FRESHNESS_CACHE["time"] = now_ts
        _DATA_FRESHNESS_CACHE["data"] = res_data
    except Exception as e:
        logger.error(f"Error computing data freshness: {e}", exc_info=True)

    return res_data

def _apply_languages_filter(q, language: Optional[str] = None, languages: Optional[str] = None):
    lang_list = []
    if languages and languages.strip():
        lang_list = [l.strip().lower() for l in languages.split(",") if l.strip() and l.strip().lower() != "all"]
    elif language and language.strip() and language.lower() != "all":
        lang_list = [language.strip().lower()]

    if not lang_list:
        return q

    # 'global' = strictly verified foreign languages (en, es, pt, ko, ja, ru, fr, de, it) or global discovery source
    # Indian regional languages and instrumental unclassified rows are strictly excluded
    if "global" in lang_list:
        global_codes = "en,es,pt,ko,ja,ru,fr,de,it"
        indian_codes = "hi,pa,ta,te,ml,kn,bn,mr,gu,ne,bho,hne,or,instrumental"
        return q.or_(
            f"language_final.in.({global_codes}),"
            f"discovery_source.eq.global,"
            f"and(language_final.is.null,language.in.({global_codes}))"
        ).or_("trend_origin.neq.IN,trend_origin.is.null").or_(f"language.not.in.({indian_codes}),language.is.null")

    filter_or = f"language_final.in.({','.join(lang_list)}),and(language_final.is.null,language.in.({','.join(lang_list)}))"
    return q.or_(filter_or)


_USER_PREFS_CACHE: dict[str, tuple[dict, float]] = {}

FEED_CARD_COLUMNS = (
    "id,audio_title,audio_artist,audio_id,audio_use_count,content_type,window_hours_remaining,velocity_avg,"
    "language,language_final,status,stage,stage_computed_at,saturation_score,creator_fit_score,hook_retention_score,created_at,"
    "first_detected_at,niche_tag,semantic_niches,discovery_source,is_regional_crossover,crossover_from_language,"
    "crossover_message,used_for,used_for_note,trend_classification,velocity_pattern,optimal_post_hour_ist,"
    "why_this_works,vibe_tag,platform,is_dance,is_voiceover,is_seed_data,is_evergreen,trend_age_hours,"
    "template_link,saturation_count,hook_brief,status_changed_at,adaptation_briefs,niche_relevance,reel_count,"
    "audio_cue_second,best_platform_first,trend_origin,virality_type,content_tone,display_title,commercial_song_alias,"
    "has_creator_outlier,global_saturation_pct,india_saturation_pct,ideal_content_description,opportunity_score,"
    "peaking_score,saturation_penalty,llm_classification_status,composite_score"
)

SLIM_FEED_COLUMNS = (
    "id,audio_title,audio_artist,audio_id,audio_use_count,status,stage,stage_computed_at,velocity_avg,"
    "opportunity_score,saturation_score,india_saturation_pct,global_saturation_pct,"
    "saturation_penalty,creator_fit_score,hook_retention_score,window_hours_remaining,"
    "first_detected_at,created_at,status_changed_at,last_seen_at,why_this_works,used_for_note,"
    "niche_tag,semantic_niches,language,language_final,trend_classification,velocity_pattern,"
    "optimal_post_hour_ist,is_dance,is_voiceover,is_seed_data,is_regional_crossover,"
    "crossover_from_language,crossover_message,hook_brief,adaptation_briefs,display_title,"
    "commercial_song_alias,has_creator_outlier,reel_count"
)

_FEED_UNIFIED_CACHE: dict = {}
_ASK_SEARCH_CACHE: dict = {}

def _normalize_trends_slim(trends: list) -> list:
    """Fast slim normalization: sanitizes title, artist, language, niches without DB reel fetches."""
    if not trends:
        return trends
    try:
        from audio_title_normalize import normalize_audio_title
        clean_trends = []
        for t in trends:
            st = (t.get("status") or "").lower()
            title = (t.get("audio_title") or "").lower()
            if st in ("unqualified", "disqualified") or "speech plan" in title or "speechplan" in title:
                continue

            raw_title = t.get("audio_title") or t.get("song") or ""
            raw_artist = t.get("audio_artist") or t.get("artist") or ""
            norm_title, norm_artist = normalize_audio_title(raw_title, raw_artist)
            t["audio_title"] = norm_title
            t["audio_artist"] = norm_artist
            t["song"] = norm_title
            t["artist"] = norm_artist
            if not t.get("content_type"):
                t["content_type"] = "viral"

            lang_final = (t.get("language_final") or "").strip().lower()
            if lang_final and lang_final not in ("unknown", "other", ""):
                t["language"] = lang_final
                t["detected_language"] = lang_final

            clean_trends.append(t)

        freshness = _get_data_freshness()
        for t in clean_trends:
            t["last_updated"] = freshness.get("last_updated")
            t["is_stale"] = freshness.get("is_stale", False)

        return clean_trends
    except Exception as e:
        logger.warning(f"Error in slim normalization: {e}")
        return trends

@router.get("/api/feed")
@limiter.limit("60/minute")
def get_unified_feed(
    request: Request,
    page: int = 1,
    limit: int = 20,
    language: Optional[str] = None,
    languages: Optional[str] = None,
    niche: Optional[str] = None,
    status: Optional[str] = None,
    stage: Optional[str] = None,
    mode: Optional[str] = None,
    sort: Optional[str] = "priority",
    current_user: str = Depends(get_current_user)
):
    """
    Order 77 Item 5 & Order 79: Unified, fast, cached feed endpoint.
    Supports stage filters (Just starting, Blowing up, Still going, Comeback, Fading, Expired)
    and modes (today vs explore).
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    try:
        now_ts = time.time()
        page = max(1, page)
        limit = min(50, max(1, limit))
        
        lang_key = languages or language or "all"
        niche_key = niche or "all"
        status_key = status or "all"
        stage_key = stage or "all"
        mode_key = mode or "all"
        cache_key = f"feed:{lang_key}:{niche_key}:{status_key}:{stage_key}:{mode_key}:{sort}:p{page}:l{limit}"
        
        if cache_key in _FEED_UNIFIED_CACHE:
            entry = _FEED_UNIFIED_CACHE[cache_key]
            if now_ts - entry.get("time", 0) < 60:
                headers = {
                    "Cache-Control": "public, max-age=60, s-maxage=300, stale-while-revalidate=600",
                    "X-Cache": "HIT-MEM",
                }
                return JSONResponse(content=entry["data"], headers=headers)
                
        q = supabase.table("trends").select(SLIM_FEED_COLUMNS, count="exact").eq("is_voiceover", False).eq("is_seed_data", False)
        
        if mode == "today":
            # Today: stage in (Just starting, Blowing up), newest real observation <=3 days, >=2 distinct creators
            q = q.in_("stage", ["Just starting", "Blowing up"]).gt("window_hours_remaining", 0)
        elif stage and stage != "all":
            q = q.eq("stage", stage)
        elif status and status != "all":
            q = q.eq("status", status)
        else:
            # Default active Explore rail (excluding expired unless requested)
            q = q.neq("status", "expired").gt("window_hours_remaining", 0)
            
        q = _apply_languages_filter(q, language, languages)
        
        if niche and niche != "all":
            q = q.or_(f"niche_tag.eq.{niche},semantic_niches.cs.{{{niche}}}")
            
        if sort == "velocity":
            q = q.order("velocity_avg", desc=True).order("id", desc=True)
        elif sort == "opportunity":
            q = q.order("opportunity_score", desc=True).order("id", desc=True)
        elif sort == "newest":
            q = q.order("first_detected_at", desc=True).order("id", desc=True)
        else:
            q = q.order("first_detected_at", desc=True).order("id", desc=True)
            
        offset = (page - 1) * limit
        q = q.range(offset, offset + limit - 1)
        
        res = execute_supabase_get(q)
        raw_trends = res.data or []
        total_count = res.count or len(raw_trends)
        
        trends = _normalize_trends_slim(raw_trends)
        
        payload = {
            "trends": trends,
            "total": total_count,
            "page": page,
            "limit": limit,
            "has_more": (offset + len(trends)) < total_count
        }
        
        _FEED_UNIFIED_CACHE[cache_key] = {"time": now_ts, "data": payload}
        if len(_FEED_UNIFIED_CACHE) > 200:
            oldest_k = min(_FEED_UNIFIED_CACHE.keys(), key=lambda k: _FEED_UNIFIED_CACHE[k]["time"])
            _FEED_UNIFIED_CACHE.pop(oldest_k, None)
            
        headers = {
            "Cache-Control": "public, max-age=60, s-maxage=300, stale-while-revalidate=600",
            "X-Cache": "MISS",
        }
        return JSONResponse(content=payload, headers=headers)
    except Exception as e:
        logger.error(f"Error fetching unified feed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/api/search/ask")
@limiter.limit("20/hour")
def search_ask(
    request: Request,
    q: str = "",
    current_user: str = Depends(get_current_user)
):
    """
    Order 77 Item 7: Natural language search that answers creator questions.
    Uses Groq/Gemini via call_llm with SQL fallback, 24h cache, 20/hr rate limit.
    """
    clean_q = (q or "").strip()
    if not clean_q:
        return JSONResponse({"direct_answer": "Please ask a question about what audio you want.", "results": []})
        
    try:
        from search_v2_engine import execute_search_v2
        
        # Check cache
        cache_key = clean_q.lower()
        now_ts = time.time()
        if cache_key in _ASK_SEARCH_CACHE:
            entry = _ASK_SEARCH_CACHE[cache_key]
            if now_ts - entry.get("time", 0) < 86400:
                return JSONResponse(
                    content=entry["data"],
                    headers={"Cache-Control": "public, max-age=3600, s-maxage=86400", "X-Cache": "HIT-MEM"}
                )

        # Fetch candidate active trends with slim columns
        query = supabase.table("trends").select(SLIM_FEED_COLUMNS).eq("is_seed_data", False).eq("is_voiceover", False).gt("window_hours_remaining", 0).order("first_detected_at", desc=True).limit(200)
        res = execute_supabase_get(query)
        raw_trends = res.data or []

        # Execute Search V2 deterministic pipeline
        search_res = execute_search_v2(clean_q, raw_trends, current_mode="india")
        
        # Normalize trends for UI output
        results_ui = _normalize_trends_slim(search_res["results"])
        
        result_payload = {
            "intent": search_res["count_line"],
            "direct_answer": search_res["count_line"],
            "count_line": search_res["count_line"],
            "parsed_filter": search_res["parsed_filter"],
            "chips": search_res["chips"],
            "results": results_ui
        }

        _ASK_SEARCH_CACHE[cache_key] = {"time": now_ts, "data": result_payload}
        if len(_ASK_SEARCH_CACHE) > 500:
            oldest_k = min(_ASK_SEARCH_CACHE.keys(), key=lambda k: _ASK_SEARCH_CACHE[k]["time"])
            _ASK_SEARCH_CACHE.pop(oldest_k, None)

        return JSONResponse(
            content=result_payload,
            headers={"Cache-Control": "public, max-age=3600, s-maxage=86400", "X-Cache": "MISS"}
        )
    except Exception as e:
        logger.error(f"Error in search_ask: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

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
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    try:
        now_ts = time.time()
        # Load user configuration for personalization
        user_niche = "all"
        user_lang = "all"
        user_plan = "free"
        
        # Airtight guest bypass guard: Must be valid email containing @ and not default guest
        if current_user and isinstance(current_user, str) and "@" in current_user and current_user != "guest@trendrop.app":
            try:
                user_plan = PlanEnforcement.get_user_plan(current_user)
                if current_user in _USER_PREFS_CACHE and (now_ts - _USER_PREFS_CACHE[current_user][1] < 300):
                    prefs = _USER_PREFS_CACHE[current_user][0]
                else:
                    if current_user.startswith("demo@") or current_user.endswith("@trendrop.app"):
                        prefs = {}
                    else:
                        prefs_res = supabase.table("user_preferences").select("niches, languages, preferred_languages, regions, state").eq("email", current_user).execute()
                        prefs = prefs_res.data[0] if prefs_res.data else {}
                    _USER_PREFS_CACHE[current_user] = (prefs, now_ts)

                if prefs.get("niches") and len(prefs["niches"]) > 0:
                    user_niche = prefs["niches"][0]
                pref_langs = prefs.get("preferred_languages") or prefs.get("languages")
                if not languages and not language and pref_langs and len(pref_langs) > 0:
                    languages = ",".join(pref_langs)
            except Exception as e:
                logger.warning(f"Error querying user profile/preferences for personalization: {e}")

        lang_key = languages or language or "all"
        niche_key = niche or "all"
        cache_key = f"trends:{lang_key}:{sort}:{niche_key}:{user_plan}"

        # Check in-memory feed cache (60s TTL)
        if cache_key in _TRENDS_FEED_CACHE:
            entry = _TRENDS_FEED_CACHE[cache_key]
            if now_ts - entry.get("time", 0) < 60:
                headers = {
                    "Cache-Control": "public, max-age=60, s-maxage=120, stale-while-revalidate=300",
                    "X-Cache": "HIT-MEM",
                    "X-Skipped-Local-Fallback": "true",
                }
                return JSONResponse(content=entry["data"], headers=headers)

        # Try fetching from Redis cache first
        if standard_queue and standard_queue.connection:
            try:
                cached_data = standard_queue.connection.get(cache_key)
                parsed_cache = json.loads(cached_data) if cached_data else None
                if parsed_cache and len(parsed_cache) > 0:
                    logger.info(f"Serving trends from cache for key: {cache_key}")
                    _TRENDS_FEED_CACHE[cache_key] = {"time": now_ts, "data": parsed_cache}
                    headers = {
                        "Cache-Control": "public, max-age=60, s-maxage=120, stale-while-revalidate=300",
                        "X-Cache": "HIT-REDIS",
                        "X-Skipped-Local-Fallback": "true",
                    }
                    return JSONResponse(content=parsed_cache, headers=headers)
            except Exception as e:
                logger.error(f"Redis fetch error: {e}")

        # Get delay hours from module-level cached tiers
        delay_hours = get_cached_tier_delay(user_plan)

        _VALID_LLM = "llm_classification_status.in.(completed,not_needed,skipped_local_fallback,pending,failed,verified),llm_classification_status.is.null"
        q = supabase.table("trends").select(FEED_CARD_COLUMNS).eq("status", "rising").eq("is_voiceover", False).eq("is_seed_data", False).or_(_VALID_LLM).gt("window_hours_remaining", 0)

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

        q = q.limit(100)
        skipped_local_fallback = True
        res = execute_supabase_get(q)
        trends = _normalize_trends(res.data or [])

        # Fallback: If delay_hours or strict rising filter returns 0 trends (e.g. fresh breakout trends detected <24h ago),
        # fallback to querying active (rising + emerging) trends so free/guest users never see an empty rail.
        if not trends:
            skipped_local_fallback = False
            q_fb = supabase.table("trends").select(FEED_CARD_COLUMNS).in_("status", ["rising", "emerging"]).eq("is_voiceover", False).eq("is_seed_data", False).or_(_VALID_LLM).gt("window_hours_remaining", 0)
            q_fb = _apply_languages_filter(q_fb, language, languages)
            q_fb = q_fb.limit(100)
            res_fb = execute_supabase_get(q_fb)
            trends = _normalize_trends(res_fb.data or [])


        # --- 70/30 Distribution: Indian/regional first, English/global after ---
        # Prioritise local trends but keep global variety.
        # Only applied when no specific language filter is active.
        active_lang = languages or language
        if not active_lang or active_lang == "all":
            _INDIAN_LANGS = {"hi", "ta", "te", "mr", "kn", "bn", "pa", "bho", "hne", "mai", "or", "", None}
            indian = [t for t in trends if (t.get("language") or "") in _INDIAN_LANGS
                      or (t.get("discovery_source") or "regional") != "global"]
            english = [t for t in trends if t not in indian]
            # Balanced 2:1 Interleaving (2 Indian : 1 Global) so global tracks appear throughout the feed
            interleaved = []
            i_idx, e_idx = 0, 0
            while i_idx < len(indian) or e_idx < len(english):
                for _ in range(2):
                    if i_idx < len(indian):
                        interleaved.append(indian[i_idx])
                        i_idx += 1
                if e_idx < len(english):
                    interleaved.append(english[e_idx])
                    e_idx += 1
            trends = interleaved

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

        freshness = _get_data_freshness()
        for t in trends:
            t["last_updated"] = freshness.get("last_updated")
            t["is_stale"] = freshness.get("is_stale", False)

        # Save to in-memory cache
        _TRENDS_FEED_CACHE[cache_key] = {"time": time.time(), "data": trends}
        if len(_TRENDS_FEED_CACHE) > 200:
            oldest_k = min(_TRENDS_FEED_CACHE.keys(), key=lambda k: _TRENDS_FEED_CACHE[k]["time"])
            _TRENDS_FEED_CACHE.pop(oldest_k, None)

        # Cache the result in Redis for 5 minutes
        if standard_queue and standard_queue.connection:
            try:
                standard_queue.connection.setex(cache_key, 300, json.dumps(trends))
            except Exception as e:
                logger.error(f"Redis cache write error: {e}")
                
        headers = {
            "Cache-Control": "public, max-age=60, s-maxage=120, stale-while-revalidate=300",
            "X-Cache": "MISS",
            "X-Skipped-Local-Fallback": "true" if skipped_local_fallback else "false",
            "X-Data-Last-Updated": freshness.get("last_updated") or "",
            "X-Data-Is-Stale": "true" if freshness.get("is_stale") else "false",
        }
        return JSONResponse(content=trends, headers=headers)
    except Exception as e:
        logger.error(f"Error fetching trends: {e}", exc_info=True)

        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/trends/freshness")
def get_trends_freshness():
    """
    Returns data freshness metrics across Instagram and Spotify sources.
    Includes last_updated, is_stale (>12h), and per-source last_success_at.
    """
    freshness = _get_data_freshness()
    headers = {
        "Cache-Control": "public, max-age=60",
        "X-Data-Last-Updated": freshness.get("last_updated") or "",
        "X-Data-Is-Stale": "true" if freshness.get("is_stale") else "false",
    }
    return JSONResponse(content=freshness, headers=headers)


# ── Scraper Run Freshness Batch Endpoint ───────────────────────────────────────

_SCRAPER_RUNS_CACHE: dict = {}

def _format_run_relative_time(dt_val) -> str:
    if not dt_val:
        return "recently"
    try:
        if isinstance(dt_val, str):
            dt_clean = dt_val.replace("Z", "+00:00")
            dt_obj = datetime.fromisoformat(dt_clean)
        elif isinstance(dt_val, datetime):
            dt_obj = dt_val
        else:
            return "recently"

        now = datetime.now(timezone.utc)
        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=timezone.utc)

        diff_sec = max(0, int((now - dt_obj).total_seconds()))
        if diff_sec < 60:
            return "just now"
        minutes = diff_sec // 60
        if minutes < 60:
            return f"{minutes}m ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h ago"
        days = hours // 24
        return f"{days}d ago"
    except Exception:
        return "recently"


@router.get("/api/trends/runs")
@router.get("/api/scraper/recent-runs")
@limiter.limit("60/minute")
def get_recent_scraper_runs(request: Request, limit: int = 6):
    """
    Fetch recent scraper runs from cron_runs table with discovered trend IDs.
    Powers the Scraper Run Freshness Batch filter in the UI.
    Placed BEFORE /api/trends/{trend_id} to prevent path parameter collision.
    """
    cache_key = f"scraper_runs:{limit}"
    now_ts = time.time()
    if cache_key in _SCRAPER_RUNS_CACHE:
        entry = _SCRAPER_RUNS_CACHE[cache_key]
        if now_ts - entry.get("time", 0) < 60:
            return JSONResponse(content=entry["data"])

    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")

    try:
        res = supabase.table("cron_runs") \
            .select("id, run_at, completed_at, new_trends_found, trend_ids, status, created_at") \
            .not_.is_("run_at", "null") \
            .order("id", desc=True) \
            .limit(limit) \
            .execute()

        runs_raw = res.data or []
        if not runs_raw:
            res_fb = supabase.table("cron_runs") \
                .select("id, run_at, completed_at, new_trends_found, trend_ids, status, created_at") \
                .order("id", desc=True) \
                .limit(limit) \
                .execute()
            runs_raw = res_fb.data or []

        formatted_runs = []
        letters = ["A", "B", "C", "D", "E", "F", "G", "H"]
        for idx, r in enumerate(runs_raw):
            letter = letters[idx] if idx < len(letters) else f"Run {idx + 1}"
            label_tag = "Latest" if idx == 0 else ("Previous" if idx == 1 else f"{idx + 1} runs ago")
            label = f"Run {letter} ({label_tag})"

            raw_ids = r.get("trend_ids") or []
            if isinstance(raw_ids, str):
                try:
                    raw_ids = json.loads(raw_ids)
                except Exception:
                    raw_ids = []

            clean_ids = []
            for tid in raw_ids:
                try:
                    clean_ids.append(int(tid))
                except (ValueError, TypeError):
                    continue

            run_time_str = r.get("run_at") or r.get("created_at")
            rel_time = _format_run_relative_time(run_time_str)

            formatted_runs.append({
                "run_id": r.get("id"),
                "letter": letter,
                "label": label,
                "relative_time": rel_time,
                "run_at": run_time_str,
                "completed_at": r.get("completed_at"),
                "new_trends_count": len(clean_ids) if clean_ids else (r.get("new_trends_found") or 0),
                "trend_ids": clean_ids,
                "status": r.get("status") or "completed",
            })

        result = {"runs": formatted_runs}
        _SCRAPER_RUNS_CACHE[cache_key] = {"time": now_ts, "data": result}
        return JSONResponse(content=result)

    except Exception as e:
        logger.exception(f"Error fetching scraper runs: {e}")
        return JSONResponse(content={"runs": []})


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
    lang_key = languages or language or "all"
    cache_key = f"emerging:{lang_key}"
    now_ts = time.time()
    if cache_key in _EMERGING_TRENDS_CACHE:
        entry = _EMERGING_TRENDS_CACHE[cache_key]
        if now_ts - entry.get("time", 0) < 60:
            headers = {
                "Cache-Control": "public, max-age=60, s-maxage=120, stale-while-revalidate=300",
                "X-Status-Filter": "emerging",
                "X-Cache": "HIT-MEM"
            }
            return JSONResponse(content=entry["data"], headers=headers)

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
        q = supabase.table("trends").select(FEED_CARD_COLUMNS).eq("status", "emerging").eq("is_voiceover", False).eq("is_seed_data", False).or_(_VALID_LLM)
        
        # 72-hour retention gate for Emerging tab (widened from 48h to capture more pre-viral trends)
        # Fixes: only 2 emerging audios shown when scraper pace slows
        emerging_cutoff = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
        q_72 = q.or_(
            f"first_detected_at.gte.{emerging_cutoff},"
            f"and(first_detected_at.is.null,created_at.gte.{emerging_cutoff})"
        )

        q_72 = _apply_languages_filter(q_72, language, languages)
        q_72 = q_72.order("velocity_avg", desc=True)
        q_72 = q_72.limit(100)
        res = q_72.execute()
        trends = _normalize_trends(res.data or [])

        # Supplement: pull recently-scraped PENDING audios (last 24h) as "just detected" signals.
        # These haven't been LLM-classified yet but are real live scrapes.
        try:
            pending_cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            q_pending = supabase.table("trends").select(FEED_CARD_COLUMNS) \
                .eq("status", "pending").eq("is_voiceover", False).eq("is_seed_data", False) \
                .or_(
                    f"first_detected_at.gte.{pending_cutoff},"
                    f"and(first_detected_at.is.null,created_at.gte.{pending_cutoff})"
                )
            q_pending = _apply_languages_filter(q_pending, language, languages)
            q_pending = q_pending.order("audio_use_count", desc=True).limit(30)
            res_pending = q_pending.execute()
            pending_trends = _normalize_trends(res_pending.data or [])
            # Mark them as emerging for the feed and deduplicate by audio_id
            existing_audio_ids = {t.get("audio_id") for t in trends if t.get("audio_id")}
            for pt in pending_trends:
                if pt.get("audio_id") not in existing_audio_ids:
                    pt["status"] = "emerging"   # surface as emerging in UI
                    pt["_is_just_detected"] = True
                    trends.append(pt)
                    existing_audio_ids.add(pt.get("audio_id"))
        except Exception as _pending_err:
            logger.warning(f"Pending supplement error: {_pending_err}")

        # Fallback: If still 0 emerging trends found, look back up to 7 days
        # so valid pre-viral emerging trends do not abruptly vanish if scraper pace slows
        if len(trends) == 0:
            try:
                emerging_cutoff_7d = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
                q_7d = supabase.table("trends").select(FEED_CARD_COLUMNS).eq("status", "emerging").eq("is_voiceover", False).eq("is_seed_data", False).or_(_VALID_LLM)
                q_7d = q_7d.or_(
                    f"first_detected_at.gte.{emerging_cutoff_7d},"
                    f"and(first_detected_at.is.null,created_at.gte.{emerging_cutoff_7d})"
                )
                q_7d = _apply_languages_filter(q_7d, language, languages)
                q_7d = q_7d.order("velocity_avg", desc=True).limit(50)
                res_7d = q_7d.execute()
                trends = _normalize_trends(res_7d.data or [])
            except Exception as _lookback_err:
                logger.warning(f"Emerging 7d lookback error: {_lookback_err}")

        # --- 70/30 Distribution for Emerging tab ---
        active_lang = languages or language
        if not active_lang or active_lang == "all":
            _INDIAN_LANGS = {"hi", "ta", "te", "mr", "kn", "bn", "pa", "bho", "hne", "mai", "or"}
            indian = [t for t in trends if (t.get("language") or "") in _INDIAN_LANGS
                      or (t.get("discovery_source") or "") == "regional"]
            english = [t for t in trends if t not in indian]
            # Balanced 2:1 Interleaving (2 Indian : 1 Global) so global emerging trends appear throughout
            interleaved = []
            i_idx, e_idx = 0, 0
            while i_idx < len(indian) or e_idx < len(english):
                for _ in range(2):
                    if i_idx < len(indian):
                        interleaved.append(indian[i_idx])
                        i_idx += 1
                if e_idx < len(english):
                    interleaved.append(english[e_idx])
                    e_idx += 1
            trends = interleaved

        trends.sort(key=lambda t: _trend_priority_key(t, user_niche, user_lang), reverse=True)
        
        # Add user watermark ID to each trend for leak tracing
        if user_id:
            for trend in trends:
                trend["user_watermark_id"] = user_id
        
        _EMERGING_TRENDS_CACHE[cache_key] = {"time": time.time(), "data": trends}
        if len(_EMERGING_TRENDS_CACHE) > 100:
            oldest_k = min(_EMERGING_TRENDS_CACHE.keys(), key=lambda k: _EMERGING_TRENDS_CACHE[k]["time"])
            _EMERGING_TRENDS_CACHE.pop(oldest_k, None)

        headers = {
            "Cache-Control": "public, max-age=60, s-maxage=120, stale-while-revalidate=300",
            "X-Status-Filter": "emerging",
            "X-Cache": "MISS"
        }
        return JSONResponse(content=trends, headers=headers)
    except Exception as e:
        logger.error(f"Error fetching emerging trends: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/trends/last-detected")
def get_last_detected_times():
    """
    Returns the newest detection timestamp per trend status.
    Used by frontend empty states across all tabs to inform users
    when a trend of that category was last detected.
    """
    if not supabase:
        return JSONResponse(content={})
    try:
        statuses = ["emerging", "rising", "resurging", "peaked", "expired"]
        result = {}
        for st in statuses:
            r = (
                supabase.table("trends")
                .select("status, first_detected_at, created_at")
                .eq("status", st)
                .order("first_detected_at", desc=True)
                .limit(1)
                .execute()
            )
            if r.data:
                item = r.data[0]
                result[st] = item.get("first_detected_at") or item.get("created_at")
            else:
                result[st] = None
        return JSONResponse(content=result, headers={"Cache-Control": "public, max-age=60"})
    except Exception as e:
        logger.error(f"Error fetching last detected times: {e}")
        return JSONResponse(content={})



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
        q_trending = supabase.table("trends").select(FEED_CARD_COLUMNS) \
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
        res = supabase.table("trends").select(FEED_CARD_COLUMNS).in_("status", ["emerging", "rising"]).eq("is_seed_data", False).in_("llm_classification_status", ["completed", "not_needed", "skipped_local_fallback", "verified"]).order("velocity_avg", desc=True).limit(100).execute()
        trends = _normalize_trends(res.data or [])
        trends.sort(key=_trend_priority_key, reverse=True)
        headers = {"Cache-Control": "public, max-age=60, s-maxage=120, stale-while-revalidate=300"}
        return JSONResponse(content=trends, headers=headers)
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
            headers = {"X-Cache": "HIT", "Cache-Control": "public, max-age=300, s-maxage=300, stale-while-revalidate=600"}
            return JSONResponse(content=entry['data'], headers=headers)
            
    try:
        q = supabase.table("trends").select(FEED_CARD_COLUMNS).eq("status", "peaked").eq("is_seed_data", False).in_("llm_classification_status", ["completed", "not_needed", "skipped_local_fallback", "verified"])
        
        # 14-day retention gate for Peaked tab (max 14 days post-peak)
        peaked_cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        q = q.or_(
            f"first_detected_at.gte.{peaked_cutoff},"
            f"and(first_detected_at.is.null,created_at.gte.{peaked_cutoff})"
        )

        q = _apply_languages_filter(q, language, languages)
        q = q.order("first_detected_at", desc=True)
        limit_val = min(limit or 100, 100)
        q = q.limit(limit_val)
        res = q.execute()
        trends = _normalize_trends(res.data or [])
        trends.sort(key=_trend_priority_key, reverse=True)
        
        # Save to cache
        _PEAKED_TRENDS_CACHE[cache_key] = {'time': now, 'data': trends}
        
        headers = {"X-Cache": "MISS", "Cache-Control": "public, max-age=300, s-maxage=300, stale-while-revalidate=600"}
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
    lang_key = languages or language or "all"
    cache_key = f"resurging:{lang_key}:{limit}"
    now_ts = time.time()
    if cache_key in _RESURGING_TRENDS_CACHE:
        entry = _RESURGING_TRENDS_CACHE[cache_key]
        if now_ts - entry.get("time", 0) < 120:
            headers = {"Cache-Control": "public, max-age=120, s-maxage=180, stale-while-revalidate=360", "X-Status-Filter": "resurging", "X-Cache": "HIT-MEM"}
            return JSONResponse(content=entry["data"], headers=headers)

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
            .select(FEED_CARD_COLUMNS)
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
        
        _RESURGING_TRENDS_CACHE[cache_key] = {"time": time.time(), "data": trends}
        if len(_RESURGING_TRENDS_CACHE) > 100:
            oldest_k = min(_RESURGING_TRENDS_CACHE.keys(), key=lambda k: _RESURGING_TRENDS_CACHE[k]["time"])
            _RESURGING_TRENDS_CACHE.pop(oldest_k, None)

        headers = {"Cache-Control": "public, max-age=120, s-maxage=180, stale-while-revalidate=360", "X-Status-Filter": "resurging", "X-Cache": "MISS"}
        return JSONResponse(content=trends, headers=headers)
    except Exception as e:
        logger.error(f"Error fetching resurging trends: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/trends/expired")
@limiter.limit("60/minute")
def get_expired_trends(
    request: Request, 
    language: Optional[str] = None, 
    languages: Optional[str] = None,
    limit: Optional[int] = None,
    current_user: str = Depends(get_current_user),
):
    """
    Fetch EXPIRED trends — trends that have passed their window or aged out.
    These are trends that are no longer active but may still have historical value.
    """
    lang_key = languages or language or "all"
    cache_key = f"expired:{lang_key}:{limit}"
    now_ts = time.time()
    if cache_key in _EXPIRED_TRENDS_CACHE:
        entry = _EXPIRED_TRENDS_CACHE[cache_key]
        if now_ts - entry.get("time", 0) < 300:
            headers = {"Cache-Control": "public, max-age=600, s-maxage=600, stale-while-revalidate=1200", "X-Status-Filter": "expired", "X-Cache": "HIT-MEM"}
            return JSONResponse(content=entry["data"], headers=headers)

    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    try:
        q = supabase.table("trends").select(FEED_CARD_COLUMNS).eq("status", "expired").eq("is_seed_data", False).in_("llm_classification_status", ["completed", "not_needed", "skipped_local_fallback", "verified"])
        
        # 30-day retention gate for Expired tab (max 30 days historical archive)
        expired_cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        q = q.or_(
            f"first_detected_at.gte.{expired_cutoff},"
            f"and(first_detected_at.is.null,created_at.gte.{expired_cutoff})"
        )
        q = _apply_languages_filter(q, language, languages)
        q = q.order("first_detected_at", desc=True)
        limit_val = min(limit or 100, 100)
        q = q.limit(limit_val)
        res = q.execute()
        trends = _normalize_trends(res.data or [])

        _EXPIRED_TRENDS_CACHE[cache_key] = {"time": time.time(), "data": trends}
        if len(_EXPIRED_TRENDS_CACHE) > 100:
            oldest_k = min(_EXPIRED_TRENDS_CACHE.keys(), key=lambda k: _EXPIRED_TRENDS_CACHE[k]["time"])
            _EXPIRED_TRENDS_CACHE.pop(oldest_k, None)

        headers = {"Cache-Control": "public, max-age=600, s-maxage=600, stale-while-revalidate=1200", "X-Status-Filter": "expired", "X-Cache": "MISS"}
        return JSONResponse(content=trends, headers=headers)
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
            .select(FEED_CARD_COLUMNS) \
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
                .select(FEED_CARD_COLUMNS) \
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
            .select(FEED_CARD_COLUMNS) \
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

        trends_res = supabase.table("trends").select(FEED_CARD_COLUMNS).in_("id", trend_ids).execute()
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
            .select(FEED_CARD_COLUMNS) \
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

