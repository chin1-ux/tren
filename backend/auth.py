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
    Validate the Supabase JWT in the Authorization header.
    Returns the user's email if valid.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header. Expected: Bearer <token>"
        )
    
    token = authorization.split("Bearer ")[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token in Authorization header"
        )
    
    try:
        # Validate JWT token with Supabase Auth
        user_res = supabase.auth.get_user(jwt=token)
        if not user_res or not user_res.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        email = user_res.user.email
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User email not found in token"
            )
        return email
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication check failed: " + str(e)
        )

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
