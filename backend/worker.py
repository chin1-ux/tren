import os
import json
import logging
import time
import requests
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("worker")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2.2 UPSTASH REDIS CACHING
import redis
UPSTASH_REDIS_URL = os.getenv("UPSTASH_REDIS_URL")
if UPSTASH_REDIS_URL:
    try:
        redis_client = redis.from_url(UPSTASH_REDIS_URL)
    except Exception as e:
        logger.error(f"Failed to connect to Upstash Redis: {e}")
        redis_client = None
else:
    redis_client = None

def update_job_progress(job_id: str, progress: int, status: str = "processing", output_url: str = None, error_message: str = None):
    # Update Supabase database
    try:
        payload = {
            "status": status,
            "progress": progress
        }
        if output_url:
            payload["output_url"] = output_url
        if error_message:
            payload["error_message"] = error_message
        supabase.table("jobs").update(payload).eq("id", int(job_id)).execute()
    except Exception as e:
        logger.error(f"Failed to update job progress in database: {e}")
        
    # Cache job progress in Redis with 1 hour TTL
    if redis_client:
        try:
            cache_payload = {
                "status": status,
                "progress": progress,
                "output_url": output_url,
                "error_message": error_message
            }
            redis_client.setex(f"job_progress:{job_id}", 3600, json.dumps(cache_payload))
        except Exception as e:
            logger.error(f"Failed to cache job progress: {e}")

def run_video_generation_job(job_id: str, job_type: str, trend_id: str, files: list = None, extra_params: dict = None):
    logger.info(f"Worker processing job: job={job_id} type={job_type}")
    try:
        update_job_progress(job_id, 10, "processing")
        time.sleep(2.0)
        
        # Audio extraction
        audio_url = None
        if trend_id and trend_id.isdigit():
            try:
                res = supabase.table("trends").select("audio_url").eq("id", int(trend_id)).execute()
                if res.data:
                    audio_url = res.data[0].get("audio_url")
            except Exception as e:
                logger.error(f"Error fetching audio_url: {e}")
                
        update_job_progress(job_id, 30, "processing")
        time.sleep(2.0)
        
        # Generate simulation
        output_url = f"/outputs/{job_id}.mp4"
        output_path = os.path.join("outputs", f"{job_id}.mp4")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # File copy or fallback download
        downloaded = False
        sample_urls = [
            "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
            "https://assets.mixkit.co/videos/preview/mixkit-drones-eye-view-of-a-harbour-city-43283-large.mp4"
        ]
        for s_url in sample_urls:
            try:
                resp = requests.get(s_url, timeout=15)
                resp.raise_for_status()
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                downloaded = True
                break
            except Exception as de:
                logger.warning(f"Failed to download sample video: {de}")
                
        if not downloaded:
            with open(output_path, "wb") as f:
                f.write(b"dummy mp4 content")
                
        update_job_progress(job_id, 80, "processing")
        time.sleep(2.0)
        
        # 2.4 FILE STORAGE: Upload to Supabase Storage outputs bucket
        # Upload user files & outputs to Supabase Storage buckets: uploads & outputs
        try:
            with open(output_path, "rb") as f:
                file_content = f.read()
            # Upload generated output
            bucket_path = f"outputs/{job_id}/reel.mp4"
            supabase.storage.from_("outputs").upload(
                file=file_content,
                path=bucket_path,
                file_options={"content-type": "video/mp4"}
            )
            # Create a signed URL valid for 24 hours
            signed_res = supabase.storage.from_("outputs").create_signed_url(bucket_path, 86400)
            if signed_res and "signedURL" in signed_res:
                output_url = signed_res["signedURL"]
            else:
                output_url = f"{SUPABASE_URL}/storage/v1/object/public/outputs/{bucket_path}"
        except Exception as upload_err:
            logger.error(f"Failed to upload generated reel to Supabase Storage: {upload_err}")
            # Fallback to local URL if storage fails
            output_url = f"/outputs/{job_id}.mp4"
            
        update_job_progress(job_id, 100, "complete", output_url=output_url)
        logger.info(f"Worker completed job {job_id}")
    except Exception as err:
        logger.error(f"Worker failed job {job_id}: {err}")
        update_job_progress(job_id, 100, "failed", error_message=str(err))
