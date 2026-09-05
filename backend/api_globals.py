import os
import sys

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import re
import uuid
import json
import logging
import requests
import secrets
import threading
import time
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException, status, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
import tempfile
from datetime import datetime, timezone, timedelta
is_vercel = os.getenv("VERCEL") is not None or os.getenv("VERCEL_TMP_DIR") is not None
if is_vercel:
    log_file = os.path.join(tempfile.gettempdir(), "api.log")
else:
    log_file = "api.log"

try:
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
except Exception:
    pass
logger = logging.getLogger(__name__)

# Force IPv4 — IPv6 broken on Windows, causes hangs on Supabase/LLM calls
import socket
_orig_gai = socket.getaddrinfo
def _ipv4_only(*a, **kw):
    return [r for r in _orig_gai(*a, **kw) if r[0] == socket.AF_INET]
socket.getaddrinfo = _ipv4_only

try:
    from supabase import create_client, Client
except Exception as e:
    logger.warning(f"Supabase library import failed: {e}")
    create_client = None
    Client = None

import sys
load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Import Redis-backed rate limiter
try:
    from redis_rate_limiter import check_rate_limit, get_rate_limiter
    REDIS_RATE_LIMITER_AVAILABLE = True
except ImportError:
    REDIS_RATE_LIMITER_AVAILABLE = False
    print("Redis rate limiter not available, falling back to in-memory slowapi")


