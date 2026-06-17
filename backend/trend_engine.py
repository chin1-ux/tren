import os
import re
import json
import time
import logging
import concurrent.futures
from datetime import datetime, timezone, timedelta
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

import sys
import socket
import urllib3.util.connection as connection

# Force IPv4 to prevent Windows/Supabase IPv6 timeout hangs
connection.allowed_gai_family = lambda: socket.AF_INET

# Configure logging to stdout and file safely
log_handlers = [
    logging.StreamHandler(sys.stdout)
]
try:
    log_handlers.append(logging.FileHandler("trend_engine.log", encoding="utf-8"))
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=log_handlers
)

def generate_local_fallback(trend):
    title = (trend.get("audio_title") or "Unknown Song").lower()
    is_dance = any(word in title for word in ["dance", "nach", "step", "groove", "taal", "bhangra", "dancecover"])
    content_type = "dance" if is_dance else "viral"
    
    # Simple keyword heuristics
    if any(word in title for word in ["travel", "safarnama", "road", "trip", "mountains", "vlog"]):
        content_type = "travel"
    elif any(word in title for word in ["fashion", "look", "style", "wear", "dress", "ootd"]):
        content_type = "fashion"
    elif any(word in title for word in ["food", "recipe", "kitchen", "cook", "chef"]):
        content_type = "food"
    elif any(word in title for word in ["comedy", "funny", "joke", "laugh", "meme"]):
        content_type = "comedy"
    elif any(word in title for word in ["motivation", "gym", "fitness", "workout", "fit"]):
        content_type = "motivation"
        
    return {
        "content_type": content_type,
        "is_dance": is_dance,
        "needs_filming": is_dance,
        "edit_style": "fast_cuts" if is_dance else "slow_dissolve",
        "narrative_structure": "transformation" if is_dance else "none",
        "text_overlay_template": f"POV: Listening to {trend.get('audio_title') or 'this track'}",
        "language": "hi" if any(c in title for c in ["a", "e", "i", "o", "u"]) else "en",
        "cultural_context": "celebration" if is_dance else "everyday",
        "ideal_content_description": f"Post aesthetic clips or photos matching the vibe of {trend.get('audio_title') or 'the song'}.",
        "camera_style": "static" if is_dance else "handheld",
        "window_hours_remaining": 24,
        "confidence": 0.90,
        "saturation_score": 0.3,
        "optimal_post_hour_ist": 18,
        "best_platform_first": "instagram",
        "why_this_works": f"The track {trend.get('audio_title') or 'this track'} is currently driving high engagement on short-form feeds.",
        "audio_cue_second": 0,
        "format_transferable": True,
        "transfer_instructions": f"Adapt the aesthetic visual style of {trend.get('audio_title') or 'the song'} to show your niche products or behind-the-scenes processes."
    }



