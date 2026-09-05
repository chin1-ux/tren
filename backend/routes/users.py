from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import logging
from datetime import datetime, timezone
from api_globals import supabase, require_auth
from schemas import UserPreferencesRequest

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/api/users/preferences")
def get_user_preferences(current_user: str = Depends(require_auth)):
    """
    Get user preferences including niches, languages, state, and notification settings
    """
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not configured")
            
        res = supabase.table("user_preferences").select("*").eq("email", current_user).execute()
        
        if not res.data:
            # Return default preferences if not found
            return {
                "success": True,
                "preferences": {
                    "email": current_user,
                    "niches": [],
                    "languages": ["en"],
                    "regions": ["IN"],
                    "creator_language": "en",
                    "state": None,
                    "global_enabled": False,
                    "notification_triggers": {},
                    "creator_tier": "nano",
                    "platform_focus": ["instagram"],
                    "saved_trends": []
                }
            }
            
        return {
            "success": True,
            "preferences": res.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user preferences for {current_user}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/api/users/preferences")
def update_user_preferences(
    req: UserPreferencesRequest,
    current_user: str = Depends(require_auth)
):
    """
    Update user preferences
    """
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not configured")
            
        data = {
            "email": current_user,
            "niches": req.niches,
            "languages": req.languages,
            "regions": req.regions,
            "creator_language": req.creator_language,
            "state": req.state,
            "global_enabled": req.global_enabled,
            "notification_triggers": req.notification_triggers,
            "creator_tier": req.creator_tier,
            "platform_focus": req.platform_focus,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Upsert preferences
        res = supabase.table("user_preferences").upsert(data).execute()
        
        return {
            "success": True,
            "message": "Preferences updated successfully",
            "preferences": res.data[0] if res.data else data
        }
    except Exception as e:
        logger.error(f"Error updating user preferences for {current_user}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/content-trends")
def get_content_trends(
    type: Optional[str] = None,
    limit: int = 20,
    current_user: str = Depends(require_auth),
):
    """
    Fetch content_trends from the unified signal processor.
    Optionally filter by trend_type (e.g. 'news_event', 'format_trend', 'predictable_event').
    """
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not configured")

        q = supabase.table("content_trends").select("*").order("last_updated_at", desc=True).limit(limit)
        if type:
            q = q.eq("trend_type", type)

        res = q.execute()
        return res.data or []
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching content_trends: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