def _get_client_ip(request: Request) -> str:
    """Extract client IP, preferring X-Forwarded-For on Vercel."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _enforce_rate_limit(request: Request, scope: str, limit: int, window: int, id_parts: list[str]):
    """Check Redis rate limit; raise 429 if exceeded. No-op when Redis is unavailable."""
    if not REDIS_RATE_LIMITER_AVAILABLE:
        return
    ip = _get_client_ip(request)
    key = f"{scope}:{ip}:" + ":".join(p for p in id_parts if p and p != "unknown")
    allowed, info = check_rate_limit(key, limit, window)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {max(1, info.get('reset_at', 0) - int(time.time()))} seconds.",
        )


# Duplicate logger initialization removed

try:
    from trend_engine import TrendEngine
except Exception as e:
    logger.warning(f"TrendEngine import failed: {e}")
    TrendEngine = None

try:
    from trend_scoring import calculate_realistic_peaking_score
except Exception as e:
    logger.warning(f"trend_scoring import failed: {e}")
    calculate_realistic_peaking_score = None

try:
    from alert_system import AlertSystem
except Exception as e:
    logger.warning(f"AlertSystem import failed: {e}")
    AlertSystem = None

try:
    from reel_generator import ReelGenerator
except Exception as e:
    logger.warning(f"ReelGenerator import failed: {e}")
    ReelGenerator = None

try:
    from beat_detector import BeatDetector
except Exception as e:
    logger.warning(f"BeatDetector import failed: {e}")
    BeatDetector = None

try:
    from instagram_scraper_browser import InstagramScraper
except Exception as e:
    logger.warning(f"InstagramScraper import failed: {e}")
    InstagramScraper = None

try:
    from youtube_scraper import YouTubeScraper
except Exception as e:
    logger.warning(f"YouTubeScraper import failed: {e}")
    YouTubeScraper = None

try:
    from caption_engine import CaptionEngine
except Exception as e:
    logger.warning(f"CaptionEngine import failed: {e}")
    CaptionEngine = None

try:
    from trend_refresher import TrendRefresher
except Exception as e:
    logger.warning(f"TrendRefresher import failed: {e}")
    TrendRefresher = None

try:
    from creator_tools import CreatorTools
except Exception as e:
    logger.warning(f"CreatorTools import failed: {e}")
    CreatorTools = None

try:
    from auth import get_current_user, require_admin, require_super_admin, require_auth, hash_password, verify_password, create_access_token, verify_token, get_admin_user_by_email, check_and_update_login_attempts, record_failed_login_attempt, reset_login_attempts, log_admin_login_attempt
except Exception as e:
    logger.warning(f"Auth functions import failed: {e}")
    def get_current_user():
        return "guest@trendrop.app"
    def require_auth():
        raise HTTPException(status_code=503, detail="Auth system not configured")
    def require_admin():
        raise HTTPException(status_code=503, detail="Auth system not configured")
    def require_super_admin():
        raise HTTPException(status_code=503, detail="Auth system not configured")
    def get_admin_user():
        raise HTTPException(status_code=503, detail="Auth system not configured")
    def hash_password(password):
        return ""
    def verify_password(password, hashed):
        return False
    def create_access_token(data, expires_delta=None):
        return ""
    def verify_token(token):
        raise HTTPException(status_code=401, detail="Auth system not configured")
    def get_admin_user_by_email(email):
        return None
    def check_and_update_login_attempts(email):
        return True
    def record_failed_login_attempt(email):
        return False
    def reset_login_attempts(email):
        return False
    def log_admin_login_attempt(email, success, ip_address=None, user_agent=None):
        return False

try:
    from plan_enforcement import PlanEnforcement, require_feature, require_credits, log_endpoint_usage, require_phone_verified, CREDIT_COSTS
except Exception as e:
    logger.warning(f"Plan enforcement import failed: {e}")
    def PlanEnforcement():
        pass
    def require_feature(feature):
        return lambda: "guest@trendrop.app"
    def require_credits(cost):
        return lambda: "guest@trendrop.app"
    def log_endpoint_usage(feature):
        return lambda: "guest@trendrop.app"
    def require_phone_verified():
        return lambda: "guest@trendrop.app"
    CREDIT_COSTS = {
        "ai_generation": 0,
        "export": 0,
        "video_analysis": 0,
    }

try:
    from instagram_oauth import InstagramOAuth
except Exception as e:
    logger.warning(f"InstagramOAuth import failed: {e}")
    InstagramOAuth = None

try:
    from instagram_algorithm_insights import InstagramAlgorithmInsights
except Exception as e:
    logger.warning(f"InstagramAlgorithmInsights import failed: {e}")
    InstagramAlgorithmInsights = None

try:
    from event_monitor import EventMonitor
except Exception as e:
    logger.warning(f"EventMonitor import failed: {e}")
    EventMonitor = None

try:
    from hashtag_velocity_tracker import HashtagVelocityTracker
except Exception as e:
    logger.warning(f"HashtagVelocityTracker import failed: {e}")
    HashtagVelocityTracker = None

try:
    from creator_analytics import CreatorAnalyticsEngine
except Exception as e:
    logger.warning(f"CreatorAnalyticsEngine import failed: {e}")
    CreatorAnalyticsEngine = None

try:
    from content_generator import AIContentGenerator as ContentGenerator
except Exception as e:
    logger.warning(f"ContentGenerator import failed: {e}")
    ContentGenerator = None

try:
    from content_generator import AIContentGenerator
except Exception as e:
    logger.warning(f"AIContentGenerator import failed: {e}")
    AIContentGenerator = None

try:
    from device_fingerprint import DeviceFingerprint
except Exception as e:
    logger.warning(f"DeviceFingerprint import failed: {e}")
    DeviceFingerprint = None

try:
    from phone_verification import PhoneVerification
except Exception as e:
    logger.warning(f"PhoneVerification import failed: {e}")
    PhoneVerification = None

try:
    from usage_tracker import UsageTracker
except Exception as e:
    logger.warning(f"UsageTracker import failed: {e}")
    UsageTracker = None

try:
    from user_management import UserManager
except Exception as e:
    logger.warning(f"UserManager import failed: {e}")
    UserManager = None

try:
    from early_trend_detection import EarlyTrendDetector
except Exception as e:
    logger.warning(f"EarlyTrendDetector import failed: {e}")
    EarlyTrendDetector = None

try:
    from virality_prediction import ViralityPredictor
except Exception as e:
    logger.warning(f"ViralityPredictor import failed: {e}")
    ViralityPredictor = None

try:
    from cultural_event_calendar import CulturalEventCalendar
except Exception as e:
    logger.warning(f"CulturalEventCalendar import failed: {e}")
    CulturalEventCalendar = None

try:
    from video_metadata_analyzer import VideoMetadataAnalyzer
except Exception as e:
    logger.warning(f"VideoMetadataAnalyzer import failed: {e}")
    VideoMetadataAnalyzer = None

try:
    from video_visual_analyzer import VideoVisualAnalyzer
except Exception as e:
    logger.warning(f"VideoVisualAnalyzer import failed: {e}")
    VideoVisualAnalyzer = None

try:
    from video_virality_scorer import VideoViralityScorer
except Exception as e:
    logger.warning(f"VideoViralityScorer import failed: {e}")
    VideoViralityScorer = None

try:
    from user_performance_tracker import UserPerformanceTracker
except Exception as e:
    logger.warning(f"UserPerformanceTracker import failed: {e}")
    UserPerformanceTracker = None

try:
    from business_metrics import BusinessMetrics
except Exception as e:
    logger.warning(f"BusinessMetrics import failed: {e}")
    BusinessMetrics = None

try:
    from revenue_tracker import RevenueTracker
except Exception as e:
    logger.warning(f"RevenueTracker import failed: {e}")
    RevenueTracker = None

try:
    from case_study_templates import get_sample_case_studies
except Exception as e:
    logger.warning(f"Case study templates import failed: {e}")
    get_sample_case_studies = None

try:
    from pitch_deck_structure import generate_pitch_deck_content, export_pitch_deck_to_markmark
except Exception as e:
    logger.warning(f"Pitch deck structure import failed: {e}")
    generate_pitch_deck_content = None
    export_pitch_deck_to_markmark = None

try:
    from phone_verification import PhoneVerification
except Exception as e:
    logger.warning(f"PhoneVerification import failed: {e}")
    PhoneVerification = None

load_dotenv()
if not os.getenv("SUPABASE_URL"):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_env = os.path.join(script_dir, ".env")
    if os.path.exists(backend_env):
        load_dotenv(backend_env)

required_env_vars = [
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "YOUTUBE_API_KEY",
    "RESEND_API_KEY",
    "SUPABASE_DB_URL"
]
missing_env_vars = [var for var in required_env_vars if not os.getenv(var)]
if not any(
    os.getenv(name).strip()
    for name in os.environ
    if name.startswith("GROQ_API_KEY") or name.startswith("GEMINI_API_KEY") or name.startswith("LLM_API_KEY")
):
    missing_env_vars.append("LLM_API_KEYS")
if missing_env_vars:
        logger.warning(f"Startup warning: Missing optional environment variables: {', '.join(missing_env_vars)}")

# Validate SUPABASE_SERVICE_ROLE_KEY (non-blocking with timeout)
supabase_url_debug = os.getenv("SUPABASE_URL")
service_key_debug = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if supabase_url_debug and service_key_debug and create_client:
    import concurrent.futures
    def _validate_svc_key():
        create_client(supabase_url_debug, service_key_debug).table("trends").select("id").limit(1).execute()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(_validate_svc_key).result(timeout=5)
        logger.info("SUPABASE_SERVICE_ROLE_KEY is valid.")
    except concurrent.futures.TimeoutError:
        logger.warning("SUPABASE_SERVICE_ROLE_KEY validation timed out, keeping key anyway")
    except Exception as e:
        logger.warning(f"SUPABASE_SERVICE_ROLE_KEY is invalid ({e}), deleting it from environment to fallback to SUPABASE_KEY (anon)")
        if "SUPABASE_SERVICE_ROLE_KEY" in os.environ:
            del os.environ["SUPABASE_SERVICE_ROLE_KEY"]

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    logger.error(f"Failed to create Supabase client: {e}")
    supabase = None

creator_tools = CreatorTools() if CreatorTools is not None else None
MOCK_JOBS = {}

import time
_USER_PROFILE_CACHE = {}
_USER_PROFILE_TTL = 300 # 5 minutes

def get_cached_user_profile(email: str) -> dict:
    now = time.time()
    if email in _USER_PROFILE_CACHE:
        entry = _USER_PROFILE_CACHE[email]
        if now - entry['time'] < _USER_PROFILE_TTL:
            return entry['data']
    
    # Cache miss
    try:
        if supabase:
            res = supabase.table("users").select("niche, language_preference, user_id, plan").eq("email", email).limit(1).execute()
            data = res.data[0] if res.data else {}
            _USER_PROFILE_CACHE[email] = {'time': now, 'data': data}
            return data
    except Exception as e:
        logger.warning(f"Error querying user profile for cache: {e}")
    return {}

def invalidate_cached_user_profile(email: str):
    if email in _USER_PROFILE_CACHE:
        del _USER_PROFILE_CACHE[email]
    
    # Also invalidate the plan gate cache
    from plan_enforcement import invalidate_plan_cache
    invalidate_plan_cache(email)

def _resolve_user(authorization: Optional[str]) -> Optional[str]:
    """
    Returns a stable user identifier string given an Authorization header.

    Priority:
      1. Supabase JWT  -> returns Supabase user UUID
      2. Custom auth_token from our `users` table -> returns the user email
      3. None if neither matches
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split("Bearer ", 1)[1].strip()
    if not token:
        return None

    # --- Try Supabase JWT first ---
    if supabase:
        try:
            local_supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            user_res = local_supabase.auth.get_user(jwt=token)
            if user_res and user_res.user:
                return str(user_res.user.id)
        except Exception:
            pass

        # --- Fall back to custom auth_token in users table ---
        try:
            res = supabase.table("users").select("email").eq("auth_token", token).limit(1).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]["email"]
        except Exception:
            pass

    return None


