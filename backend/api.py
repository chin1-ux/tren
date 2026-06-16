import os
import uuid
import json
import logging
import requests
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from supabase import create_client, Client

# Import the local modules
# To allow importing when running api.py directly or as a package
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trend_engine import TrendEngine
from alert_system import AlertSystem
from reel_generator import ReelGenerator
from beat_detector import BeatDetector
from instagram_scraper import InstagramScraper
from youtube_scraper import YouTubeScraper

# Configure logging
logging.basicConfig(
    filename="api.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load credentials from .env
load_dotenv()
# Fallback to backend/.env if not loaded (e.g. when run from workspace root)
if not os.getenv("SUPABASE_URL"):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_env = os.path.join(script_dir, ".env")
    if os.path.exists(backend_env):
        load_dotenv(backend_env)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("Supabase credentials missing from environment.")
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Create uploads/ and outputs/ directories immediately (required before mounting StaticFiles)
os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

# Initialize FastAPI application
app = FastAPI(
    title="Trendrop Backend API",
    description="FastAPI service for Trendrop social media trend detection and automated reel generation",
    version="1.0"
)

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads/ and outputs/ directories on startup
@app.on_event("startup")
def startup_event():
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)
    logger.info("Created uploads/ and outputs/ directories on startup.")

# Serve static files for generated reels
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")


# Define Schemas for input validation
class SubscribeRequest(BaseModel):
    email: EmailStr
    niche: str
    language: str


# --- ENDPOINTS ---

@app.get("/health")
def health_check():
    """Returns the API health status and version."""
    return {"status": "ok", "version": "1.0"}


@app.get("/api/trends")
def get_trends():
    """Fetch all trends from Supabase 'trends' table where status = rising, ordered by velocity_avg descending."""
    try:
        res = supabase.table("trends") \
            .select("*") \
            .eq("status", "rising") \
            .order("velocity_avg", desc=True) \
            .execute()
        trends = res.data or []
        for t in trends:
            t["song"] = t.get("audio_title")
            t["artist"] = t.get("audio_artist")
        return trends
    except Exception as e:
        logger.error(f"Error fetching trends: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch trends: {str(e)}"
        )


@app.get("/api/trends/{trend_id}")
def get_trend(trend_id: int):
    """Fetch single trend by ID from Supabase."""
    try:
        res = supabase.table("trends") \
            .select("*") \
            .eq("id", trend_id) \
            .execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trend with ID {trend_id} not found"
            )
        trend = res.data[0]
        trend["song"] = trend.get("audio_title")
        trend["artist"] = trend.get("audio_artist")
        return trend
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching trend {trend_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch trend: {str(e)}"
        )


@app.get("/api/trends/{trend_id}/reels")
def get_trend_reels(trend_id: int):
    """Fetch reels associated with a trend by matching audio_title and audio_artist."""
    try:
        # 1. Fetch the trend to get its audio_title and audio_artist
        trend_res = supabase.table("trends").select("audio_title, audio_artist").eq("id", trend_id).execute()
        if not trend_res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trend with ID {trend_id} not found"
            )
        trend = trend_res.data[0]
        title = trend.get("audio_title")
        artist = trend.get("audio_artist")
        
        # 2. Query reels matching this title and artist
        reels_res = supabase.table("reels") \
            .select("*") \
            .eq("audio_title", title) \
            .eq("audio_artist", artist) \
            .order("velocity_score", desc=True) \
            .execute()
        return reels_res.data or []
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching reels for trend {trend_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch reels: {str(e)}"
        )


@app.post("/api/subscribe")
def subscribe(request: SubscribeRequest):
    """Save user subscription info to Supabase users table (maps language -> language_preference)."""
    try:
        user_data = {
            "email": request.email,
            "niche": request.niche,
            "language_preference": request.language
        }
        # Using upsert to prevent conflicts on unique constraint on email
        res = supabase.table("users").upsert(user_data, on_conflict="email").execute()
        if not res.data:
            raise Exception("No data returned from database upsert.")
        return {"success": True, "message": "You are subscribed"}
    except Exception as e:
        logger.error(f"Error subscribing email {request.email}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to subscribe: {str(e)}"
        )


# --- BACKGROUND TASKS ---

