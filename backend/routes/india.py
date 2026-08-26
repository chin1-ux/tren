from fastapi import APIRouter, HTTPException, Depends, Request, Header, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import os, json, time, logging, traceback
from api_globals import *
from schemas import *

router = APIRouter()

@router.get("/api/india/regional-trends")
@limiter.limit("30/minute")
def get_regional_trends(
    request: Request,
    region: Optional[str] = None,
    current_user: str = Depends(get_current_user),
    _plan_check: str = Depends(require_feature("india_features"))
):
    """Get trends specific to Indian regions."""
    if not IndiaFeaturesEngine:
        raise HTTPException(status_code=500, detail="India features engine not configured.")
    
    try:
        engine = IndiaFeaturesEngine()
        trends = engine.detect_regional_trends(region=region)
        
        return {
            'regional_trends': [
                {
                    'region': trend.region,
                    'city': trend.city,
                    'language': trend.language,
                    'trend_name': trend.trend_name,
                    'viral_score': trend.viral_score,
                    'cultural_context': trend.cultural_context,
                    'peak_hours': trend.peak_hours,
                    'hashtags': trend.hashtags,
                    'content_themes': trend.content_themes
                }
                for trend in trends
            ],
            'total_trends': len(trends)
        }
    except Exception as e:
        logger.exception(f"Error getting regional trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to get regional trends")


@router.get("/api/india/regional-timing")
@limiter.limit("30/minute")
def get_regional_timing_optimization(
    request: Request,
    region: str = "north",
    current_user: str = Depends(get_current_user),
    _plan_check: str = Depends(require_feature("india_features"))
):
    """Get optimal posting times for a specific Indian region."""
    if not IndiaFeaturesEngine:
        raise HTTPException(status_code=500, detail="India features engine not configured.")
    
    try:
        engine = IndiaFeaturesEngine()
        timing = engine.get_regional_timing_optimization(region)
        
        return {
            'region': timing.region,
            'city': timing.city,
            'peak_hours': timing.peak_hours,
            'secondary_hours': timing.secondary_hours,
            'best_days': timing.best_days,
            'timezone_offset': timing.timezone_offset,
            'cultural_considerations': timing.cultural_considerations
        }
    except Exception as e:
        logger.exception(f"Error getting regional timing: {e}")
        raise HTTPException(status_code=500, detail="Failed to get regional timing")


@router.post("/api/india/detect-language")
@limiter.limit("30/minute")
def detect_language_crossover(
    request: Request,
    content: str,
    current_user: str = Depends(require_auth)
):
    """Detect which Indian languages are present in content."""
    if not IndiaFeaturesEngine:
        raise HTTPException(status_code=500, detail="India features engine not configured.")
    
    try:
        engine = IndiaFeaturesEngine()
        languages = engine.detect_language_crossover(content)
        return {
            'detected_languages': languages,
            'content': content
        }
    except Exception as e:
        logger.exception(f"Error detecting languages: {e}")
        raise HTTPException(status_code=500, detail="Failed to detect languages")


@router.get("/api/india/hashtag-strategy")
@limiter.limit("30/minute")
def get_regional_hashtag_strategy(
    request: Request,
    region: str = "north",
    content_type: str = "general",
    current_user: str = Depends(get_current_user)
):
    """Get hashtag strategy tailored to a specific Indian region."""
    if not IndiaFeaturesEngine:
        raise HTTPException(status_code=500, detail="India features engine not configured.")
    
    try:
        engine = IndiaFeaturesEngine()
        strategy = engine.get_regional_hashtag_strategy(region, content_type)
        return strategy
    except Exception as e:
        logger.exception(f"Error getting regional hashtag strategy: {e}")
        raise HTTPException(status_code=500, detail="Failed to get regional hashtag strategy")


@router.get("/api/india/creator-patterns")
@limiter.limit("30/minute")
def get_creator_pattern_analysis(
    request: Request,
    creator_region: str = "north",
    current_user: str = Depends(get_current_user)
):
    """Get creator pattern analysis specific to a region."""
    if not IndiaFeaturesEngine:
        raise HTTPException(status_code=500, detail="India features engine not configured.")
    
    try:
        engine = IndiaFeaturesEngine()
        patterns = engine.get_creator_pattern_analysis(creator_region)
        return patterns
    except Exception as e:
        logger.exception(f"Error getting creator patterns: {e}")
        raise HTTPException(status_code=500, detail="Failed to get creator patterns")


