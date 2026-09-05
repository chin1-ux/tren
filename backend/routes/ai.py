from fastapi import APIRouter, HTTPException, Depends, Request, Header, UploadFile, File, Form, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import os, json, time, logging, traceback
from api_globals import *
from api_globals import standard_queue
from schemas import *

router = APIRouter()

@router.post("/api/prepost-score")
@limiter.limit("5/minute")
def get_prepost_score(request: Request, req: PrePostRequest, current_user_email: str = Depends(require_auth)):
    try:
        res = creator_tools.get_pre_post_score(
            niche=req.niche,
            hook=req.hook,
            audio_title=req.audio_title,
            caption=req.caption,
            hashtags=req.hashtags,
            post_time=req.post_time
        )
        # Save to DB
        analysis_data = {
            "user_email": current_user_email,
            "video_url": "",
            "analysis_details": res,
            "score": res.get("overall_score", 0)
        }
        supabase.table("pre_post_analyses").insert(analysis_data).execute()
        return res
    except Exception as e:
        logger.error(f"Error in /api/prepost-score: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/api/generate-hooks")
@limiter.limit("10/minute")
def generate_hooks(request: Request, req: HookRequest, current_user: str = Depends(get_current_user), _credit_check: str = Depends(require_credits(CREDIT_COSTS['ai_generation']))):
    try:
        niche = req.trend or req.niche or "lifestyle"
        topic = req.content_description or req.topic or "viral reels"
        result = creator_tools.generate_hooks(niche=niche, topic=topic)
        return result
    except Exception as e:
        logger.exception(f"Error in /api/generate-hooks: {e}")
        # Return fallback hooks instead of error
        return {
            "hooks": [
                {"style": "Curiosity", "text": f"Why nobody is talking about {topic}", "why_it_works": "Intrigue"},
                {"style": "Authority", "text": f"The only {niche} guide you need for {topic}", "why_it_works": "Establishes immediate value"},
                {"style": "Relatable", "text": "I was today years old when I learned this about " + topic, "why_it_works": "Humor & connection"}
            ]
        }


@router.post("/api/score-reel")
@limiter.limit("20/hour")
def score_reel(request: Request, req: ScoreReelRequest, current_user_email: str = Depends(require_auth)):
    try:
        import re
        hashtags = re.findall(r"#\w+", req.caption)
        hook = req.caption.split('\n')[0] if '\n' in req.caption else req.caption.split('.')[0]
        if not hook:
            hook = "Check this out!"

        try:
            res = creator_tools.get_pre_post_score(
                niche=req.niche,
                hook=hook,
                audio_title=req.audio,
                caption=req.caption,
                hashtags=hashtags,
                post_time=req.posting_time
            )
        except Exception as e:
            logger.warning(f"LLM scoring failed, using fallback: {e}")
            res = {
                "overall_score": 75,
                "breakdown": {"hook_strength": 70, "audio_match": 80, "seo_and_caption": 70, "hashtags": 80, "timing": 80},
                "fixes": ["Keep the first 3 seconds extremely fast-paced.", "Optimize the caption with target keywords."],
                "estimated_reach_multiplier": "1.2x",
                "is_fallback": True,
                "fallback_reason": "LLM unavailable — showing generic score"
            }

        overall = res.get("overall_score", 75)
        breakdown = res.get("breakdown", {})

        if overall >= 90:
            grade = "A+"
        elif overall >= 80:
            grade = "A"
        elif overall >= 70:
            grade = "B"
        elif overall >= 60:
            grade = "C"
        else:
            grade = "D"

        try:
            analysis_data = {
                "user_email": current_user_email,
                "video_url": "",
                "analysis_details": res,
                "score": overall
            }
            supabase.table("pre_post_analyses").insert(analysis_data).execute()
        except Exception as e:
            logger.exception(f"Failed to persist pre_post analysis for user {current_user_email}: {e}")

        return {
            "overall_score": overall,
            "grade": grade,
            "hook_score": breakdown.get("hook_strength", 70),
            "audio_score": breakdown.get("audio_match", 70),
            "caption_score": breakdown.get("seo_and_caption", 70),
            "hashtag_score": breakdown.get("hashtags", 70),
            "timing_score": breakdown.get("timing", 70),
            "top_fixes": res.get("fixes", []),
            "is_fallback": res.get("is_fallback", False),
            "fallback_reason": res.get("fallback_reason"),
        }
    except Exception as e:
        logger.error(f"Error in /api/score-reel: {e}", exc_info=True)
        # Return fallback score instead of error
        return {
            "overall_score": 75,
            "grade": "B",
            "hook_score": 70,
            "audio_score": 70,
            "caption_score": 70,
            "hashtag_score": 70,
            "timing_score": 70,
            "top_fixes": ["Keep the first 3 seconds extremely fast-paced.", "Optimize the caption with target keywords."],
            "is_fallback": True,
            "fallback_reason": "LLM unavailable — showing generic score"
        }


