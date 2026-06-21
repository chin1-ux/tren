import os
import uuid
import json
import logging
import requests
import secrets
import threading
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException, status, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
import logging
logging.basicConfig(
    filename="api.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    from supabase import create_client, Client
except Exception as e:
    logger.warning(f"Supabase library import failed: {e}")
    create_client = None
    Client = None

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import sys
load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Duplicate logger initialization removed

try:
    from trend_engine import TrendEngine
except Exception as e:
    logger.warning(f"TrendEngine import failed: {e}")
    TrendEngine = None

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
    from instagram_scraper import InstagramScraper
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
    from auth import get_current_user, get_admin_user
except Exception as e:
    logger.warning(f"Auth functions import failed: {e}")
    def get_current_user():
        raise HTTPException(status_code=401, detail="Authentication not configured")
    def get_admin_user():
        raise HTTPException(status_code=401, detail="Admin authentication not configured")

load_dotenv()
if not os.getenv("SUPABASE_URL"):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_env = os.path.join(script_dir, ".env")
    if os.path.exists(backend_env):
        load_dotenv(backend_env)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning("SUPABASE_URL or SUPABASE_KEY missing; Supabase client will be unavailable.")
    supabase = None
else:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        supabase = None
creator_tools = CreatorTools()

os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Trendrop Backend API",
    description="AI-powered trend intelligence for Indian short-form creators",
    version="2.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Secure CORS config whitelisting Vercel, Railway, and Localhost
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.railway\.app|https://.*\.vercel\.app|http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def start_cron_thread():
    try:
        import schedule
        import time
        from cron_job import run_full_pipeline
        
        logger.info("Starting background scraper cron thread...")
        # Wait 60 seconds after startup to let Render complete the health check deployment
        time.sleep(60)
        
        logger.info("Running initial background scraper pipeline...")
        run_full_pipeline()
        
        # Schedule to run every 3 hours
        schedule.every(3).hours.do(run_full_pipeline)
        while True:
            schedule.run_pending()
            time.sleep(60)
    except Exception as e:
        logger.error(f"Error in background scraper cron thread: {e}", exc_info=True)

@app.on_event("startup")
def startup_event():
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)
    logger.info("Trendrop API v2.0 started.")
    threading.Thread(target=start_cron_thread, daemon=True).start()

app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")


# ── Pydantic Models ────────────────────────────────────────────────────────────

class SubscribeRequest(BaseModel):
    email: EmailStr
    niche: str
    language: str

class FeedbackRequest(BaseModel):
    trend_id: int
    feedback_type: str  # "too_late" | "too_early" | "perfect" | "stale"
    comment: Optional[str] = None
    user_email: Optional[str] = None


class PrePostRequest(BaseModel):
    niche: str
    hook: str
    audio_title: str
    caption: str
    hashtags: List[str]
    post_time: str
    user_email: Optional[str] = None


class HookRequest(BaseModel):
    niche: str
    topic: str


class SeoCaptionRequest(BaseModel):
    description: str
    platform: Optional[str] = "instagram"


class CalendarRequest(BaseModel):
    user_email: Optional[str] = None
    niche: str
    language: str
    frequency: str


class CreatorProfileRequest(BaseModel):
    user_email: Optional[str] = None
    instagram_username: str
    niche: str
    followers: int
    engagement_rate: float
    trend_score: float
    portfolio_links: List[str]
    price_per_post: int


class BrandDealRequest(BaseModel):
    creator_email: Optional[str] = None
    brand_name: str
    deal_amount: int
    details: str


class MemoryRequest(BaseModel):
    trend_id: int
    format_name: str
    hook_variant: str
    planned_mode: str
    outcome_score: Optional[float] = None
    notes: Optional[str] = None


class TrialPlanRequest(BaseModel):
    creator_niche: Optional[str] = None
    creator_language: Optional[str] = None



# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "2.0", "product": "Trendrop India"}