@router.get("/api/india/cultural-events")
@limiter.limit("30/minute")
def get_cultural_events(
    request: Request,
    days_ahead: int = 90,
    current_user: str = Depends(get_current_user),
    _plan_check: str = Depends(require_feature("india_features"))
):
    """Get upcoming India-specific cultural events."""
    if not CulturalEventCalendar:
        raise HTTPException(status_code=500, detail="Cultural event calendar not configured.")
    
    try:
        events = CulturalEventCalendar.get_upcoming_events(days_ahead)
        # Dual-key response: 'events' for EarlyDetectionPanel, 'cultural_events' for IndiaFeaturesDashboard
        # Known wart — one logical resource returning two shapes. Clean up when consumers align.
        return {
            'events': events,
            'cultural_events': [
                {
                    'event_name': e['name'],
                    'event_date': e['date'],
                    'content_automation': e.get('content_automation', []),
                    'creator_opportunities': e.get('creator_opportunities', [])
                }
                for e in events
            ],
            'total': len(events),
            'total_events': len(events)
        }
    except Exception as e:
        logger.exception(f"Error getting cultural events: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cultural events")


@router.get("/api/india/cultural-events/{event_name}")
@limiter.limit("30/minute")
def get_cultural_event_suggestions(
    request: Request,
    event_name: str,
    region: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """Get content suggestions for a specific cultural event."""
    if not CulturalEventCalendar:
        raise HTTPException(status_code=500, detail="Cultural event calendar not configured.")
    
    try:
        suggestions = CulturalEventCalendar.get_event_content_suggestions(event_name, region)
        return suggestions
    except Exception as e:
        logger.exception(f"Error getting cultural event suggestions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cultural event suggestions")


@router.get("/api/india/cultural-events/{event_name}/optimal-timing")
@limiter.limit("30/minute")
def get_cultural_event_timing(
    request: Request,
    event_name: str,
    current_user: str = Depends(get_current_user)
):
    """Get optimal posting window for a cultural event."""
    if not CulturalEventCalendar:
        raise HTTPException(status_code=500, detail="Cultural event calendar not configured.")
    
    try:
        window = CulturalEventCalendar.get_optimal_posting_window(event_name)
        return window
    except Exception as e:
        logger.exception(f"Error getting cultural event timing: {e}")
        raise HTTPException(status_code=500, detail="Failed to get optimal timing")


@router.get("/api/india/caption/generate")
@limiter.limit("10/minute")
def generate_india_caption(
    request: Request,
    trend_name: str,
    language: str = "hindi",
    tone: str = "casual",
    current_user: str = Depends(require_credits(CREDIT_COSTS['ai_generation']))
):
    """Generate India-specific caption in regional language."""
    if not ContentGenerator:
        raise HTTPException(status_code=500, detail="Content generator not configured.")
    
    try:
        generator = ContentGenerator()
        caption = generator.generate_india_caption(trend_name, language, tone)
        
        return {
            'caption': caption.caption,
            'hashtags': caption.hashtags,
            'tone': caption.tone,
            'cta': caption.cta
        }
    except Exception as e:
        logger.exception(f"Error generating India caption: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate caption")


@router.get("/api/india/content-ideas/generate")
@limiter.limit("10/minute")
def generate_india_content_ideas(
    request: Request,
    event_type: str = "festival",
    count: int = 3,
    current_user: str = Depends(require_credits(CREDIT_COSTS['ai_generation']))
):
    """Generate India-specific content ideas for cultural events."""
    if not ContentGenerator:
        raise HTTPException(status_code=500, detail="Content generator not configured.")
    
    try:
        generator = ContentGenerator()
        ideas = generator.generate_india_content_ideas(event_type, count)
        
        return {
            'ideas': [
                {
                    'title': idea.title,
                    'description': idea.description,
                    'content_type': idea.content_type,
                    'niche': idea.niche,
                    'difficulty': idea.difficulty,
                    'script_outline': idea.script_outline,
                    'hashtags': idea.suggested_hashtags
                }
                for idea in ideas
            ],
            'total': len(ideas)
        }
    except Exception as e:
        logger.exception(f"Error generating India content ideas: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate content ideas")


@router.get("/api/india/cultural-event/{event_name}")
@limiter.limit("30/minute")
def get_cultural_event(
    request: Request,
    event_name: str,
    current_user: str = Depends(require_credits(CREDIT_COSTS['ai_generation']))
):
    """Get content suggestions for a specific cultural event."""
    if not ContentGenerator:
        raise HTTPException(status_code=500, detail="Content generator not configured.")
    
    try:
        generator = ContentGenerator()
        event_data = generator.get_cultural_event_content(event_name)
        return event_data
    except Exception as e:
        logger.exception(f"Error getting cultural event: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cultural event")