@router.get("/api/daily-ideas/{user_email}")
@limiter.limit("10/minute")
def get_daily_ideas_by_email(user_email: str, request: Request, current_user_email: str = Depends(require_auth)):
    if user_email != current_user_email:
        raise HTTPException(status_code=403, detail="Forbidden: You cannot access daily ideas of another user")

    # 2.2 CACHING: ideas:{user_email}:{date}
    import datetime as dt
    today_str = dt.date.today().isoformat()
    cache_key = f"ideas:{user_email}:{today_str}"

    if standard_queue and standard_queue.connection:
        try:
            cached_data = standard_queue.connection.get(cache_key)
            if cached_data:
                logger.info(f"Serving daily ideas from cache for: {cache_key}")
                return json.loads(cached_data)
        except Exception as e:
            logger.error(f"Redis fetch error for ideas: {e}")

    try:
        ideas = creator_tools.get_daily_ideas(user_email=user_email)
    except Exception as e:
        logger.warning(f"LLM daily ideas failed, using fallback: {e}")
        # Fallback ideas
        ideas = [
            {"title": "The Ultimate Lifestyle Hack", "description": "Show a 15-second hack of something in your niche.", "hook": "Stop doing it the hard way!", "audio_suggestion": "Upbeat trending pop", "posting_time": "6:30 PM", "is_fallback": True, "fallback_reason": "LLM unavailable — showing template ideas"},
            {"title": "Day in the Life", "description": "B-roll of your daily routine with text overlay.", "hook": "What my typical day actually looks like...", "audio_suggestion": "Chill Lofi", "posting_time": "8:00 PM", "is_fallback": True, "fallback_reason": "LLM unavailable — showing template ideas"},
            {"title": "My Biggest Mistake", "description": "Share a relatable mistake and how you solved it.", "hook": "Don't make this mistake I made...", "audio_suggestion": "Dramatic build-up", "posting_time": "7:15 PM", "is_fallback": True, "fallback_reason": "LLM unavailable — showing template ideas"}
        ]

    difficulties = ["Easy", "Medium", "Hard"]
    for i, idea in enumerate(ideas):
        if "difficulty" not in idea:
            idea["difficulty"] = difficulties[i % len(difficulties)]

    # Cache ideas for 1 hour
    if standard_queue and standard_queue.connection:
        try:
            standard_queue.connection.setex(cache_key, 3600, json.dumps(ideas))
        except Exception as e:
            logger.error(f"Redis write error for ideas: {e}")

    return ideas