# ── Trends Feed ────────────────────────────────────────────────────────────────

@app.get("/api/trends")
@limiter.limit("100/minute")
def get_trends(request: Request, language: Optional[str] = None, sort: Optional[str] = "velocity"):
    """
    Fetch RISING trends from Supabase.
    Optional filters: ?language=hi&sort=velocity|time_left|newest
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    try:
        q = supabase.table("trends").select("*").eq("status", "rising")
        if language and language != "all":
            q = q.eq("language", language)

        if sort == "time_left":
            q = q.order("window_hours_remaining", desc=False)
        elif sort == "newest":
            q = q.order("created_at", desc=True)
        else:
            q = q.order("velocity_avg", desc=True)

        res = q.execute()
        trends = res.data or []
        for t in trends:
            t["song"] = t.get("audio_title")
            t["artist"] = t.get("audio_artist")
        return trends
    except Exception as e:
        logger.error(f"Error fetching trends: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trends/emerging")
@limiter.limit("100/minute")
def get_emerging_trends(request: Request, language: Optional[str] = None):
    """
    Fetch EMERGING trends — the early access feed (pre-viral, 0–6h window).
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    try:
        q = supabase.table("trends").select("*").eq("status", "emerging")
        if language and language != "all":
            q = q.eq("language", language)
        q = q.order("velocity_avg", desc=True)
        res = q.execute()
        trends = res.data or []
        for t in trends:
            t["song"] = t.get("audio_title")
            t["artist"] = t.get("audio_artist")
        return trends
    except Exception as e:
        logger.error(f"Error fetching emerging trends: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trends/all-active")
