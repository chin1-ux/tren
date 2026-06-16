import os
import uuid
import json
import logging
import requests
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from supabase import create_client, Client
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trend_engine import TrendEngine
from alert_system import AlertSystem
from reel_generator import ReelGenerator
from beat_detector import BeatDetector
from instagram_scraper import InstagramScraper
from youtube_scraper import YouTubeScraper
from caption_engine import CaptionEngine
from trend_refresher import TrendRefresher

logging.basicConfig(
    filename="api.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()
if not os.getenv("SUPABASE_URL"):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_env = os.path.join(script_dir, ".env")
    if os.path.exists(backend_env):
        load_dotenv(backend_env)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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

# CORS — allow all origins for dev; tighten to Vercel domain in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)
    logger.info("Trendrop API v2.0 started.")

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
    try:
        res = supabase.table("trends") \
            .select("*") \
            .in_("status", ["emerging", "rising"]) \
            .order("velocity_avg", desc=True) \
            .execute()
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


# ── User / Subscribe ───────────────────────────────────────────────────────────

@app.post("/api/subscribe")
@limiter.limit("10/minute")
def subscribe(request: Request, req: SubscribeRequest):
    """Save user subscription to Supabase users table."""
    try:
        user_data = {
            "email": req.email,
            "niche": req.niche,
            "language_preference": req.language
        }
        res = supabase.table("users").upsert(user_data, on_conflict="email").execute()
        if not res.data:
            raise Exception("No data returned from upsert")
        return {"success": True, "message": "You are subscribed!"}
    except Exception as e:
        logger.error(f"Subscribe failed for {req.email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── Feedback ───────────────────────────────────────────────────────────────────

@app.post("/api/feedback")
@limiter.limit("20/minute")
def submit_feedback(request: Request, req: FeedbackRequest):
    """
    Creator feedback on a trend: too_late | too_early | perfect | stale.
    Stored in trend_feedback table for future ML training signal.
    """
    try:
        feedback_data = {
            "trend_id": req.trend_id,
            "feedback_type": req.feedback_type,
            "comment": req.comment,
            "user_email": req.user_email,
        }
        supabase.table("trend_feedback").insert(feedback_data).execute()
        return {"success": True, "message": "Feedback received. Thank you!"}
    except Exception as e:
        logger.error(f"Feedback save failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
def trigger_scraper(request: Request, background_tasks: BackgroundTasks):
    """Manually trigger the full scraper + trend detection pipeline."""
    try:
        background_tasks.add_task(run_scrapers_background)
        return {"message": "Pipeline started in background"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