@router.get("/api/generate-calendar/{user_email}")
@limiter.limit("5/minute")
def generate_calendar_for_user(user_email: str, request: Request, current_user_email: str = Depends(get_current_user), _credit_check: str = Depends(require_credits(CREDIT_COSTS['ai_generation']))):
    if user_email != current_user_email:
        raise HTTPException(status_code=403, detail="Forbidden: You cannot generate a calendar for another user")
    try:
        niche = "lifestyle"
        language = "en"
        frequency = "daily"

        if supabase:
            try:
                user_data = get_cached_user_profile(user_email)
                if user_data:
                    niche = user_data.get("niche", niche)
                    language = user_data.get("language_preference", language)
            except Exception as db_err:
                logger.warning(f"Error fetching user for calendar: {db_err}")

        try:
            res = creator_tools.generate_calendar(
                user_email=user_email,
                niche=niche,
                language=language,
                frequency=frequency
            )
        except Exception as e:
            logger.warning(f"LLM calendar generation failed, using fallback: {e}")
            # Fallback calendar
            res = {
                "is_fallback": True,
                "fallback_reason": "LLM unavailable — showing generic calendar template",
                "calendar": [
                    {"day": i, "topic": f"Day {i} challenge/tip", "hook": f"Here is tip #{i}...", "audio_style": "Trending audio", "hashtags": [f"#{niche}"], "posting_time": "6:00 PM"}
                    for i in range(1, 31)
                ]
            }

        if supabase:
            try:
                calendar_data = {
                    "user_email": user_email,
                    "niche": niche,
                    "language": language,
                    "frequency": frequency,
                    "schedule_data": res
                }
                supabase.table("calendar_plans").upsert(calendar_data, on_conflict="user_email").execute()
            except Exception as db_err:
                logger.warning(f"Error saving calendar to DB: {db_err}")
        return res

    except Exception as e:
        logger.error(f"Error in /api/generate-calendar/{user_email}: {e}", exc_info=True)
        # Return fallback calendar instead of error
        return {
            "is_fallback": True,
            "fallback_reason": "Server error — showing generic calendar template",
            "calendar": [
                {"day": i, "topic": f"Day {i} challenge/tip", "hook": f"Here is tip #{i}...", "audio_style": "Trending audio", "hashtags": ["#lifestyle"], "posting_time": "6:00 PM"}
                for i in range(1, 31)
            ]
        }


@router.post("/api/seo-caption")
@limiter.limit("10/minute")
def generate_seo_caption(request: Request, req: SeoCaptionRequest, current_user_email: str = Depends(require_credits(CREDIT_COSTS['ai_generation']))):
    try:
        return creator_tools.generate_seo_caption(description=req.description, platform=req.platform)
    except Exception as e:
        logger.error(f"Error in /api/seo-caption: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/daily-ideas")
@limiter.limit("10/minute")
def get_daily_ideas(request: Request, current_user_email: str = Depends(require_credits(CREDIT_COSTS['ai_generation']))):
    # CACHING: ideas:{user_email}:{date}
    import datetime as dt
    today_str = dt.date.today().isoformat()
    cache_key = f"ideas:{current_user_email}:{today_str}"
    
    if standard_queue and standard_queue.connection:
        try:
            cached_data = standard_queue.connection.get(cache_key)
            if cached_data:
                logger.info(f"Serving daily ideas from cache for: {cache_key}")
                return json.loads(cached_data)
        except Exception as e:
            logger.error(f"Redis fetch error for ideas: {e}")

    try:
        ideas = creator_tools.get_daily_ideas(user_email=current_user_email)
        difficulties = ["Easy", "Medium", "Hard"]
        for i, idea in enumerate(ideas):
            if "difficulty" not in idea:
                idea["difficulty"] = difficulties[i % len(difficulties)]
                
        # Cache ideas for 1 hour
        if standard_queue and standard_queue.connection:
            try:
                standard_queue.connection.setex(cache_key, 3600, json.dumps(ideas))
            except Exception as e:
                logger.error(f"Redis write error for ideas: {e}")
                
        return ideas
    except Exception as e:
        logger.error(f"Error in /api/daily-ideas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/api/calendar")
@limiter.limit("5/minute")
def create_calendar(request: Request, req: CalendarRequest, current_user_email: str = Depends(get_current_user), _credit_check: str = Depends(require_credits(CREDIT_COSTS['ai_generation']))):
    try:
        try:
            res = creator_tools.generate_calendar(
                user_email=current_user_email,
                niche=req.niche,
                language=req.language,
                frequency=req.frequency
            )
        except Exception as e:
            logger.warning(f"LLM calendar generation failed, using fallback: {e}")
            # Fallback calendar
            res = {
                "calendar": [
                    {"day": i, "topic": f"Day {i} challenge/tip", "hook": f"Here is tip #{i}...", "audio_style": "Trending audio", "hashtags": [f"#{req.niche}"], "posting_time": "6:00 PM"}
                    for i in range(1, 31)
                ]
            }
        # Upsert in DB
        calendar_data = {
            "user_email": current_user_email,
            "niche": req.niche,
            "language": req.language,
            "frequency": req.frequency,
            "schedule_data": res
        }
        supabase.table("calendar_plans").upsert(calendar_data, on_conflict="user_email").execute()
        return res
    except Exception as e:
        logger.error(f"Error in /api/calendar: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/calendar")