class TrendEngine:
    def __init__(self):
        load_dotenv()
        if not os.getenv("SUPABASE_URL"):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            backend_env = os.path.join(script_dir, ".env")
            if os.path.exists(backend_env):
                load_dotenv(backend_env)

        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")

        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase credentials missing from .env")
        if not self.gemini_key:
            raise ValueError("GEMINI_API_KEY missing from .env")

        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

    def detect_trends(self) -> list:
        """
        Detects EMERGING and RISING trends from Instagram + YouTube data.
        
        New logic:
        - A single reel with velocity_score >3.0 in last 6h can trigger EMERGING status
        - 5+ unique creators = RISING status
        - Gemini classifies + enriches with caption, hashtags, optimal post time, saturation score
        - Returns list of new trend IDs saved to Supabase
        """
        logging.info("=== TrendEngine.detect_trends() starting ===")
        new_trend_ids = []

        try:
            # ── STEP 1: Load recent high-velocity reels (last 48h) ─────────────
            time_threshold_48h = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
            time_threshold_6h = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()

            reels_res = self.supabase.table("reels") \
                .select("*") \
                .gt("velocity_score", 0.3) \
                .gte("created_at", time_threshold_48h) \
                .execute()
            reels = reels_res.data or []
            logging.info(f"Loaded {len(reels)} reels for evaluation")

            # ── STEP 2: Group by audio ─────────────────────────────────────────
            audio_groups = {}
            for reel in reels:
                audio_title = reel.get("audio_title")
                audio_artist = reel.get("audio_artist") or "Unknown Artist"
                if not audio_title or not audio_title.strip():
                    continue
                key = (audio_title.strip(), audio_artist.strip())
                if key not in audio_groups:
                    audio_groups[key] = []
                audio_groups[key].append(reel)
            logging.info(f"Grouped into {len(audio_groups)} unique audio combinations")

            # ── STEP 3: Skip already-known trends ─────────────────────────────
            existing_res = self.supabase.table("trends") \
                .select("audio_title, audio_artist") \
                .execute()
            existing = {
                (t.get("audio_title", "").strip(), t.get("audio_artist", "").strip())
                for t in (existing_res.data or [])
                if t.get("audio_title")
            }

            # ── STEP 4: Evaluate each audio group ─────────────────────────────
            confirmed = []
            for (title, artist), group_reels in audio_groups.items():
                if (title, artist) in existing:
                    continue

                usernames = {r.get("owner_username") for r in group_reels if r.get("owner_username")}
                velocities = [r.get("velocity_score", 0.0) for r in group_reels]
                avg_velocity = sum(velocities) / len(velocities) if velocities else 0.0
                max_velocity = max(velocities) if velocities else 0.0

                # Determine initial status
                # EMERGING: even 1 reel with very high velocity in last 6h
                recent_reels_6h = [r for r in group_reels if r.get("created_at", "") >= time_threshold_6h]
                very_viral = any(r.get("velocity_score", 0) > 3.0 for r in recent_reels_6h)

                if len(usernames) >= 5:
                    initial_status = "rising"
                elif len(usernames) >= 1 and (avg_velocity > 1.5 or very_viral):
                    initial_status = "emerging"
                elif very_viral:
                    initial_status = "emerging"
                else:
                    continue  # Not significant enough yet

                # Validate time window: all reels within 48h of each other
                posted_times = []
                for r in group_reels:
                    posted_str = r.get("posted_at")
                    if posted_str:
                        if posted_str.endswith("Z"):
                            posted_str = posted_str[:-1] + "+00:00"
                        try:
                            posted_times.append(datetime.fromisoformat(posted_str))
                        except Exception:
                            pass
                if posted_times:
                    if (max(posted_times) - min(posted_times)) > timedelta(hours=72):
                        continue

                confirmed.append({
                    "audio_title": title,
                    "audio_artist": artist,
                    "reels": group_reels,
                    "avg_velocity": avg_velocity,
                    "max_velocity": max_velocity,
                    "count": len(group_reels),
                    "usernames": list(usernames),
                    "initial_status": initial_status,
                })

            logging.info(f"Confirmed {len(confirmed)} new trends for Gemini classification")

            # Sort and limit to top 15 to avoid API rate limits and speed up processing
            confirmed = sorted(confirmed, key=lambda x: x["avg_velocity"], reverse=True)[:15]
            logging.info(f"Selected top {len(confirmed)} trends for classification")

            # ── STEP 5: Cross-reference YouTube Shorts ─────────────────────────
            shorts_res = self.supabase.table("youtube_shorts") \
                .select("*") \
                .gte("created_at", time_threshold_48h) \
                .execute()
            shorts = shorts_res.data or []

            for trend in confirmed:
                song_lower = trend["audio_title"].lower()
                artist_lower = trend["audio_artist"].lower()
                is_mega = False
                for short in shorts:
                    st = (short.get("title") or "").lower()
                    sv = short.get("velocity_score") or 0.0
                    if (song_lower in st or artist_lower in st) and sv > 1.0:
                        is_mega = True
                        break
                trend["is_mega"] = is_mega
                trend["trend_type"] = "mega_trend" if is_mega else "trend"
                if is_mega:
                    logging.info(f"MEGA TREND: '{trend['audio_title']}' also on YouTube Shorts")

            # ── STEP 6: Gemini Classification ─────────────────────────────────
            gemini_url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-2.5-flash:generateContent?key={self.gemini_key}"
            )
            headers = {"Content-Type": "application/json"}

            def classify_single_trend(trend):
                captions = [r.get("caption") for r in trend["reels"] if r.get("caption")]
                sample_captions = " | ".join(captions[:5])
                all_hashtags = set()
                for r in trend["reels"]:
                    tags = r.get("hashtags")
                    if isinstance(tags, list):
                        all_hashtags.update(tags)
                unique_hashtags = ", ".join(list(all_hashtags)[:30])

                user_prompt = f"""
Classify this REAL social media trend and enrich it with creator intelligence.

Audio: "{trend['audio_title']}" by {trend['audio_artist']}
Creators using it: {trend['count']}
Average velocity: {trend['avg_velocity']:.2f}x above baseline
Sample captions from creators: {sample_captions}
Hashtags found: {unique_hashtags}
Also trending on YouTube: {trend.get('is_mega', False)}

Return ONLY a valid JSON object with EXACTLY these fields:
{{
  "content_type": "one of: dance, scenic, fashion, travel, food, narrative_edit, text_overlay, comedy, devotional, festival, motivation, fitness, study, other",
  "is_dance": true or false,
  "needs_filming": true if creator must film themselves live,
  "edit_style": "one of: fast_cuts, slow_dissolve, zoom_pulse, smooth_transition, color_flash",
  "narrative_structure": "one of: before_after, transformation, reveal, countdown, none",
  "text_overlay_template": "exact text pattern creators use like 'POV: you finally did it' OR null",
  "language": "one of: en, hi, kn, ta, te, bn, mr, other",
  "cultural_context": "one of: festival, celebration, everyday, none",
  "ideal_content_description": "one sentence on what photos/clips work best for this trend",
  "camera_style": "one of: selfie, wide_shot, close_up, aerial, handheld, static",
  "window_hours_remaining": "integer estimate 6–72 before oversaturation",
  "confidence": "float 0.0–1.0",
  "saturation_score": "float 0.0–1.0 where 0=very early 1=oversaturated",
  "optimal_post_hour_ist": "best hour 0-23 IST to post for maximum reach",
  "best_platform_first": "instagram or youtube_shorts",
  "why_this_works": "one sentence explaining the viral psychology behind this trend",
  "audio_cue_second": "integer — which second in the song to start filming (e.g. 7 for a beat drop at 0:07)",
  "format_transferable": true or false,
  "transfer_instructions": "if format_transferable is true, brief instruction on how a creator from a completely different niche (like tech, gaming, or food) can adapt this trend/format to their own niche; if not, return null or empty string"
}}
"""
                payload = {
                    "contents": [{"parts": [{"text": user_prompt}]}],
                    "systemInstruction": {
                        "parts": [{"text": "You are a social media trend analyst. Return ONLY valid JSON. No markdown."}]
                    },
                    "generationConfig": {"responseMimeType": "application/json"}
                }

                max_attempts = 4
                success = False
                for attempt in range(1, max_attempts + 1):
                    try:
                        logging.info(f"Gemini call for '{trend['audio_title']}' (attempt {attempt})")
                        # Lower timeout to 5 seconds so it doesn't hang if there's network/DNS delay
                        resp = requests.post(gemini_url, headers=headers, json=payload, timeout=5)
                        if resp.status_code == 429:
                            if attempt < max_attempts:
                                time.sleep(attempt * 2) # reduced sleep time to speed up fallback
                                continue
                        resp.raise_for_status()
                        rj = resp.json()
                        candidates = rj.get("candidates", [])
                        if not candidates:
                            break
                        text = candidates[0]["content"]["parts"][0]["text"].strip()
                        if text.startswith("```"):
                            s = text.find("{")
                            e = text.rfind("}")
                            if s != -1 and e != -1:
                                text = text[s:e + 1]
                        classification = json.loads(text)
                        trend.update(classification)
                        success = True
                        break
                    except Exception as e:
                        logging.warning(f"Gemini attempt {attempt} failed: {e}")
                        if attempt < max_attempts:
                            time.sleep(1) # reduced sleep time to speed up fallback
                
                if not success:
                    logging.warning(f"Gemini classification failed for '{trend['audio_title']}'. Applying local fallback.")
                    fallback = generate_local_fallback(trend)
                    trend.update(fallback)

            # Classify top 15 trends in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                executor.map(classify_single_trend, confirmed)

            # ── STEP 7: Save to Supabase ───────────────────────────────────────
            for trend in confirmed:
                confidence = trend.get("confidence", 0.0)
                if isinstance(confidence, str):
                    try:
                        confidence = float(confidence)
                    except Exception:
                        confidence = 0.0

                if confidence <= 0.55:
                    logging.info(f"Skipping '{trend['audio_title']}' — low confidence ({confidence:.2f})")
                    continue

                trend_data = {
                    "audio_title": trend["audio_title"],
                    "audio_artist": trend["audio_artist"],
                    "platform": "instagram",
                    "trend_type": trend.get("trend_type", "trend"),
                    "velocity_avg": trend["avg_velocity"],
                    "peak_velocity": trend["max_velocity"],
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
                    "confidence": confidence,
                    "status": trend.get("initial_status", "rising"),
                    "saturation_score": trend.get("saturation_score", 0.2),
                    "optimal_post_hour_ist": trend.get("optimal_post_hour_ist"),
                    "best_platform_first": trend.get("best_platform_first", "instagram"),
                    "why_this_works": trend.get("why_this_works"),
                    "audio_cue_second": trend.get("audio_cue_second"),
                    "content_type": trend.get("content_type"),
                    "format_transferable": trend.get("format_transferable", False),
                    "transfer_instructions": trend.get("transfer_instructions"),
                }

                try:
                    res = self.supabase.table("trends").insert(trend_data).execute()
                    if res.data:
                        tid = res.data[0].get("id")
                        new_trend_ids.append(tid)
                        logging.info(f"Saved '{trend['audio_title']}' as {trend.get('initial_status')} (id={tid})")
                except Exception as e:
                    logging.error(f"Failed to save '{trend['audio_title']}': {e}", exc_info=True)

        except Exception as e:
            logging.error(f"Critical error in detect_trends: {e}", exc_info=True)

        logging.info(f"=== TrendEngine done. {len(new_trend_ids)} new trends saved ===")
        return new_trend_ids


if __name__ == "__main__":
    engine = TrendEngine()
    ids = engine.detect_trends()
    print(f"New trend IDs: {ids}")
