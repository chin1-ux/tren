import os
import logging
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from fastapi import Header, HTTPException, status, Depends, Request
from supabase import create_client, Client
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables early to ensure they are available for authentication
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 30

if not JWT_SECRET_KEY:
    raise ValueError(
        "JWT_SECRET_KEY must be set in environment variables. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )

# Handle missing Supabase credentials gracefully for CI/testing
if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning("SUPABASE_URL and SUPABASE_KEY not set - auth system will be disabled")
    supabase = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def _check_user_locked(email: str) -> None:
    """Raise 403 immediately if the user's status is 'locked'."""
    try:
        res = supabase.table("users").select("status").eq("email", email).limit(1).execute()
        if res.data and res.data[0].get("status") == "locked":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is locked. Contact support."
            )
    except HTTPException:
        raise
    except Exception:
        pass  # If we can't check, don't block — but log it

def get_current_user(authorization: str = Header(None)) -> str:
    """
    Validate the Supabase JWT or custom auth_token in the Authorization header.
    Returns the user's email if valid. Falls back to guest@trendrop.app if invalid or missing.
    Raises 403 if the resolved account has status == 'locked'.
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
        res = supabase.table("users").select("email, status").eq("auth_token", token).limit(1).execute()
        if res.data and len(res.data) > 0:
            row = res.data[0]
            if row.get("status") == "locked":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account is locked. Contact support."
                )
            return row["email"]
    except HTTPException:
        raise
    except Exception:
        pass

    # 2. Validate token using Supabase Auth JWT validator
    try:
        user_res = supabase.auth.get_user(jwt=token)
        if user_res and user_res.user:
            email = user_res.user.email
            if email:
                _check_user_locked(email)
                return email
    except HTTPException:
        raise
    except Exception:
        pass

    # 3. Try custom JWT verification (for admin tokens)
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if "sub" in payload:
            _check_user_locked(payload["sub"])
            return payload["sub"]
    except HTTPException:
        raise
    except Exception:
        pass

    return "guest@trendrop.app"


def require_auth(current_user: str = Depends(get_current_user)) -> str:
    """Reject unauthenticated (guest) requests with 401."""
    if current_user == "guest@trendrop.app":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return current_user


def hash_password(password: str) -> str:
    """Generate bcrypt hash for password."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Dict:
    """Verify JWT token and return payload."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

def get_admin_user_by_email(email: str) -> Optional[Dict]:
    """Get admin user from admin_users table by email."""
    if not supabase:
        logger.warning("Supabase client not available in get_admin_user_by_email")
        return None
    try:
        logger.info(f"Fetching admin user for email: {email}")
        res = supabase.table("admin_users").select("*").eq("email", email).single().execute()
        if res.data:
            logger.info(f"Admin user found: {email}")
        else:
            logger.warning(f"Admin user not found: {email}")
        return res.data if res.data else None
    except Exception as e:
        logger.error(f"Error getting admin user: {e}")
        return None

def check_and_update_login_attempts(email: str) -> bool:
    """Check if account is locked and update login attempts. Returns True if allowed."""
    if not supabase:
        return True
    
    try:
        admin_user = get_admin_user_by_email(email)
        if not admin_user:
            return False
        
        # Check if account is locked
        locked_until = admin_user.get("locked_until")
        if locked_until:
            locked_time = datetime.fromisoformat(locked_until.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) < locked_time:
                return False  # Account is still locked
        
        # Reset failed attempts if lockout period has passed
        if locked_until and datetime.now(timezone.utc) >= locked_time:
            supabase.table("admin_users").update({
                "failed_login_attempts": 0,
                "locked_until": None
            }).eq("email", email).execute()
        
        return True
    except Exception as e:
        logger.error(f"Error checking login attempts: {e}")
        return False

def record_failed_login_attempt(email: str) -> bool:
    """Record a failed login attempt and lock account if threshold reached."""
    if not supabase:
        return False
    
    try:
        admin_user = get_admin_user_by_email(email)
        if not admin_user:
            return False
        
        failed_attempts = admin_user.get("failed_login_attempts", 0) + 1
        update_data = {"failed_login_attempts": failed_attempts}
        
        # Lock account after 5 failed attempts for 15 minutes
        if failed_attempts >= 5:
            locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            update_data["locked_until"] = locked_until.isoformat()
        
        supabase.table("admin_users").update(update_data).eq("email", email).execute()
        return True
    except Exception as e:
        logger.error(f"Error recording failed login: {e}")
        return False

def reset_login_attempts(email: str) -> bool:
    """Reset failed login attempts after successful login."""
    if not supabase:
        return False
    
    try:
        supabase.table("admin_users").update({
            "failed_login_attempts": 0,
            "locked_until": None,
            "last_login": datetime.now(timezone.utc).isoformat()
        }).eq("email", email).execute()
        return True
    except Exception as e:
        logger.error(f"Error resetting login attempts: {e}")
        return False

def log_admin_login_attempt(email: str, success: bool, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> bool:
    """Log admin login attempt to admin_audit_log_enhanced."""
    if not supabase:
        return False
    
    try:
        supabase.table("admin_audit_log_enhanced").insert({
            "admin_email": email,
            "action": "login_attempt",
            "details": {"success": success},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }).execute()
        return True
    except Exception as e:
        logger.error(f"Error logging admin login attempt: {e}")
        return False

def require_admin(request: Request) -> Dict:
    """
    FastAPI dependency that validates JWT token and admin role.
    Decodes JWT from Authorization header, verifies role in ('admin','super_admin'),
    raises 401/403 otherwise, returns the admin's email + role.
    """
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.split("Bearer ")[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token"
        )
    
    # Verify token
    payload = verify_token(token)
    email = payload.get("sub")
    role = payload.get("role")
    
    if not email or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    if role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return {"email": email, "role": role}

def require_super_admin(request: Request) -> Dict:
    """
    FastAPI dependency that validates JWT token and super_admin role.
    Requires role == 'super_admin', raises 403 otherwise.
    """
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.split("Bearer ")[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token"
        )
    
    # Verify token
    payload = verify_token(token)
    email = payload.get("sub")
    role = payload.get("role")
    
    if not email or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    if role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    
    return {"email": email, "role": role}