import tempfile
base_dir = os.getenv("VERCEL_TMP_DIR", tempfile.gettempdir())
uploads_path = os.path.join(base_dir, "uploads")
outputs_path = os.path.join(base_dir, "outputs")
os.makedirs(uploads_path, exist_ok=True)
os.makedirs(outputs_path, exist_ok=True)

# Rate limiter — slowapi always enabled; Redis limiter available for future middleware use
limiter = Limiter(key_func=get_remote_address, enabled=os.getenv("DISABLE_RATE_LIMITER", "0") != "1")
redis_limiter = get_rate_limiter() if REDIS_RATE_LIMITER_AVAILABLE else None

from fastapi.middleware.gzip import GZipMiddleware
try:
    import sentry_sdk
    sentry_sdk.init(
        dsn="https://68bd847016cb673a5a3c45a3bb093531@o4511918964277248.ingest.de.sentry.io/4511918972469328",
        send_default_pii=False,
        traces_sample_rate=0.1,
        environment=os.getenv("ENVIRONMENT", "development")
    )
except ImportError:
    print("Warning: sentry_sdk not installed. Sentry reporting disabled.")

# redis/queue/cache setup
standard_queue = None
priority_queue = None
_PEAKED_TRENDS_CACHE = {}

try:
    import redis
    from rq import Queue
    UPSTASH_REDIS_URL = os.getenv("UPSTASH_REDIS_URL")
    if UPSTASH_REDIS_URL:
        redis_conn = redis.from_url(UPSTASH_REDIS_URL)
        standard_queue = Queue("standard", connection=redis_conn)
        priority_queue = Queue("priority", connection=redis_conn)
