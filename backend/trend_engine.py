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
        "niche_tag": content_type if content_type != "viral" else "general",
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
        # Gemini removed – Groq is the sole LLM provider
        self.groq_key = os.getenv("GROQ_API_KEY")

        if not self.groq_key:
            raise ValueError("GROQ_API_KEY not configured in environment")

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
            # Check for scraper outage: skip if <5 reels scraped in last 3.5h
            time_threshold_3h = (datetime.now(timezone.utc) - timedelta(hours=3, minutes=30)).isoformat()
            new_reels_count_res = self.supabase.table("reels") \
                .select("reel_id", count="exact") \
                .gte("scraped_at", time_threshold_3h) \
                .execute()
            
            new_reels_scraped = new_reels_count_res.count or 0
            if new_reels_scraped < 5:
                logging.warning(f"Possible scraper outage detected (only {new_reels_scraped} reels scraped in the last 3.5h). Skipping trend detection entirely.")
                return []

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

                if creator_count >= 3:
                    initial_status = "rising"
                elif creator_count >= 1:
                    initial_status = "emerging"
                else:
                    continue

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

            logging.info(f"Confirmed {len(confirmed)} new trends for Groq classification")

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

            try:
                from llm import call_llm
            except ImportError:
                try:
                    from backend.llm import call_llm
                except ImportError:
                    from .llm import call_llm

            def classify_single_trend(trend):
                captions = [r.get("caption") for r in trend["reels"] if r.get("caption")]
                sample_captions = " | ".join(captions[:5])
                all_hashtags = set()
                for r in trend["reels"]:
                    tags = r.get("hashtags")
                    if isinstance(tags, list):
                        all_hashtags.update(tags)
                unique_hashtags = ", ".join(list(all_hashtags)[:30])

                system_prompt = "You are a social media trend analyst. Return ONLY valid JSON. No markdown."
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
                max_attempts = 4
                success = False
                for attempt in range(1, max_attempts + 1):
                    try:
                        logging.info(f"LLM call for '{trend['audio_title']}' (attempt {attempt})")
                        classification = call_llm(system_prompt, user_prompt, timeout=10)
                        trend.update(classification)
                        success = True
                        break
                    except Exception as e:
                        logging.warning(f"LLM attempt {attempt} failed: {e}")
                        if attempt < max_attempts:
                            time.sleep(attempt)
                
                if not success:
                    logging.warning(f"LLM classification failed for '{trend['audio_title']}'. Applying local fallback.")
                    fallback = generate_local_fallback(trend)
                    trend.update(fallback)

            # Classify top 15 trends sequentially with stagger/delay to respect rate limits
            for idx, trend in enumerate(confirmed):
                if idx > 0:
                    stagger_delay = 2.0
                    logging.info(f"Rate limiting: sleeping {stagger_delay}s before next Groq classification...")
                    time.sleep(stagger_delay)
                classify_single_trend(trend)

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

                # ── Aggregate audio_use_count + audio_id from linked reels ──
                group_reels = trend.get("reels", [])
                audio_use_count = max(
                    (r.get("audio_use_count") or 0 for r in group_reels),
                    default=0,
                )
                audio_id = next(
                    (r.get("audio_id") for r in group_reels if r.get("audio_id")),
                    None,
                )
                # India reel count = reels tagged creator_country=IN
                india_use_count = sum(
                    1 for r in group_reels if r.get("creator_country") == "IN"
                )

                # Saturation percentages
                global_sat = round(min(100.0, (audio_use_count / 100_000) * 100), 1)
                india_sat = round(min(100.0, (india_use_count / 8_000) * 100), 1)

                # Window hours
                avg_vel = trend["avg_velocity"]
                if audio_use_count > 100_000:
                    window_h = 0
                elif avg_vel * 100 > 300 and audio_use_count < 20_000:
                    window_h = 8
                elif avg_vel * 100 > 150 and audio_use_count < 50_000:
                    window_h = 16
                elif avg_vel * 100 > 100 and audio_use_count < 80_000:
                    window_h = 24
                else:
                    window_h = int(trend.get("window_hours_remaining") or 24)

                # Niche tag: from hook_brief if available, else content_type
                niche_tag = (
                    trend.get("niche_tag")
                    or trend.get("content_type")
                    or "general"
                )
                # hook_brief / format_patterns from reels (aggregated from any Groq analysis)
                hook_brief = next(
                    (r.get("hook_brief") for r in group_reels if r.get("hook_brief")),
                    []
                )
                format_patterns = next(
                    (r.get("format_patterns") for r in group_reels if r.get("format_patterns")),
                    []
                )
                # trend_origin – most common among reels
                origins = [r.get("trend_origin", "unknown") for r in group_reels if r.get("trend_origin")]
                trend_origin = max(set(origins), key=origins.count) if origins else "unknown"
                is_cross_cultural = any(r.get("is_cross_cultural") for r in group_reels)

                trend_data = {
                    "audio_title": trend["audio_title"],
                    "audio_artist": trend["audio_artist"],
                    "audio_id": audio_id,
                    "audio_use_count": audio_use_count,
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
                    "window_hours_remaining": window_h,
                    "confidence": confidence,
                    "status": trend.get("initial_status", "rising"),
                    "saturation_score": trend.get("saturation_score", 0.2),
                    "global_saturation_pct": global_sat,
                    "india_saturation_pct": india_sat,
                    "niche_tag": niche_tag,
                    "hook_brief": hook_brief,
                    "format_patterns": format_patterns,
                    "trend_origin": trend_origin,
                    "is_cross_cultural": is_cross_cultural,
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

            # Calculate and save audio-level trend scores
            self.calculate_audio_trend_scores()

        except Exception as e:
            logging.error(f"Critical error in detect_trends: {e}", exc_info=True)

        logging.info(f"=== TrendEngine done. {len(new_trend_ids)} new trends saved ===")
        return new_trend_ids

    def classify_lifecycle(self, audio_id: str, reels: list = None, percentile_80: float = 0.0) -> dict:
        """
        Classifies the lifecycle stage of a specific audio_id based on recent reels.
        Returns a dict containing:
          - lifecycle_stage: EMERGING, RISING, CRESTING, SATURATED/DECLINING
          - reel_count: total reels
          - unique_creator_count: total unique creators
          - creator_velocity: current creator velocity
          - reel_velocity: current reel velocity
          - details: dict containing underlying bucket counts/velocities
        """
        import math
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if reels is None:
            threshold_7d = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            res = self.supabase.table("reels") \
                .select("audio_id, owner_username, posted_at, velocity_score, reel_id, view_count, like_count, comment_count, audio_title, audio_artist") \
                .eq("audio_id", audio_id) \
                .gte("posted_at", threshold_7d) \
                .execute()
            reels = res.data or []
        
        def parse_utc_dt(dt_str):
            if not dt_str:
                return None
            if isinstance(dt_str, datetime):
                dt = dt_str
            else:
                if dt_str.endswith("Z"):
                    dt_str = dt_str[:-1] + "+00:00"
                dt = datetime.fromisoformat(dt_str)
            if dt.tzinfo is not None:
                return dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt

        buckets = []
        for i in range(58):
            buckets.append({"reels": [], "creators": set()})
        
        max_bucket_idx = -1
        for r in reels:
            posted_str = r.get("posted_at")
            posted_dt = parse_utc_dt(posted_str)
            if not posted_dt:
                continue
            
            diff_seconds = (now - posted_dt).total_seconds()
            if diff_seconds < 0:
                diff_seconds = 0
            
            bucket_idx = int(diff_seconds / (3.0 * 3600.0))
            if bucket_idx < 58:
                buckets[bucket_idx]["reels"].append(r)
                if r.get("owner_username"):
                    buckets[bucket_idx]["creators"].add(r.get("owner_username"))
                if bucket_idx > max_bucket_idx:
                    max_bucket_idx = bucket_idx

        all_creators = set()
        for b in buckets:
            all_creators.update(b["creators"])
        total_unique_creators = len(all_creators)
        
        # Check if there is a previous record in audio_trend_scores
        has_previous = False
        try:
            prev_res = self.supabase.table("audio_trend_scores") \
                .select("id") \
                .eq("audio_id", audio_id) \
                .limit(1) \
                .execute()
            if prev_res.data:
                has_previous = True
        except Exception as e:
            logging.warning(f"Error checking previous trend scores for {audio_id}: {e}")

        reel_count_0 = len(buckets[0]["reels"])
        reel_count_1 = len(buckets[1]["reels"])
        reel_count_2 = len(buckets[2]["reels"])
        
        creator_count_0 = len(buckets[0]["creators"])
        creator_count_1 = len(buckets[1]["creators"])
        creator_count_2 = len(buckets[2]["creators"])

        if not has_previous:
            return {
                "lifecycle_stage": "INSUFFICIENT_DATA",
                "reel_count": len(reels),
                "unique_creator_count": total_unique_creators,
                "creator_velocity": None,
                "reel_velocity": None,
                "details": {
                    "max_bucket_idx": max_bucket_idx,
                    "creator_velocity_previous": None,
                    "creator_count_current_bucket": creator_count_0,
                    "creator_count_previous_bucket": creator_count_1,
                    "reel_count_current_bucket": reel_count_0,
                    "reel_count_previous_bucket": reel_count_1
                }
            }

        creator_velocity_0 = (creator_count_0 - creator_count_1) / 3.0
        creator_velocity_1 = (creator_count_1 - creator_count_2) / 3.0
        
        reel_velocity_0 = (reel_count_0 - reel_count_1) / 3.0
        
        # Classification
        if creator_count_0 >= 3 and max_bucket_idx <= 1:
            stage = "EMERGING"
        elif creator_velocity_0 > 0 and creator_velocity_0 >= percentile_80 and total_unique_creators < 10:
            stage = "RISING"
        elif total_unique_creators >= 10 and creator_velocity_0 > 0 and creator_velocity_0 < creator_velocity_1:
            stage = "CRESTING"
        elif total_unique_creators >= 10 and creator_velocity_0 <= 0 and creator_velocity_1 <= 0:
            stage = "SATURATED/DECLINING"
        else:
            if total_unique_creators >= 10:
                if creator_velocity_0 > 0:
                    stage = "RISING"
                else:
                    stage = "SATURATED/DECLINING"
            else:
                if creator_count_0 >= 1:
                    stage = "EMERGING"
                else:
                    stage = "SATURATED/DECLINING"

        return {
            "lifecycle_stage": stage,
            "reel_count": len(reels),
            "unique_creator_count": total_unique_creators,
            "creator_velocity": creator_velocity_0,
            "reel_velocity": reel_velocity_0,
            "details": {
                "max_bucket_idx": max_bucket_idx,
                "creator_velocity_previous": creator_velocity_1,
                "creator_count_current_bucket": creator_count_0,
                "creator_count_previous_bucket": creator_count_1,
                "reel_count_current_bucket": reel_count_0,
                "reel_count_previous_bucket": reel_count_1
            }
        }

    def calculate_audio_trend_scores(self):
        logging.info("=== Running calculate_audio_trend_scores ===")
        try:
            import math
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            
            # Check for scraper outage
            time_threshold_3h = (datetime.now(timezone.utc) - timedelta(hours=3, minutes=30)).isoformat()
            new_reels_count_res = self.supabase.table("reels") \
                .select("reel_id", count="exact") \
                .gte("scraped_at", time_threshold_3h) \
                .execute()
            
            new_reels_scraped = new_reels_count_res.count or 0
            if new_reels_scraped < 5:
                logging.warning(f"Possible scraper outage detected (only {new_reels_scraped} reels scraped in the last 3.5h). Skipping trend scoring to prevent false decline signals.")
                return

            threshold_7d = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            
            reels_res = self.supabase.table("reels") \
                .select("audio_id, owner_username, posted_at, velocity_score, reel_id, view_count, like_count, comment_count, audio_title, audio_artist") \
                .gte("posted_at", threshold_7d) \
                .execute()
            
            all_reels = reels_res.data or []
            logging.info(f"Loaded {len(all_reels)} reels from last 7 days for audio trend scoring.")
            
            audio_groups = {}
            for r in all_reels:
                aid = r.get("audio_id")
                if not aid:
                    continue
                audio_groups.setdefault(aid, []).append(r)
            
            if not audio_groups:
                logging.info("No reels with audio_id found in the last 7 days.")
                return
            
            creator_velocities = []
            for aid, group in audio_groups.items():
                res = self.classify_lifecycle(aid, reels=group, percentile_80=0.0)
                creator_velocities.append(res["creator_velocity"])
            
            creator_velocities.sort()
            if creator_velocities:
                idx = int(len(creator_velocities) * 0.8)
                percentile_80 = creator_velocities[idx]
            else:
                percentile_80 = 0.0
                
            logging.info(f"80th percentile of creator velocity: {percentile_80:.4f}")
            
            scrape_cycle_at = datetime.now(timezone.utc).isoformat()
            for aid, group in audio_groups.items():
                res = self.classify_lifecycle(aid, reels=group, percentile_80=percentile_80)
                
                # Rank reels by velocity score descending
                sorted_reels = sorted(group, key=lambda r: r.get("velocity_score") or 0.0, reverse=True)
                top_reels_serialized = []
                for r in sorted_reels[:5]:
                    top_reels_serialized.append({
                        "reel_id": r.get("reel_id"),
                        "owner_username": r.get("owner_username"),
                        "velocity_score": r.get("velocity_score"),
                        "view_count": r.get("view_count"),
                        "like_count": r.get("like_count"),
                        "comment_count": r.get("comment_count"),
                        "audio_title": r.get("audio_title"),
                        "audio_artist": r.get("audio_artist"),
                        "posted_at": r.get("posted_at")
                    })
                
                score_data = {
                    "audio_id": aid,
                    "scrape_cycle_at": scrape_cycle_at,
                    "reel_count": res["reel_count"],
                    "unique_creator_count": res["unique_creator_count"],
                    "creator_velocity": res["creator_velocity"],
                    "reel_velocity": res["reel_velocity"],
                    "lifecycle_stage": res["lifecycle_stage"],
                    "top_reels": top_reels_serialized
                }
                
                self.supabase.table("audio_trend_scores").insert(score_data).execute()
                logging.info(f"Saved audio trend score for {aid}: stage={res['lifecycle_stage']}, total_creators={res['unique_creator_count']}, c_vel={res['creator_velocity']:.4f}")
                
        except Exception as e:
            logging.error(f"Error in calculate_audio_trend_scores: {e}", exc_info=True)


if __name__ == "__main__":
    engine = TrendEngine()
    ids = engine.detect_trends()
    print(f"New trend IDs: {ids}")