@limiter.limit("10/minute")
def get_calendar(request: Request, current_user_email: str = Depends(get_current_user), _credit_check: str = Depends(require_credits(CREDIT_COSTS['ai_generation']))):
    try:
        res = supabase.table("calendar_plans").select("*").eq("user_email", current_user_email).execute()
        if res.data:
            return res.data[0]["schedule_data"]
        return {"calendar": []}
    except Exception as e:
        logger.exception(f"Error getting calendar: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/api/ai/generate-caption")
@limiter.limit("20/minute")
def generate_caption(
    request: Request,
    trend_id: int = Query(..., description="ID of the trend to generate caption kit for"),
    current_user: str = Depends(get_current_user),
    _credit_check: str = Depends(require_credits(CREDIT_COSTS['ai_generation']))
):
    """Generate an AI caption kit for a specific trend."""
    try:
        from caption_engine import CaptionEngine
        engine = CaptionEngine()
        caption_kit = engine.get_caption_kit(trend_id)
        
        return caption_kit
    except ValueError as ve:
        logger.warning(f"Validation error in caption generation: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception(f"Error generating caption kit: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate caption kit")


@router.post("/api/video/analyze-metadata")
@limiter.limit("5/minute")
def analyze_video_metadata(
    request: Request,
    payload: VideoUrlRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
):
    """
    Analyze video metadata using FFmpeg, falling back to simulated data if not available.
    Credits are ONLY charged when real analysis is returned (not simulated).
    """
    temp_path = None
    try:
        video_url = payload.video_url
        
        if not VideoMetadataAnalyzer:
            return {
                'overall_score': 90.0,
                'scores': {
                    'duration': 90.0,
                    'aspect_ratio': 100.0,
                    'resolution': 80.0,
                    'frame_rate': 100.0,
                    'file_size': 100.0
                },
                'recommendations': [
                    "Optimal vertical aspect ratio detected (9:16).",
                    "Resolution (1080p) is highly optimal for mobile viewports."
                ],
                'is_simulated': True,
                'note': "FFmpeg is not configured on this server. Running in simulated fallback mode."
            }

        temp_path = _download_video_to_temp(video_url)
        raw_metadata = VideoMetadataAnalyzer.extract_metadata(temp_path)
        analysis = VideoMetadataAnalyzer.analyze_metadata_quality(raw_metadata)
        if isinstance(analysis, dict):
            analysis['is_simulated'] = False
            analysis['raw_metadata'] = raw_metadata
        background_tasks.add_task(PlanEnforcement.deduct_credits, current_user, CREDIT_COSTS['video_analysis'], reason='video_analysis', endpoint='/api/video/analyze-metadata')
        return analysis
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error analyzing video metadata: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze video metadata")
    finally:
        _cleanup_temp(temp_path)


@router.post("/api/video/analyze-visual")
@limiter.limit("5/minute")
def analyze_video_visual(
    request: Request,
    payload: VideoUrlRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
):
    """
    Analyze video visual content using OpenCV, falling back to simulated data if not available.
    Credits are ONLY charged when real analysis is returned (not simulated).
    """
    temp_path = None
    try:
        video_url = payload.video_url
        if not VideoVisualAnalyzer:
            return {
                'face_detection': {'face_present_percentage': 26.67, 'detected_faces_count': 1},
                'motion_analysis': {'has_constant_motion': True, 'motion_score': 85.0},
                'color_analysis': {'is_colorful': True, 'is_well_lit': True, 'vibrancy_score': 78.5},
                'scene_detection': {'edit_style': 'fast_cuts', 'scene_changes_count': 6},
                'text_detection': {'has_text_overlays': True, 'text_overlay_detected': True},
                'is_simulated': True,
                'note': "OpenCV/pytesseract is not configured on this server. Running in simulated fallback mode."
            }
        
        temp_path = _download_video_to_temp(video_url)
        analysis = VideoVisualAnalyzer.analyze_visual_content(temp_path)
        if isinstance(analysis, dict):
            analysis['is_simulated'] = False
        background_tasks.add_task(PlanEnforcement.deduct_credits, current_user, CREDIT_COSTS['video_analysis'], reason='video_analysis', endpoint='/api/video/analyze-visual')
        return analysis
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error analyzing video visual: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze video visual")
    finally:
        _cleanup_temp(temp_path)


@router.post("/api/video/predict-virality")
@limiter.limit("5/minute")
def predict_video_virality(
    request: Request,
    payload: VideoUrlRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
):
    """
    Predict video virality combining metadata and visual analysis.
    Credits are ONLY charged when real analysis is returned (not simulated).
    """
    temp_path = None
    try:
        video_url = payload.video_url

        if not VideoViralityScorer:
            return {
                'virality_score': 84.25,
                'viral_potential': "HIGH",
                'success_probability': 0.82,
                'score_breakdown': {
                    'metadata_score': 90.0,
                    'visual_score': 79.5,
                    'engagement_index': 83.25
                },
                'is_simulated': True,
                'note': "Virality scorer engine is not configured on this server. Running in simulated fallback mode."
            }
        
        temp_path = _download_video_to_temp(video_url)
        raw_metadata = VideoMetadataAnalyzer.extract_metadata(temp_path) if VideoMetadataAnalyzer else {}
        metadata_analysis = VideoMetadataAnalyzer.analyze_metadata_quality(raw_metadata) if VideoMetadataAnalyzer else {'overall_score': 50, 'scores': {}, 'recommendations': []}
        visual_analysis = VideoVisualAnalyzer.analyze_visual_content(temp_path) if VideoVisualAnalyzer else {}
        
        prediction = VideoViralityScorer.calculate_virality_score(metadata_analysis, visual_analysis)
        if isinstance(prediction, dict):
            prediction['is_simulated'] = False
        background_tasks.add_task(PlanEnforcement.deduct_credits, current_user, CREDIT_COSTS['video_analysis'], reason='video_analysis', endpoint='/api/video/predict-virality')
        return prediction
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error predicting video virality: {e}")
        raise HTTPException(status_code=500, detail="Failed to predict video virality")
    finally:
        _cleanup_temp(temp_path)


@router.post("/api/video/improvements")
@limiter.limit("5/minute")
def get_video_improvements(
    request: Request,
    payload: VideoUrlRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
):
    """
    Get improvement suggestions for video virality.
    Credits are ONLY charged when real analysis is returned (not simulated).
    """
    temp_path = None
    try:
        video_url = payload.video_url
        
        if not VideoViralityScorer:
            suggestions = [
                "Duration check: Keep video length between 15-30 seconds to optimize retention rate.",
                "Visual enhancements: Ensure good light setup and color vibrancy in the first 3 seconds.",
                "Overlay text styling: Use large, high-contrast subtitles to capture mute scroll viewers."
            ]
            return {
                'suggestions': suggestions,
                'total': len(suggestions),
                'is_simulated': True
            }

        temp_path = _download_video_to_temp(video_url)
        raw_metadata = VideoMetadataAnalyzer.extract_metadata(temp_path) if VideoMetadataAnalyzer else {}
        metadata_analysis = VideoMetadataAnalyzer.analyze_metadata_quality(raw_metadata) if VideoMetadataAnalyzer else {'overall_score': 50, 'scores': {}, 'recommendations': []}
        visual_analysis = VideoVisualAnalyzer.analyze_visual_content(temp_path) if VideoVisualAnalyzer else {}
        
        suggestions = VideoViralityScorer.get_improvement_suggestions(metadata_analysis, visual_analysis)
        background_tasks.add_task(PlanEnforcement.deduct_credits, current_user, CREDIT_COSTS['video_analysis'], reason='video_analysis', endpoint='/api/video/improvements')
        return {
            'suggestions': suggestions,
            'total': len(suggestions),
            'is_simulated': False
        }
    except Exception as e:
        logger.exception(f"Error getting video improvements: {e}")
        raise HTTPException(status_code=500, detail="Failed to get improvement suggestions")


