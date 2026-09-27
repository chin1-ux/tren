from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List, Optional
import logging
from datetime import datetime, timezone
from api_globals import supabase, require_auth
from schemas import UserPreferencesRequest, UserLanguagePreferencesRequest

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


ALLOWED_LANGUAGES = {
    "hi", "pa", "ta", "te", "kn", "ml", "mr", "bn", "gu", "ne",
    "en", "es", "pt", "ko", "instrumental", "other"
}

@router.put("/api/users/language-preferences")
def update_user_language_preferences(
    req: UserLanguagePreferencesRequest = Body(...),
    current_user: str = Depends(require_auth)
):
    """
    Update preferred languages for authenticated user.
    Validates against ALLOWED_LANGUAGES, rejecting with HTTP 400 if invalid.
    """
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not configured")

        valid_langs = []
        for code in req.languages:
            clean_code = str(code).strip().lower()
            if clean_code not in ALLOWED_LANGUAGES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid language code: '{code}'. Allowed languages: {sorted(list(ALLOWED_LANGUAGES))}"
                )
            if clean_code not in valid_langs:
                valid_langs.append(clean_code)

        data = {
            "email": current_user,
            "preferred_languages": valid_langs,
            "languages": valid_langs,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        # Upsert preferences
        res = supabase.table("user_preferences").upsert(data).execute()
        
        # Optional: sync to users table if exists
        try:
            supabase.table("users").update({"preferred_languages": valid_langs}).eq("email", current_user).execute()
        except Exception as _ue:
            logger.debug(f"users table sync optional: {_ue}")

        return {
            "success": True,
            "message": "Language preferences updated successfully",
            "preferred_languages": valid_langs,
            "preferences": res.data[0] if res.data else data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating language preferences for {current_user}: {e}")
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

