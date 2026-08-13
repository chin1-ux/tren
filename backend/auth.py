import os
import logging
from fastapi import Header, HTTPException, status, Depends
from supabase import create_client, Client
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables early to ensure they are available for authentication
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

# Handle missing Supabase credentials gracefully for CI/testing
if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning("SUPABASE_URL and SUPABASE_KEY not set - auth system will be disabled")
    supabase = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_current_user(authorization: str = Header(None)) -> str:
    """
    Validate the Supabase JWT or custom auth_token in the Authorization header.
    Returns the user's email if valid. Falls back to guest@trendrop.app if invalid or missing.
    """
    if not supabase:
        return "guest@trendrop.app"
    
    if not authorization or not authorization.startswith("Bearer "):
        return "guest@trendrop.app"
    
    token = authorization.split("Bearer ")[1].strip()
    if not token:
        return "guest@trendrop.app"
    
    # 1. Try custom auth_token check first
    try:
        res = supabase.table("users").select("email").eq("auth_token", token).limit(1).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]["email"]
    except Exception:
        pass

    # 2. Validate token using Supabase Auth JWT validator
    try:
        user_res = supabase.auth.get_user(jwt=token)
        if user_res and user_res.user:
            email = user_res.user.email
            if email:
                return email
    except Exception as e:
        pass

    return "guest@trendrop.app"

def require_admin(current_user: str = Depends(get_current_user)) -> str:
    """
    Dependency that checks if the current user has admin role.
    Raises 403 if user is not an admin.
    Returns the user's email if authorized.
    """
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth system not configured"
        )
    
    if current_user == "guest@trendrop.app":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        # Check user's role from users table
        res = supabase.table("users").select("role", "id").eq("email", current_user).single().execute()
        
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not found"
            )
        
        user_role = res.data.get("role")
        user_id = res.data.get("id")
        
        if user_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        # Return both email and id for audit logging
        return current_user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify admin status"
        )

