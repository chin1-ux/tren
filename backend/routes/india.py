from fastapi import APIRouter, HTTPException, Depends, Request, Header, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import os, json, time, logging, traceback
from api_globals import *
from schemas import *

router = APIRouter()


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


