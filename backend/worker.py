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
        
        # Audio extraction
        audio_url = None
        if trend_id and trend_id.isdigit():
            try:
                res = supabase.table("trends").select("audio_url").eq("id", int(trend_id)).execute()
                if res.data:
                    audio_url = res.data[0].get("audio_url")
            except Exception as e:
                logger.error(f"Error fetching audio_url: {e}")
                
        update_job_progress(job_id, 20, "processing")
        
        # Download files locally
        local_files = []
        if files:
            for f in files:
                local_path = os.path.join("uploads", job_id, os.path.basename(f))
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                try:
                    res_bytes = supabase.storage.from_("uploads").download(f)
                    with open(local_path, "wb") as out_f:
                        out_f.write(res_bytes)
                    local_files.append(local_path)
                except Exception as dl_err:
                    logger.warning(f"Could not download file {f} from Supabase, checking if local path exists: {dl_err}")
                    if os.path.exists(f):
                        local_files.append(f)
                    elif os.path.exists(local_path):
                        local_files.append(local_path)
                    else:
                        raise RuntimeError(f"Source file {f} could not be retrieved: {dl_err}")
        
        update_job_progress(job_id, 30, "processing")
        
        audio_path = None
        if audio_url:
            try:
                upload_dir = f"uploads/{job_id}"
                os.makedirs(upload_dir, exist_ok=True)
                audio_path = os.path.join(upload_dir, "audio.mp3")
                resp = requests.get(audio_url, timeout=15)
                resp.raise_for_status()
                with open(audio_path, "wb") as f:
                    f.write(resp.content)
            except Exception as ae:
                logger.warning(f"Failed to download audio from {audio_url}: {ae}")
                audio_path = None
                
        output_url = f"/outputs/{job_id}.mp4"
        output_path = os.path.join("outputs", f"{job_id}.mp4")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Invoke actual ReelGenerator
        from reel_generator import ReelGenerator
        generator = ReelGenerator()
        def progress_cb(pct: int):
            scaled = 30 + int(pct * 0.5)
            update_job_progress(job_id, scaled, "processing")
            
        generator.generate_reel(
            image_paths=local_files,
            audio_path=audio_path,
            output_path=output_path,
            progress_callback=progress_cb
        )
        
        update_job_progress(job_id, 85, "processing")
        
        # 2.4 FILE STORAGE: Upload to Supabase Storage outputs bucket
        storage_ok = False
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
            storage_ok = True
        except Exception as upload_err:
            logger.error(f"Failed to upload generated reel to Supabase Storage: {upload_err}")
            # Do NOT fall back to a local path — it will 404 for the user in production.
            # Mark the job failed so the frontend shows a clear error state.
            update_job_progress(
                job_id, 100, "failed",
                error_message=f"Video generated but upload failed: {upload_err}. Please retry."
            )
            return

        if storage_ok:
            update_job_progress(job_id, 100, "complete", output_url=output_url)
            logger.info(f"Worker completed job {job_id}")
    except Exception as err:
        logger.error(f"Worker failed job {job_id}: {err}")
        update_job_progress(job_id, 100, "failed", error_message=str(err))

