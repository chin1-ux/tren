import os
import re
import json
import time
import logging
from datetime import datetime, timezone, timedelta
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

# Configure logging
logging.basicConfig(
    filename="trend_engine.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class TrendEngine:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Fallback to backend/.env if not loaded (e.g. when run from workspace root)
        if not os.getenv("SUPABASE_URL"):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            backend_env = os.path.join(script_dir, ".env")
            if os.path.exists(backend_env):
                load_dotenv(backend_env)
                
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            logging.error("Supabase credentials (SUPABASE_URL / SUPABASE_KEY) are missing.")
            raise ValueError("Supabase credentials are missing from .env")
        if not self.gemini_key:
            logging.error("GEMINI_API_KEY is missing from environment variables.")
            raise ValueError("GEMINI_API_KEY is missing from .env")
            
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

    def detect_trends(self) -> list:
        """
        Detects trends from Instagram reels, cross-references with YouTube Shorts,
        classifies using Gemini 2.0 Flash, and saves confirmed trends to Supabase.
        """
        logging.info("Starting trend detection run...")
        new_trend_ids = []
        
        try:
            # STEP 1 — LOAD RECENT REELS
            # Read all reels where created_at is within last 48 hours and velocity_score > 0.5
            time_threshold = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
            logging.info(f"Fetching reels created since {time_threshold} with velocity_score > 0.5")
            
            reels_res = self.supabase.table("reels") \
                .select("*") \
                .gt("velocity_score", 0.5) \
                .gte("created_at", time_threshold) \
                .execute()
            
            reels = reels_res.data or []
            logging.info(f"Loaded {len(reels)} reels for evaluation.")
            
            # STEP 2 — GROUP BY AUDIO
            # Group reels by audio_title + audio_artist combination. Ignore if audio_title is null/empty.
            audio_groups = {}
            for reel in reels:
                audio_title = reel.get("audio_title")
                audio_artist = reel.get("audio_artist") or "Unknown Artist"
                
                if not audio_title or not audio_title.strip():
                    continue
                
                group_key = (audio_title.strip(), audio_artist.strip())
                if group_key not in audio_groups:
                    audio_groups[group_key] = []
                audio_groups[group_key].append(reel)
                
            logging.info(f"Grouped into {len(audio_groups)} unique audio combinations.")
            
            # STEP 3 — IDENTIFY TRENDS
            # Query existing trends to avoid duplicates
            existing_trends_res = self.supabase.table("trends").select("audio_title, audio_artist").execute()
            existing_trends = {
                (t.get("audio_title", "").strip(), t.get("audio_artist", "").strip())
                for t in (existing_trends_res.data or [])
                if t.get("audio_title")
            }
            
            confirmed_trends = []
            for (title, artist), group_reels in audio_groups.items():
                # Check 1: At least 3 different owner_username in the group
                usernames = {r.get("owner_username") for r in group_reels if r.get("owner_username")}
                if len(usernames) < 3:
                    continue
                
                # Check 2: Average velocity_score of group > 1.5
                velocities = [r.get("velocity_score", 0.0) for r in group_reels]
                avg_velocity = sum(velocities) / len(velocities) if velocities else 0.0
                if avg_velocity <= 1.5:
                    continue
                
                # Check 3: All reels posted within 48 hours of each other
                posted_times = []
                for r in group_reels:
                    posted_at_str = r.get("posted_at")
                    if posted_at_str:
                        # Clean/parse isoformat
                        if posted_at_str.endswith("Z"):
                            posted_at_str = posted_at_str[:-1] + "+00:00"
                        try:
                            posted_times.append(datetime.fromisoformat(posted_at_str))
                        except Exception as parse_err:
                            logging.warning(f"Error parsing posted_at '{posted_at_str}': {parse_err}")
                
                if not posted_times:
                    continue
                
                min_post = min(posted_times)
                max_post = max(posted_times)
                if (max_post - min_post) > timedelta(hours=48):
                    continue
                
                # Check 4: Not already saved in 'trends' table
                if (title, artist) in existing_trends:
                    continue
                
                confirmed_trends.append({
                    "audio_title": title,
                    "audio_artist": artist,
                    "reels": group_reels,
                    "avg_velocity": avg_velocity,
                    "count": len(group_reels),
                    "usernames": list(usernames)
                })
                
            logging.info(f"Identified {len(confirmed_trends)} confirmed trends from Instagram reels.")
            
            # STEP 4 — ALSO CHECK YOUTUBE SHORTS
            # Read youtube_shorts table for last 48 hours
            shorts_res = self.supabase.table("youtube_shorts") \
                .select("*") \
                .gte("created_at", time_threshold) \
                .execute()
            shorts = shorts_res.data or []
            
            # Helper to check if a song appears in YouTube Shorts with high velocity
            for trend in confirmed_trends:
                is_mega = False
                song_title = trend["audio_title"].lower()
                
                for short in shorts:
                    short_title = (short.get("title") or "").lower()
                    short_velocity = short.get("velocity_score") or 0.0
                    
                    # High velocity threshold for YouTube Shorts (e.g. > 1.0)
                    # Checking if the song title appears in YouTube Short title with high velocity
                    if song_title in short_title and short_velocity > 1.0:
                        is_mega = True
                        break
                
                trend["is_mega"] = is_mega
                trend["trend_type"] = "mega_trend" if is_mega else "trend"
                if is_mega:
                    logging.info(f"MEGA TREND detected: '{trend['audio_title']}' also trending on YouTube Shorts.")

            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_key}"
            headers = {"Content-Type": "application/json"}
            
            for trend in confirmed_trends:
                # Get sample captions (first 3)
                captions = [r.get("caption") for r in trend["reels"] if r.get("caption")]
                sample_captions = " | ".join(captions[:3])
                
                # All unique hashtags
                all_hashtags = set()
                for r in trend["reels"]:
                    tags = r.get("hashtags")
                    if isinstance(tags, list):
                        all_hashtags.update(tags)
                unique_hashtags = ", ".join(all_hashtags)
                
                user_prompt = (
                    f"Classify this social media trend: "
                    f"Audio: {trend['audio_title']} by {trend['audio_artist']} "
                    f"Sample captions: {sample_captions} "
                    f"Hashtags used: {unique_hashtags} "
                    f"Number of creators: {trend['count']} "
                    f"Average velocity: {trend['avg_velocity']}  "
                    f"Return JSON: {{   content_type: one of [dance, scenic, fashion, travel, food,     "
                    f"narrative_edit, text_overlay, comedy, devotional, festival,     "
                    f"motivation, fitness, study, other],   is_dance: true or false,   "
                    f"needs_filming: true if user must film themselves,   "
                    f"edit_style: one of [fast_cuts, slow_dissolve, zoom_pulse,     "
                    f"smooth_transition, color_flash],   narrative_structure: one of [before_after, "
                    f"transformation, reveal, countdown, none],   text_overlay_template: the exact "
                    f"text pattern used in trend like POV: you finally did it OR null if no text,   "
                    f"language: one of [en, hi, kn, ta, te, bn, mr, other],   "
                    f"cultural_context: one of [festival, celebration, everyday, none],   "
                    f"ideal_content_description: one sentence describing what photos or clips work "
                    f"best for this trend,   camera_style: one of [selfie, wide_shot, close_up,     "
                    f"aerial, handheld, static],   window_hours_remaining: your estimate of hours "
                    f"before this trend is oversaturated (between 12 and 72),   "
                    f"confidence: number between 0.0 and 1.0 }}"
                )
                
                payload = {
                    "contents": [{
                        "parts": [{"text": user_prompt}]
                    }],
                    "systemInstruction": {
                        "parts": [{"text": "You are a social media trend analyst. Classify trends accurately. Return only valid JSON. No markdown. No explanation."}]
                    },
                    "generationConfig": {
                        "responseMimeType": "application/json"
                    }
                }
                
                # Retry loop for Gemini API calls to handle rate limits (429)
                max_attempts = 4
                success = False
                for attempt in range(1, max_attempts + 1):
                    try:
                        logging.info(f"Calling Gemini API for trend '{trend['audio_title']}' (Attempt {attempt}/{max_attempts})...")
                        response = requests.post(gemini_url, headers=headers, json=payload)
                        
                        if response.status_code == 429:
                            if attempt < max_attempts:
                                sleep_time = attempt * 5
                                logging.warning(f"Gemini API rate limited (429). Retrying in {sleep_time}s...")
                                time.sleep(sleep_time)
                                continue
                        
                        response.raise_for_status()
                        
                        resp_json = response.json()
                        candidates = resp_json.get("candidates", [])
                        if not candidates:
                            logging.error(f"No generation candidates returned from Gemini for trend: {trend['audio_title']}")
                            break
                        
                        text_response = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                        # Robust JSON extraction to remove markdown wrapper if any
                        if text_response.startswith("```"):
                            start_idx = text_response.find("{")
                            end_idx = text_response.rfind("}")
                            if start_idx != -1 and end_idx != -1:
                                text_response = text_response[start_idx:end_idx+1]
                                
                        classification = json.loads(text_response)
                        
                        # Merging classification results into trend dict
                        trend.update(classification)
                        success = True
                        break
                    except Exception as gemini_err:
                        if attempt == max_attempts:
                            logging.error(f"Gemini classification failed for trend '{trend['audio_title']}' after {max_attempts} attempts: {gemini_err}", exc_info=True)
                        else:
                            logging.warning(f"Attempt {attempt} failed for Gemini API: {gemini_err}. Retrying...")
                            time.sleep(attempt * 3)

            # STEP 6 — SAVE TREND
            for trend in confirmed_trends:
                confidence = trend.get("confidence", 0.0)
                if confidence <= 0.6:
                    logging.info(f"Skipping saving trend '{trend['audio_title']}' due to confidence score ({confidence:.2f}) <= 0.6")
                    continue
                
                # Prepare saving schema payload
                trend_data = {
                    "audio_title": trend["audio_title"],
                    "audio_artist": trend["audio_artist"],
                    "platform": "instagram",
                    "trend_type": trend["trend_type"],
                    "velocity_avg": trend["avg_velocity"],
                    "reel_count": trend["count"],
                    "is_dance": trend.get("is_dance", False),
                    "needs_filming": trend.get("needs_filming", False),
                    "edit_style": trend.get("edit_style"),
                    "narrative_structure": trend.get("narrative_structure"),
                    "text_overlay_template": trend.get("text_overlay_template"),
                    "language": trend.get("language"),
                    "cultural_context": trend.get("cultural_context"),
                    "ideal_content_description": trend.get("ideal_content_description"),
                    "camera_style": trend.get("camera_style"),
                    "window_hours_remaining": int(trend.get("window_hours_remaining") or 24),
                    "confidence": confidence
                }
                
                try:
                    insert_res = self.supabase.table("trends").insert(trend_data).execute()
                    if insert_res.data:
                        inserted_id = insert_res.data[0].get("id")
                        new_trend_ids.append(inserted_id)
                        logging.info(f"Successfully saved trend '{trend['audio_title']}' with ID {inserted_id}")
                except Exception as save_err:
                    logging.error(f"Failed to save trend '{trend['audio_title']}' to Supabase: {save_err}", exc_info=True)

        except Exception as e:
            logging.error(f"Error occurred in detect_trends: {e}", exc_info=True)
            print(f"Error during trend detection: {e}")
            
        # STEP 7 — RETURN
        print(f"Trends detected this run: {len(new_trend_ids)}")
        return new_trend_ids

if __name__ == "__main__":
    engine = TrendEngine()
    engine.detect_trends()