except Exception as e:
    logger.warning(f"Redis/RQ integration in api_globals disabled: {e}")

app = FastAPI(
    title="Trendrop Backend API",
    description="AI-powered trend intelligence for Indian short-form creators",
    version="2.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)



# ── Trends Feed ────────────────────────────────────────────────────────────────

# Normalize content_type variants → canonical keys so the frontend filter works
CONTENT_TYPE_NORMALIZE = {
    "narrative_edit": "narrative_edit",
    "text_overlay":   "text_overlay",
    "regional":       "regional",
    "motivation":     "motivation",
    "fitness":        "fitness",
    "study":          "study",
    "news/political": "current_affairs",
    "romance/relationship": "romance_relationship",
}

def _normalize_trends(trends: list) -> list:
    """Normalize content_type and inject song/artist aliases on each trend row."""
    if not trends:
        return trends

    from audio_title_normalize import normalize_audio_title

    # Batch query reels for all trend artists in a single DB round-trip
    artists = list(set(t.get("audio_artist") for t in trends if t.get("audio_artist")))
    reels_lookup = {}
    if artists and supabase:
        try:
            res_reels = supabase.table("reels") \
                .select("reel_id, views_delta_last_run, audio_title, audio_artist, velocity_score") \
                .in_("audio_artist", artists) \
                .execute()
            
            for r in (res_reels.data or []):
                norm_title = normalize_audio_title(r.get("audio_title", "") or "")
                key = (norm_title, r.get("audio_artist"))
                velocity = float(r.get("velocity_score") or 0.0)
                existing = reels_lookup.get(key)
                if not existing or velocity > float(existing.get("velocity_score") or 0.0):
                    reels_lookup[key] = r
        except Exception as e:
            logger.warning(f"Failed to pre-fetch reels info: {e}")

    for t in trends:
        t["song"]   = t.get("audio_title")
        t["artist"] = t.get("audio_artist")
        ct = (t.get("content_type") or "").lower().strip().replace(" ", "_")
        t["content_type"] = CONTENT_TYPE_NORMALIZE.get(ct, ct)
        
        # Inject matching reel details from lookup using normalized title
        norm_title = normalize_audio_title(t.get("audio_title", "") or "")
        key = (norm_title, t.get("audio_artist"))
        match = reels_lookup.get(key)
        if match:
            t["reel_id"] = match.get("reel_id")
            t["views_delta_last_run"] = match.get("views_delta_last_run") or 0
            
    return trends


def _trend_priority_key(trend: dict, user_niche: str = "all", user_lang: str = "all") -> tuple[float, int, int, float, float]:
    origin = (trend.get("trend_origin") or "").upper()
    is_cross = bool(trend.get("is_cross_cultural"))
    global_first = 1 if is_cross or origin not in {"", "IN", "UNKNOWN"} else 0
    regional = 0 if origin in {"", "IN", "UNKNOWN"} else 1
    if is_cross:
        regional = 0

    # 1. Personalization Boost
    niche_boost = 0.0
    trend_niche = (trend.get("niche_tag") or "general").lower()
    if user_niche != "all" and user_niche.lower() in [trend_niche, (trend.get("content_type") or "").lower()]:
        niche_boost = 50.0  # Heavy boost for niche matching
        
    lang_boost = 0.0
    trend_lang = (trend.get("language") or "").lower()
    if user_lang != "all" and user_lang.lower() == trend_lang:
        lang_boost = 20.0  # Boost for language match

    # 2. Saturation Penalty (Game Theory Downranking)
    # Penalize if multiple creators are actively targeting this trend
    sat_count = trend.get("saturation_count") or 0
    saturation_penalty = sat_count * 15.0

    base_score = float(trend.get("composite_score") or trend.get("velocity_avg") or 0.0)
    personalized_score = base_score + niche_boost + lang_boost - saturation_penalty

    return (
        personalized_score,
        global_first,
        regional,
        base_score,
        float(trend.get("reel_count") or 0),
    )

# --- Subscription Tiers Cache ---
TIERS_CACHE = {}
TIERS_CACHE_LAST_FETCH = None

def get_cached_tiers():
    global TIERS_CACHE_LAST_FETCH, TIERS_CACHE
    now = datetime.now(timezone.utc)
    if not TIERS_CACHE or not TIERS_CACHE_LAST_FETCH or (now - TIERS_CACHE_LAST_FETCH).total_seconds() > 300:
        if supabase:
            try:
                res = supabase.table("subscription_tiers").select("*").execute()
                if res.data:
                    TIERS_CACHE = {row["name"]: row for row in res.data}
                    TIERS_CACHE_LAST_FETCH = now
            except Exception as e:
                logger.error(f"Error fetching subscription tiers for cache: {e}")
    return TIERS_CACHE

def get_cached_tier_delay(plan_name: str) -> int:
    tiers = get_cached_tiers()
    tier = tiers.get(plan_name)
    if tier:
        return tier.get("data_delay_hours", 6)
    return 6

