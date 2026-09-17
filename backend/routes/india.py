from fastapi import APIRouter, HTTPException, Depends, Request, Header, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import os, json, time, logging, traceback, re
from datetime import datetime, timezone, timedelta
from api_globals import *
from schemas import *

router = APIRouter()

# Meme / non-news signal keywords — if post caption matches these, it's not a newsworthy story
_MEME_SIGNALS = re.compile(
    r"tag (a |your )?(friend|bro|sis|someone|anyone)"
    r"|who did it better"
    r"|comment (below|down|your)?"
    r"|drop a (❤️|🔥|💯|👇)"
    r"|follow (us|me|for more)"
    r"|wait for it"
    r"|part [0-9]"
    r"|\btag\b.{0,15}\b(for|to)\b"
    r"|repost this"
    r"|dm (us|me) for"
    r"|giveaway",
    re.IGNORECASE
)

_NEWS_SOURCES = {
    "ndtv", "the hindu", "hindustan times", "times of india", "india today",
    "economic times", "mint", "bbc", "reuters", "ap news", "the wire",
    "scroll", "quint", "newslaundry", "firstpost", "the print", "espn",
    "cricinfo", "433", "complex", "variety", "deadline", "billboard",
    "rolling stone", "nme", "pitchfork"
}


def _is_news_content(item: dict) -> bool:
    """Returns True if this content_trends row is genuine news (not a meme/entertainment post)."""
    name = (item.get("trend_name") or "").lower()
    keywords = " ".join(item.get("topic_keywords") or []).lower()
    combined = f"{name} {keywords}"
    # If it matches meme signals, reject
    if _MEME_SIGNALS.search(combined):
        return False
    # If name ends with '- Source Name' pattern (typical news headline format), pass
    if re.search(r" - [A-Za-z ]{3,40}$", item.get("trend_name") or ""):
        return True
    # Allow if source name is in our known news sources whitelist
    for src in _NEWS_SOURCES:
        if src in combined:
            return True
    # If it's a factual-looking headline (contains year, numbers, proper nouns)
    if re.search(r"\b(20[0-9]{2}|[A-Z][a-z]+ [A-Z][a-z]+|\d+%|\$\d+|₹\d+)\b", item.get("trend_name") or ""):
        return True
    return False


def _get_news_cutoff_iso(hours: int = 72) -> str:
    """Returns ISO timestamp for the news recency cutoff."""
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


@router.get("/api/india/cultural-events")
@limiter.limit("30/minute")
def get_cultural_events(
    request: Request,
    days_ahead: int = 90,
    current_user: str = Depends(get_current_user)
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


@router.get("/api/content-trends")
@limiter.limit("60/minute")
def get_content_trends(
    request: Request,
    type: Optional[str] = None,
    recency_hours: int = 72,
    current_user: str = Depends(get_current_user)
):
    """
    Fetch high-impact live news and pop culture trends.
    - trend_type 'news' (was incorrectly queried as 'news_event' — now fixed)
    - Filtered to recency_hours (default 72h) to ensure freshness
    - Meme/non-news posts are filtered out via keyword analysis
    """
    if supabase:
        try:
            q = supabase.table("content_trends").select("*")

            # DB stores trend_type as 'news' — support legacy 'news_event' param alias too
            if type:
                if type in ("news_event", "news"):
                    # Accept both aliases; DB column value is 'news'
                    q = q.eq("trend_type", "news")
                else:
                    q = q.eq("trend_type", type)
            else:
                # Default: only return news items for this endpoint
                q = q.eq("trend_type", "news")

            # Recency filter — only items updated within recency_hours
            cutoff = _get_news_cutoff_iso(recency_hours)
            q = q.gte("last_updated_at", cutoff)

            q = q.order("confidence", desc=True).limit(30)
            res = q.execute()

            if res.data and len(res.data) > 0:
                # Filter out meme-like posts at the service layer
                filtered = [item for item in res.data if _is_news_content(item)]
                if filtered:
                    logger.info(f"content-trends: returning {len(filtered)} verified news items (from {len(res.data)} raw)")
                    return filtered
                else:
                    logger.info("content-trends: all items filtered as non-news. Returning empty.")
            else:
                logger.info(f"content-trends: no items in last {recency_hours}h. DB has data but nothing recent.")

        except Exception as e:
            logger.warning(f"Error fetching content_trends from DB: {e}")

    # No fabricated fallback — return empty with metadata so frontend can show honest empty state
    return []


@router.get("/api/news/virality-predictions")
@limiter.limit("60/minute")
def get_news_virality_predictions(
    request: Request,
    limit: int = 10,
    current_user: str = Depends(get_current_user)
):
    """Alias endpoint for NewsFeedPanel virality predictions — wraps content-trends with news type."""
    return get_content_trends(request=request, type="news", recency_hours=72, current_user=current_user)