@limiter.limit("60/minute")
def get_all_active_trends(request: Request):
    """Returns both emerging + rising trends merged."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    try:
        res = supabase.table("trends").select("*").in_("status", ["emerging", "rising"]).order("velocity_avg", desc=True).execute()
        trends = res.data or []
        for t in trends:
            t["song"] = t.get("audio_title")
            t["artist"] = t.get("audio_artist")
        return trends
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trends/by-language/{lang}")
@limiter.limit("100/minute")
def get_trends_by_language(request: Request, lang: str):
    """Returns trends filtered by specific language code (hi, kn, ta, te, en, ...)."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    try:
        res = supabase.table("trends") \
            .select("*") \
            .in_("status", ["emerging", "rising"]) \
            .eq("language", lang) \
            .order("velocity_avg", desc=True) \
            .execute()
        trends = res.data or []
        for t in trends:
            t["song"] = t.get("audio_title")
            t["artist"] = t.get("audio_artist")
        return trends
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trends/{trend_id}")
@limiter.limit("100/minute")
def get_trend(request: Request, trend_id: int):
    """Fetch single trend by ID."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    try:
        res = supabase.table("trends").select("*").eq("id", trend_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail=f"Trend {trend_id} not found")
        trend = res.data[0]
        trend["song"] = trend.get("audio_title")
        trend["artist"] = trend.get("audio_artist")
        return trend
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trends/{trend_id}/reels")
@limiter.limit("60/minute")
def get_trend_reels(request: Request, trend_id: int):
    """Fetch reels linked to a trend (by matching audio_title + audio_artist)."""
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not configured.")
    try:
        trend_res = supabase.table("trends") \
            .select("audio_title, audio_artist") \
            .eq("id", trend_id) \
            .execute()
        if not trend_res.data:
            raise HTTPException(status_code=404, detail=f"Trend {trend_id} not found")
        t = trend_res.data[0]
        title, artist = t.get("audio_title"), t.get("audio_artist")
        reels_res = supabase.table("reels") \
            .select("*") \
            .eq("audio_title", title) \
            .eq("audio_artist", artist) \
            .order("velocity_score", desc=True) \
            .limit(20) \
            .execute()
        return reels_res.data or []
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trends/{trend_id}/caption")
@limiter.limit("30/minute")
def get_trend_caption(request: Request, trend_id: int):
    """
    Returns AI-generated caption kit for a trend.
    Includes: 3 caption variants, 15 hashtags, audio cue, posting strategy.
    Results are cached in trend_captions table.
    """
    try:
        engine = CaptionEngine()
        kit = engine.get_caption_kit(trend_id)
        return kit
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Caption generation failed for trend {trend_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trends/{trend_id}/similar")
@limiter.limit("60/minute")
def get_similar_trends(request: Request, trend_id: int):
    """Returns past trends with the same content_type and language (peaked or expired, showing history)."""
    try:
        trend_res = supabase.table("trends") \
            .select("content_type, language") \
            .eq("id", trend_id) \
            .execute()
        if not trend_res.data:
            raise HTTPException(status_code=404, detail=f"Trend {trend_id} not found")
        t = trend_res.data[0]
        content_type = t.get("content_type")
        language = t.get("language")
        q = supabase.table("trends").select("*").neq("id", trend_id)
        if content_type:
            q = q.eq("content_type", content_type)
        if language:
            q = q.eq("language", language)
        q = q.order("velocity_avg", desc=True).limit(5)
        res = q.execute()
        similar = res.data or []
        for s in similar:
            s["song"] = s.get("audio_title")
            s["artist"] = s.get("audio_artist")
        return similar
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trends/{trend_id}/decision")
@limiter.limit("60/minute")
def get_trend_decision(request: Request, trend_id: int, creator_niche: Optional[str] = None, creator_language: Optional[str] = None):
    """
    Returns a simple creator decision layer for the trend:
    post it, trial it, or skip it.
    """
    try:
        res = supabase.table("trends").select("*").eq("id", trend_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail=f"Trend {trend_id} not found")
        t = res.data[0]

        fit = float(t.get("creator_fit_score") or 0)
        hook = float(t.get("hook_retention_score") or 0)
        crowd = 1.0 - float(t.get("saturation_penalty") or 0)
        composite = float(t.get("composite_score") or 0)
        confidence = float(t.get("confidence") or 0)

        score = (fit * 0.35) + (hook * 0.25) + (crowd * 0.2) + (min(1.0, confidence) * 0.2)
        if creator_niche and creator_niche.lower() in (t.get("content_type") or "").lower():
            score += 0.05
        if creator_language and creator_language.lower() == (t.get("language") or "").lower():
            score += 0.05

        if score >= 0.72 and composite >= 3.0:
            decision = "post"
        elif score >= 0.55:
            decision = "trial"
        else:
            decision = "skip"

        test_hook = t.get("text_overlay_template") or f"POV: you just found {t.get('audio_title')}"
        public_hook = f"Would you use this sound for {t.get('content_type') or 'your niche'}?"

        rationale = (
            f"Fit {int(fit * 100)}%, hook {int(hook * 100)}%, crowd {int(crowd * 100)}%, "
            f"confidence {int(confidence * 100)}%."
        )

        return {
            "decision": decision,
            "score": round(score, 3),
            "rationale": rationale,
            "test_hook": test_hook,
            "public_hook": public_hook,
            "trend": {
                "creator_fit_score": fit,
                "hook_retention_score": hook,
                "saturation_penalty": float(t.get("saturation_penalty") or 0),
                "composite_score": composite,
                "confidence": confidence,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/trends/{trend_id}/memory")
@limiter.limit("30/minute")
def save_trend_memory(request: Request, trend_id: int, req: MemoryRequest, current_user_email: str = Depends(get_current_user)):
    try:
        memory = {
            "user_email": current_user_email,
            "trend_id": trend_id,
            "format_name": req.format_name,
            "hook_variant": req.hook_variant,
            "planned_mode": req.planned_mode,
            "outcome_score": req.outcome_score,
            "notes": req.notes,
        }
        supabase.table("creator_trend_memory").insert(memory).execute()
        return {"success": True}
    except Exception as e:
        logger.error(f"Error saving trend memory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


# ── User / Subscribe ───────────────────────────────────────────────────────────

@app.post("/api/subscribe")
@limiter.limit("10/minute")
def subscribe(request: Request, req: SubscribeRequest):
    """Save user subscription to Supabase users table and return auth_token."""
    try:
        # Check if user already exists
        res = supabase.table("users").select("auth_token").eq("email", req.email).execute()
        token = None
        if res.data and len(res.data) > 0:
            token = res.data[0].get("auth_token")
        
        if not token:
            token = secrets.token_hex(16)

        user_data = {
            "email": req.email,
            "niche": req.niche,
            "language_preference": req.language,
            "auth_token": token
        }
        supabase.table("users").upsert(user_data, on_conflict="email").execute()
        return {"success": True, "message": "You are subscribed!", "auth_token": token, "email": req.email}
    except Exception as e:
        logger.error(f"Subscribe failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


# ── Feedback ───────────────────────────────────────────────────────────────────

@app.post("/api/feedback")
@limiter.limit("20/minute")
def submit_feedback(request: Request, req: FeedbackRequest, current_user_email: str = Depends(get_current_user)):
    """
    Creator feedback on a trend: too_late | too_early | perfect | stale.
    Stored in trend_feedback table for future ML training signal.
    """
    try:
        feedback_data = {
            "trend_id": req.trend_id,
            "feedback_type": req.feedback_type,
            "comment": req.comment,
            "user_email": current_user_email,
        }
        supabase.table("trend_feedback").insert(feedback_data).execute()
        return {"success": True, "message": "Feedback received. Thank you!"}
    except Exception as e:
        logger.error(f"Feedback save failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


# ── Reel Generation ────────────────────────────────────────────────────────────

def run_reel_generation(job_id: str, file_paths: List[str], trend_id: str):
    logger.info(f"Background reel generation started: job={job_id}")
    try:
        supabase.table("jobs").update({"status": "processing", "progress": 0}).eq("id", int(job_id)).execute()
        trend_res = supabase.table("trends").select("*").eq("id", int(trend_id)).execute()
        if not trend_res.data:
            raise ValueError(f"Trend {trend_id} not found")
        trend_data = trend_res.data[0]

        audio_path = None
        audio_url = trend_data.get("audio_url")
        if audio_url:
            try:
                upload_dir = f"uploads/{job_id}"
                os.makedirs(upload_dir, exist_ok=True)
                audio_path = os.path.join(upload_dir, "audio.mp3")
                resp = requests.get(audio_url, timeout=30)
                resp.raise_for_status()
                with open(audio_path, "wb") as f:
                    f.write(resp.content)
            except Exception as e:
                logger.warning(f"Audio download failed: {e}. Continuing without audio.")
                audio_path = None

        generator = ReelGenerator()

        def progress_cb(pct: int):
            supabase.table("jobs").update({"progress": pct}).eq("id", int(job_id)).execute()

        output_path = os.path.join("outputs", f"{job_id}.mp4")
        generator.generate_reel(
            image_paths=file_paths,
            audio_path=audio_path,
            output_path=output_path,
            progress_callback=progress_cb
        )

        output_url = f"/outputs/{job_id}.mp4"
        supabase.table("jobs").update({
            "status": "complete",
            "progress": 100,
            "output_url": output_url
        }).eq("id", int(job_id)).execute()
        logger.info(f"Job {job_id} complete.")

    except Exception as err:
        logger.error(f"Reel generation error (job={job_id}): {err}", exc_info=True)
        try:
            supabase.table("jobs").update({
                "status": "failed",
                "error_message": str(err)
            }).eq("id", int(job_id)).execute()
        except Exception:
            pass


def run_scrapers_background():
    logger.info("Background scraper started.")
    try:
        try:
            insta = InstagramScraper()
            insta.scrape_trending_reels()
        except Exception as e:
            logger.error(f"Instagram scraper background error: {e}", exc_info=True)
        try:
            yt = YouTubeScraper()
            yt.scrape_trending_shorts()
        except Exception as e:
            logger.error(f"YouTube scraper background error: {e}", exc_info=True)
        new_ids = []
        try:
            te = TrendEngine()
            new_ids = te.detect_trends()
        except Exception as e:
            logger.error(f"TrendEngine background error: {e}", exc_info=True)
        try:
            refresher = TrendRefresher()
            refresher.refresh_all()
        except Exception as e:
            logger.error(f"TrendRefresher background error: {e}", exc_info=True)
        if new_ids:
            try:
                alert = AlertSystem()
                alert.send_trend_alerts(new_ids)
            except Exception as e:
                logger.error(f"AlertSystem background error: {e}", exc_info=True)
        logger.info("Background scraper complete.")
    except Exception as e:
        logger.error(f"Critical background scraper error: {e}", exc_info=True)


@app.post("/api/generate-reel")
@limiter.limit("10/minute")
async def generate_reel_endpoint(
    request: Request,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    trend_id: str = Form(...),
    user_email: str = Form(...)
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    try:
        job_data = {
            "job_type": "reel_generation",
            "status": "pending",
            "user_email": user_email,
            "progress": 0,
            "input_data": json.dumps({"files_count": len(files), "trend_id": trend_id})
        }
        res = supabase.table("jobs").insert(job_data).execute()
        if not res.data:
            raise ValueError("Failed to create job record")
        job_id = str(res.data[0]["id"])

        job_dir = f"uploads/{job_id}"
        os.makedirs(job_dir, exist_ok=True)
        file_paths = []
        for file in files:
            filename = os.path.basename(file.filename)
            fpath = os.path.join(job_dir, filename)
            with open(fpath, "wb") as f:
                content = await file.read()
                f.write(content)
            file_paths.append(fpath)

        background_tasks.add_task(run_reel_generation, job_id, file_paths, trend_id)
        return {"job_id": job_id}
    except Exception as e:
        logger.error(f"generate-reel error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reel-status/{job_id}")
@limiter.limit("60/minute")
def get_reel_status(request: Request, job_id: int):
    try:
        res = supabase.table("jobs").select("*").eq("id", job_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        job = res.data[0]
        return {
            "status": job.get("status"),
            "progress": job.get("progress"),
            "output_url": job.get("output_url"),
            "error_message": job.get("error_message")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/run-scraper")
@limiter.limit("2/minute")
def trigger_scraper(request: Request, background_tasks: BackgroundTasks, is_admin: bool = Depends(get_admin_user)):
    """Manually trigger the full scraper + trend detection pipeline. Protected by Admin API Key."""
    try:
        background_tasks.add_task(run_scrapers_background)
        return {"message": "Pipeline started in background"}
    except Exception as e:
        logger.error(f"Scraper trigger failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


# ── Creator Tools & Features ──────────────────────────────────────────────────

@app.post("/api/prepost-score")
@limiter.limit("5/minute")
def get_prepost_score(request: Request, req: PrePostRequest, current_user_email: str = Depends(get_current_user)):
    try:
        res = creator_tools.get_pre_post_score(
            niche=req.niche,
            hook=req.hook,
            audio_title=req.audio_title,
            caption=req.caption,
            hashtags=req.hashtags,
            post_time=req.post_time
        )
        # Save to DB
        analysis_data = {
            "user_email": current_user_email,
            "video_url": "",
            "analysis_details": res,
            "score": res.get("overall_score", 0)
        }
        supabase.table("pre_post_analyses").insert(analysis_data).execute()
        return res
    except Exception as e:
        logger.error(f"Error in /api/prepost-score: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/api/generate-hooks")
@limiter.limit("10/minute")
def generate_hooks(request: Request, req: HookRequest, current_user_email: str = Depends(get_current_user)):
    try:
        return creator_tools.generate_hooks(niche=req.niche, topic=req.topic)
    except Exception as e:
        logger.error(f"Error in /api/generate-hooks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/api/seo-caption")
@limiter.limit("10/minute")
def generate_seo_caption(request: Request, req: SeoCaptionRequest, current_user_email: str = Depends(get_current_user)):
    try:
        return creator_tools.generate_seo_caption(description=req.description, platform=req.platform)
    except Exception as e:
        logger.error(f"Error in /api/seo-caption: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get("/api/daily-ideas")
@limiter.limit("10/minute")
def get_daily_ideas(request: Request, current_user_email: str = Depends(get_current_user)):
    try:
        return creator_tools.get_daily_ideas(user_email=current_user_email)
    except Exception as e:
        logger.error(f"Error in /api/daily-ideas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/api/calendar")
@limiter.limit("5/minute")
def create_calendar(request: Request, req: CalendarRequest, current_user_email: str = Depends(get_current_user)):
    try:
        res = creator_tools.generate_calendar(
            user_email=current_user_email,
            niche=req.niche,
            language=req.language,
            frequency=req.frequency
        )
        # Upsert in DB
        calendar_data = {
            "user_email": current_user_email,
            "niche": req.niche,
            "language": req.language,
            "frequency": req.frequency,
            "schedule_data": res
        }
        supabase.table("calendar_plans").upsert(calendar_data, on_conflict="user_email").execute()
        return res
    except Exception as e:
        logger.error(f"Error in /api/calendar: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get("/api/calendar")
@limiter.limit("10/minute")
def get_calendar(request: Request, current_user_email: str = Depends(get_current_user)):
    try:
        res = supabase.table("calendar_plans").select("*").eq("user_email", current_user_email).execute()
        if res.data:
            return res.data[0]["schedule_data"]
        return {"calendar": []}
    except Exception as e:
        logger.error(f"Error getting calendar: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


# ── Brand Deal Marketplace ────────────────────────────────────────────────────

@app.get("/api/marketplace/profiles")
@limiter.limit("30/minute")
def get_creator_profiles(request: Request, niche: Optional[str] = None):
    try:
        q = supabase.table("creator_profiles").select("*").eq("is_active", True)
        if niche and niche != "all":
            q = q.eq("niche", niche)
        res = q.order("followers", desc=True).execute()
        return res.data or []
    except Exception as e:
        logger.error(f"Error getting creator profiles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/api/marketplace/profile")
@limiter.limit("10/minute")
def create_or_update_profile(request: Request, req: CreatorProfileRequest, current_user_email: str = Depends(get_current_user)):
    try:
        profile_data = {
            "user_email": current_user_email,
            "instagram_username": req.instagram_username,
            "niche": req.niche,
            "followers": req.followers,
            "engagement_rate": req.engagement_rate,
            "trend_score": req.trend_score,
            "portfolio_links": req.portfolio_links,
            "price_per_post": req.price_per_post,
            "is_active": True
        }
        res = supabase.table("creator_profiles").upsert(profile_data, on_conflict="user_email").execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        logger.error(f"Error saving/updating creator profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/api/marketplace/deals")
@limiter.limit("10/minute")
def create_brand_deal(request: Request, req: BrandDealRequest, current_user_email: str = Depends(get_current_user)):
    try:
        # Calculate 15% commission
        commission = req.deal_amount * 0.15
        deal_data = {
            "creator_email": current_user_email,
            "brand_name": req.brand_name,
            "deal_amount": req.deal_amount,
            "commission_amount": commission,
            "status": "pending",
            "details": req.details
        }
        res = supabase.table("brand_deals").insert(deal_data).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        logger.error(f"Error creating brand deal: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get("/api/marketplace/deals")
@limiter.limit("20/minute")
def get_brand_deals(request: Request, current_user_email: str = Depends(get_current_user)):
    try:
        res = supabase.table("brand_deals").select("*").eq("creator_email", current_user_email).order("created_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        logger.error(f"Error getting brand list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
