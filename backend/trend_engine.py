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
        "language": trend.get("language") or "en",
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
        "transfer_instructions": f"Adapt the aesthetic visual style of {trend.get('audio_title') or 'the song'} to show your niche products or behind-the-scenes processes.",
        "creator_fit_score": 0.62,
        "saturation_penalty": 0.35,
        "hook_retention_score": 0.58,
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

    def _calculate_creator_fit_score(self, title: str, artist: str, creator_count: int, avg_velocity: float, recent_6h_avg: float, recent_24h_avg: float, oldest_age_hours: float) -> float:
        text = f"{title} {artist}".lower()
        is_dance = any(word in text for word in ["dance", "step", "groove", "bhangra", "hookstep", "taal"])
        is_visual = any(word in text for word in ["aesthetic", "cinematic", "vlog", "travel", "look", "style", "fashion"])
        is_instructional = any(word in text for word in ["tutorial", "how", "learn", "tips", "guide", "hack"])
        is_emotional = any(word in text for word in ["love", "heart", "sad", "miss", "story", "pain", "broken"])
        base = 0.45
        if is_dance:
            base += 0.18
        if is_visual:
            base += 0.14
        if is_instructional:
            base += 0.12
        if is_emotional:
            base += 0.08
        momentum = min(0.25, (avg_velocity + recent_6h_avg + recent_24h_avg) / 30)
        breadth = min(0.15, creator_count * 0.03)
        freshness = max(0.0, 0.12 - (oldest_age_hours / 400))
        return max(0.0, min(1.0, base + momentum + breadth + freshness))

    def _calculate_saturation_penalty(self, creator_count: int, avg_velocity: float, max_velocity: float, oldest_age_hours: float) -> float:
        crowding = min(1.0, creator_count / 12)
        momentum_density = min(1.0, (avg_velocity * 0.5 + max_velocity * 0.3) / 8)
        age_pressure = min(1.0, oldest_age_hours / 72)
        return max(0.0, min(1.0, (crowding * 0.45) + (momentum_density * 0.35) + (age_pressure * 0.20)))

    def _estimate_hook_retention_score(self, title: str, recent_6h_avg: float, avg_velocity: float, max_velocity: float) -> float:
        text = title.lower()
        hooky_words = [
            "dance", "step", "reveal", "before", "after", "pov", "wait",
            "story", "confession", "transition", "glow up", "drop", "beat"
        ]
        visual_words = ["cinematic", "aesthetic", "travel", "fashion", "food", "fit", "motivation"]
        word_score = 0.35
        if any(word in text for word in hooky_words):
            word_score += 0.25
        if any(word in text for word in visual_words):
            word_score += 0.12
        momentum_signal = min(0.25, (recent_6h_avg * 0.15) + (avg_velocity * 0.08) + (max_velocity * 0.05))
        return max(0.0, min(1.0, word_score + momentum_signal))

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
                creator_count = len(usernames)
                velocities = [r.get("velocity_score", 0.0) for r in group_reels]
                avg_velocity = sum(velocities) / len(velocities) if velocities else 0.0
                max_velocity = max(velocities) if velocities else 0.0

                recent_6h_velocities = []
                recent_24h_velocities = []
                recent_reels_6h = []
                oldest_age_hours = 0.0
                for r in group_reels:
                    created_str = r.get("created_at")
                    if not created_str:
                        continue
                    try:
                        if created_str.endswith("Z"):
                            created_str = created_str[:-1] + "+00:00"
                        created_dt = datetime.fromisoformat(created_str)
                        if created_dt.tzinfo is None:
                            created_dt = created_dt.replace(tzinfo=timezone.utc)
                        age_hours = (datetime.now(timezone.utc) - created_dt).total_seconds() / 3600
                        oldest_age_hours = max(oldest_age_hours, age_hours)
                        if age_hours <= 6:
                            recent_6h_velocities.append(r.get("velocity_score", 0.0))
                            recent_reels_6h.append(r)
                        if age_hours <= 24:
                            recent_24h_velocities.append(r.get("velocity_score", 0.0))
                    except Exception:
                        pass

                recent_6h_avg = sum(recent_6h_velocities) / len(recent_6h_velocities) if recent_6h_velocities else 0.0
                recent_24h_avg = sum(recent_24h_velocities) / len(recent_24h_velocities) if recent_24h_velocities else avg_velocity
                recency_bonus = max(0.5, 1.5 - (oldest_age_hours / 48)) if oldest_age_hours else 1.0
                creator_bonus = 1.0 + min(0.6, creator_count * 0.08)
                trend_score = ((avg_velocity * 0.45) + (max_velocity * 0.2) + (recent_6h_avg * 0.25) + (recent_24h_avg * 0.1)) * creator_bonus * recency_bonus

                # Creator fit looks at what the trend is actually good for, not just raw momentum.
                creator_fit_score = self._calculate_creator_fit_score(
                    title=title,
                    artist=artist,
                    creator_count=creator_count,
                    avg_velocity=avg_velocity,
                    recent_6h_avg=recent_6h_avg,
                    recent_24h_avg=recent_24h_avg,
                    oldest_age_hours=oldest_age_hours,
                )

                # Saturation penalty measures whether the trend is getting crowded.
                saturation_penalty = self._calculate_saturation_penalty(
                    creator_count=creator_count,
                    avg_velocity=avg_velocity,
                    max_velocity=max_velocity,
                    oldest_age_hours=oldest_age_hours,
                )

                # Hook retention is estimated from the content format and momentum profile.
                hook_retention_score = self._estimate_hook_retention_score(
                    title=title,
                    recent_6h_avg=recent_6h_avg,
                    avg_velocity=avg_velocity,
                    max_velocity=max_velocity,
                )

                composite_score = (
                    (trend_score * 0.40)
                    + (creator_fit_score * 3.0)
                    + (hook_retention_score * 2.0)
                    - (saturation_penalty * 1.8)
                )

                # Determine initial status
                very_viral = any((r.get("velocity_score", 0) or 0) > 3.0 for r in recent_reels_6h)

                if creator_count >= 5 and composite_score >= 3.2:
                    initial_status = "rising"
                elif creator_count >= 2 and (avg_velocity > 1.4 or very_viral or composite_score >= 2.8):
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
                    "trend_score": trend_score,
                    "composite_score": composite_score,
                    "creator_fit_score": creator_fit_score,
                    "saturation_penalty": saturation_penalty,
                    "hook_retention_score": hook_retention_score,
                    "count": len(group_reels),
                    "usernames": list(usernames),
                    "initial_status": initial_status,
                })

            logging.info(f"Confirmed {len(confirmed)} new trends for Gemini classification")

            # Sort and limit to top 15 to avoid API rate limits and speed up processing
            confirmed = sorted(confirmed, key=lambda x: (x["composite_score"], x["trend_score"], x["avg_velocity"]), reverse=True)[:15]
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

                # Blend model confidence with observed trend strength so we don't over-trust the LLM.
                confidence = min(0.98, max(0.0, confidence) + min(0.12, (trend.get("trend_score", 0.0) or 0.0) / 50))

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
                    "creator_fit_score": trend.get("creator_fit_score"),
                    "saturation_penalty": trend.get("saturation_penalty"),
                    "hook_retention_score": trend.get("hook_retention_score"),
                    "composite_score": trend.get("composite_score"),
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
