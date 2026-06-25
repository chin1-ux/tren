import os
from fastapi import Header, HTTPException, status, Depends
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables early to ensure they are available for authentication
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "trendrop_dev_admin_secret_key_2026")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_current_user(authorization: str = Header(None)) -> str:
    """
    Validate the Supabase JWT or the custom subscription auth_token in the Authorization header.
    Returns the user's email if valid. Falls back to guest@trendrop.app if invalid or missing.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return "guest@trendrop.app"
    
    token = authorization.split("Bearer ")[1].strip()
    if not token:
        return "guest@trendrop.app"
    
    # 1. Try to validate as custom subscription auth_token
    try:
        res = supabase.table("users").select("email").eq("auth_token", token).execute()
        if res.data and len(res.data) > 0:
            email = res.data[0].get("email")
            if email:
                return email
    except Exception as e:
        pass

    # 2. Fall back to validating as Supabase JWT
    try:
        user_res = supabase.auth.get_user(jwt=token)
        if user_res and user_res.user:
            email = user_res.user.email
            if email:
                return email
    except Exception as e:
        pass

    return "guest@trendrop.app"

def get_admin_user(x_admin_key: str = Header(None)) -> bool:
    """
    Validates X-Admin-Key header against the ADMIN_SECRET_KEY.
    """
    if not x_admin_key or x_admin_key != ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized administrative request"
        )
    return True