def run_reel_generation(job_id: str, file_paths: List[str], trend_id: str):
    """Background task to run reel generation."""
    logger.info(f"Background task run_reel_generation started for job {job_id}")
    try:
        # 1. Update job status to processing
        supabase.table("jobs").update({"status": "processing", "progress": 0}).eq("id", int(job_id)).execute()
        
        # 2. Fetch trend data from Supabase
        trend_res = supabase.table("trends").select("*").eq("id", int(trend_id)).execute()
        if not trend_res.data:
            raise ValueError(f"Trend with ID {trend_id} not found in database.")
        trend_data = trend_res.data[0]
        
        # 3. If trend has audio_url: download the audio file
        audio_path = None
        audio_url = trend_data.get("audio_url")
        if audio_url:
            try:
                logger.info(f"Downloading audio from {audio_url} for job {job_id}...")
                audio_path = os.path.join(f"uploads/{job_id}", "audio.mp3")
                response = requests.get(audio_url, timeout=30)
                response.raise_for_status()
                with open(audio_path, "wb") as audio_file:
                    audio_file.write(response.content)
                logger.info(f"Downloaded audio to {audio_path}")
            except Exception as download_err:
                logger.warning(f"Failed to download audio from {audio_url}: {download_err}. Proceeding without audio.")
                audio_path = None
                
        # 4. Create ReelGenerator instance
        generator = ReelGenerator()
        
        # 5. Define progress callback to update progress field in Supabase jobs table
        def progress_callback(progress_val: int):
            supabase.table("jobs").update({"progress": progress_val}).eq("id", int(job_id)).execute()
            
        # 6. Call generate_reel()
        output_path = os.path.join("outputs", f"{job_id}.mp4")
        generator.generate_reel(
            image_paths=file_paths,
            audio_path=audio_path,
            output_path=output_path,
            progress_callback=progress_callback
        )
        
        # 7. Update job: status=complete, output_url=/outputs/{job_id}.mp4
        output_url = f"/outputs/{job_id}.mp4"
        supabase.table("jobs").update({
            "status": "complete",
            "progress": 100,
            "output_url": output_url
        }).eq("id", int(job_id)).execute()
        logger.info(f"Job {job_id} completed successfully.")
        
    except Exception as err:
        logger.error(f"Error generating reel for job {job_id}: {err}", exc_info=True)
        # 8. Update job: status=failed, error_message=str(error)
        try:
            supabase.table("jobs").update({
                "status": "failed",
                "error_message": str(err)
            }).eq("id", int(job_id)).execute()
        except Exception as update_err:
            logger.error(f"Failed to set job {job_id} to failed state in Supabase: {update_err}")


def run_scrapers_background():
    """Background task to run scrapers, trend detection, and notification engines in sequence."""
    logger.info("Background scraper runner started.")
    try:
        # 1. Instagram Scraper
        try:
            logger.info("Running Instagram Scraper...")
            insta = InstagramScraper()
            insta.scrape_trending_reels()
        except Exception as e:
            logger.error(f"Instagram Scraper background run failed: {e}", exc_info=True)
            
        # 2. YouTube Scraper
        try:
            logger.info("Running YouTube Scraper...")
            yt = YouTubeScraper()
            yt.scrape_trending_shorts()
        except Exception as e:
            logger.error(f"YouTube Scraper background run failed: {e}", exc_info=True)
            
        # 3. Trend Engine
        new_trend_ids = []
        try:
            logger.info("Running Trend Detection Engine...")
            te = TrendEngine()
            new_trend_ids = te.detect_trends()
        except Exception as e:
            logger.error(f"Trend Engine background run failed: {e}", exc_info=True)
            
        # 4. Alert System
        if new_trend_ids:
            try:
                logger.info(f"New trends detected: {new_trend_ids}. Running Alert System...")
                alert = AlertSystem()
                alert.send_trend_alerts(new_trend_ids)
            except Exception as e:
                logger.error(f"Alert System background run failed: {e}", exc_info=True)
        else:
            logger.info("No new trends detected. Skipping Alert System.")
            
        logger.info("Background scraper runner completed successfully.")
    except Exception as e:
        logger.error(f"Critical failure in background scraper runner: {e}", exc_info=True)


# --- API ENDPOINTS (CONT.) ---

@app.post("/api/generate-reel")
async def generate_reel_endpoint(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    trend_id: str = Form(...),
    user_email: str = Form(...)
):
    """
    Accepts multipart form data to queue a reel generation job.
    Saves files locally, initializes a pending job in Supabase,
    and runs generation in the background.
    """
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files uploaded.")
        
    try:
        # 1. Create job record in Supabase jobs table with status=pending
        job_data = {
            "job_type": "reel_generation",
            "status": "pending",
            "user_email": user_email,
            "progress": 0,
            "input_data": json.dumps({"files_count": len(files), "trend_id": trend_id})
        }
        res = supabase.table("jobs").insert(job_data).execute()
        if not res.data:
            raise ValueError("Failed to create job entry in database.")
            
        job_record = res.data[0]
        job_id = str(job_record["id"])
        
        # 2. Save uploaded files to uploads/{job_id}/ folder
        job_upload_dir = f"uploads/{job_id}"
        os.makedirs(job_upload_dir, exist_ok=True)
        
        file_paths = []
        for file in files:
            # Prevent path traversal security issue by taking basename
            filename = os.path.basename(file.filename)
            file_path = os.path.join(job_upload_dir, filename)
            
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            file_paths.append(file_path)
            
        # 3. Start background task: run_reel_generation(job_id, files, trend_id)
        background_tasks.add_task(run_reel_generation, job_id, file_paths, trend_id)
        
        # 4. Return immediately: {job_id: string}
        return {"job_id": job_id}
        
    except Exception as e:
        logger.error(f"Error handling generate-reel request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate reel generation: {str(e)}"
        )


@app.get("/api/reel-status/{job_id}")
def get_reel_status(job_id: int):
    """Fetch job from Supabase by job_id."""
    try:
        res = supabase.table("jobs").select("*").eq("id", job_id).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job with ID {job_id} not found."
            )
            
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
        logger.error(f"Error fetching status for job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch job status: {str(e)}"
        )


@app.post("/api/run-scraper")
def trigger_scraper(background_tasks: BackgroundTasks):
    """Trigger Instagram + YouTube scraper manually. Run as background task."""
    try:
        background_tasks.add_task(run_scrapers_background)
        return {"message": "Scraper started"}
    except Exception as e:
        logger.error(f"Failed to start scraper background task: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger scraper: {str(e)}"
        )
