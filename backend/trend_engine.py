import os
import re
import json
import time
import logging
import concurrent.futures
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import requests
from classification_rules import classify_niche, classify_content_tone
from language_detection import _detect_audio_language
from audio_title_normalize import normalize_audio_title
from trend_scoring import calculate_opportunity_score, calculate_trend_state, calculate_realistic_peaking_score, GLOBAL_SATURATION_THRESHOLD_REELS, INDIA_SATURATION_THRESHOLD_REELS
from dotenv import load_dotenv

# Defensive guard: hashtag pool names are internal routing labels, not real niches.
# If they leak into niche_tag, remap to "general" and log a warning.
_POOL_NAMES = {"INDIA_VERNACULAR", "GLOBAL_DISCOVERY", "INDIA_TRENDING", "GLOBAL_NICHES"}

def _sanitize_niche_tag(niche_tag: str) -> str:
    if niche_tag in _POOL_NAMES:
        logging.warning(f"Pool name '{niche_tag}' leaked to niche_tag — remapping to 'general'")
        return "general"
    return niche_tag
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
except Exception as _fh_err:
    # Log file unavailable (e.g. read-only filesystem on Vercel/serverless).
    print(f"trend_engine: WARNING: could not open log file, stdout only: {_fh_err}")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=log_handlers
)

def generate_local_fallback(trend):
    title = (trend.get("audio_title") or "Unknown Song").lower()
    is_dance = any(word in title for word in ["dance", "nach", "step", "groove", "taal", "bhangra", "dancecover"])
    use_count = trend.get("use_count") or 0
    age_hours = trend.get("age_hours") or 48

    # Dynamic scores based on actual trend data
    if use_count > 100000:
        saturation_score = 0.8
        confidence = 0.7
    elif use_count > 10000:
        saturation_score = 0.5
        confidence = 0.8
    else:
        saturation_score = 0.2
        confidence = 0.9

    # Recency boost — newer trends score higher
    if age_hours < 6:
        confidence = min(confidence + 0.05, 0.95)
        saturation_score = max(saturation_score - 0.1, 0.0)
    elif age_hours > 48:
        confidence = max(confidence - 0.1, 0.5)

    # Optimal posting hour based on current time of day
    from datetime import datetime, timezone
    current_hour_ist = (datetime.now(timezone.utc).hour + 5 + 30 // 60) % 24
    if current_hour_ist < 12:
        optimal_post_hour_ist = 20  # evening peak
    elif current_hour_ist < 17:
        optimal_post_hour_ist = 13  # afternoon
    else:
        optimal_post_hour_ist = 10  # next morning

    return {
        "content_type": None,
        "is_dance": is_dance,
        "niche_tag": trend.get("niche_tag") or "general",
        "needs_filming": is_dance,
        "edit_style": "fast_cuts" if is_dance else "slow_dissolve",
        "narrative_structure": "transformation" if is_dance else "none",
        "text_overlay_template": f"POV: Listening to {trend.get('audio_title') or 'this track'}",
        "language": None,
        "cultural_context": "celebration" if is_dance else "everyday",
        "ideal_content_description": f"Post aesthetic clips or photos matching the vibe of {trend.get('audio_title') or 'the song'}.",
        "camera_style": "static" if is_dance else "handheld",
        "window_hours_remaining": max(6, 72 - age_hours),
        "confidence": confidence,
        "saturation_score": saturation_score,
        "optimal_post_hour_ist": optimal_post_hour_ist,
        "best_platform_first": "instagram",
        "why_this_works": f"The track {trend.get('audio_title') or 'this track'} is currently driving high engagement on short-form feeds.",
        "audio_cue_second": 0,
        "format_transferable": True,
        "transfer_instructions": f"Adapt the aesthetic visual style of {trend.get('audio_title') or 'the song'} to show your niche products or behind-the-scenes processes.",
        "creator_fit_score": 0.62,
        "saturation_penalty": saturation_score,
        "hook_retention_score": round(0.5 + (confidence - 0.5) * 0.4, 2),
    }


def _serialize_llm_response(payload: dict | None) -> str | None:
    if payload is None:
        return None
    try:
        return json.dumps(payload, ensure_ascii=False)
    except Exception as _ser_err:
        logging.warning(f"_serialize_llm_response: failed to serialize LLM payload ({type(_ser_err).__name__}: {_ser_err}); returning None")
        return None


def _detect_regional_crossover(audio_language: str, reels: list[dict]) -> dict:
    """
    Returns crossover info if a regional language audio is spreading
    to a different language creator community.
    """
    if not audio_language or audio_language in {"en", "unknown"}:
        return {"is_crossover": False}

    REGIONAL_LANGS = {"ta", "te", "kn", "mr", "ml", "bn", "pa", "bho", "hne"}
    if audio_language not in REGIONAL_LANGS:
        return {"is_crossover": False}

    # Check if any reels using this audio come from Hindi/general pools
    hindi_pool_reels = [
        r for r in reels
        if r.get("source_hashtag_pool") in {"INDIA_TRENDING", "INDIA_VERNACULAR", "GLOBAL_DISCOVERY"}
        and any(
            tag in {"hindireels", "trendingindia", "reelsindia", "reelkarofeelkaro"}
            for tag in (r.get("hashtags") or [])
        )
    ]
    if len(hindi_pool_reels) >= 2:
        LANG_NAMES = {
            "ta": "Tamil", "te": "Telugu", "kn": "Kannada",
            "mr": "Marathi", "ml": "Malayalam", "bn": "Bengali", "pa": "Punjabi"
        }
        return {
            "is_crossover": True,
            "from_language": LANG_NAMES.get(audio_language, audio_language),
            "crossover_reel_count": len(hindi_pool_reels),
            "message": f"This {LANG_NAMES.get(audio_language, 'regional')} audio is spreading to Hindi creators"
        }
    return {"is_crossover": False}


def _trend_discovery_source(trend: dict) -> str:
    origin = (trend.get("trend_origin") or "").upper()
    is_cross = trend.get("is_cross_cultural", False)
    # Only truly non-Indian, non-unknown origins are "global"
    if is_cross and origin not in {"IN", "UNKNOWN", ""}:
        return "global"
    if origin not in {"", "IN", "UNKNOWN"} and not is_cross:
        return "global"  # Confirmed foreign (KR, US, BR etc.) without crossover
    if (trend.get("max_velocity") or 0) >= 3.0 or (trend.get("avg_velocity") or 0) >= 1.5:
        return "unexpected_candidate"
    return "regional"


def _select_trend_origin(reels: list[dict]) -> str:
    origins = [
        (r.get("trend_origin") or "").upper()
        for r in reels
        if (r.get("trend_origin") or "").strip()
    ]
    if not origins:
        return "unknown"

    counts: dict[str, int] = {}
    for origin in origins:
        if origin in {"", "UNKNOWN"}:
            continue
        counts[origin] = counts.get(origin, 0) + 1

    if not counts:
        return "unknown"

    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    top_origin, top_count = ranked[0]
    if len(ranked) > 1 and ranked[1][1] == top_count:
        return "unknown"
    return top_origin


def _trend_group_key(reel: dict) -> tuple[str, str] | None:
    title = (reel.get("audio_title") or "").strip()
    artist = (reel.get("audio_artist") or "").strip()
    if not title and not artist:
        return None
    if not title:
        return None
    if title.lower() == "original audio" or "original audio" in title.lower():
        # Completely ignore original audio for now, per user request.
        return None
    if not artist:
        artist = "Unknown Artist"
    canonical_title = normalize_audio_title(title)
    if not canonical_title:
        return None
    return (canonical_title, artist)


def _aggregate_content_tone(reels: list[dict]) -> str:
    tones = [r.get("content_tone") for r in reels if r.get("content_tone") and r.get("content_tone") != "unknown"]
    if not tones:
        return "unknown"
    counts = {}
    for t in tones:
        counts[t] = counts.get(t, 0) + 1
    ranked = sorted(counts.items(), key=lambda x: -x[1])
    return ranked[0][0]


def _classify_trend_type(title: str, artist: str, avg_velocity: float, max_velocity: float, 
                         audio_use_count: int, oldest_age_hours: float) -> dict:
    """
    Classify trend type for display differentiation.
    Returns classification and velocity pattern analysis.
    """
    title_lower = title.lower()
    artist_lower = artist.lower()
    
    # Classic artist detection
    classic_artists = [
        'ar rahman', 'arijit singh', 'shreya ghoshal', 'sonu nigam', 'lata mangeshkar',
        'kishore kumar', 'mohammed rafi', 'asha bhosle', 'udit narayan', 'kumar sanu',
        'pritam', 'vishal-shekhar', 'shankar-ehsaan-loy', 'anu malik', 'nadeem-shravan'
    ]
    is_classic_artist = any(ca in artist_lower for ca in classic_artists)
    
    # Determine trend classification
    classification = "new_viral"
    
    if is_classic_artist:
        if avg_velocity > 50000 and max_velocity > 100000:
            classification = "viral_revival"  # Classic artist with high velocity = revival
        elif audio_use_count > 1000000 and avg_velocity < 20000:
            classification = "evergreen_popular"  # High usage but low velocity = evergreen
        else:
            classification = "classic_hit"  # Classic artist with moderate metrics
    elif audio_use_count > 2000000 and avg_velocity < 10000:
        classification = "evergreen_popular"  # Very high usage, low velocity
    elif oldest_age_hours > 48 and avg_velocity < 30000:
        classification = "evergreen_popular"  # Old detection with low velocity
    
    # Determine velocity pattern
    velocity_pattern = "sudden_spike"
    
    if max_velocity / (avg_velocity + 1) > 3:
        velocity_pattern = "sudden_spike"  # Max velocity much higher than average = spike
    elif avg_velocity > 50000 and max_velocity / (avg_velocity + 1) < 1.5:
        velocity_pattern = "steady_popular"  # High consistent velocity
    elif avg_velocity > 20000:
        velocity_pattern = "gradual_growth"  # Moderate upward trend
    elif avg_velocity < 5000 and oldest_age_hours > 24:
        velocity_pattern = "declining"  # Low velocity, getting older
    
    return {
        "trend_classification": classification,
        "velocity_pattern": velocity_pattern,
        "is_evergreen": classification == "evergreen_popular"
    }

def _dominant_source_hashtag_pool(reels: list[dict]) -> str | None:
    pools = [r.get("source_hashtag_pool") for r in reels if r.get("source_hashtag_pool")]
    if not pools:
        return None
    return Counter(pools).most_common(1)[0][0]


def _get_news_search_query(audio_title: str, audio_artist: str, reels: list[dict]) -> str:
    title = audio_title or ""
    # Remove bracketed info (e.g. (From "Movie"))
    title_clean = re.sub(r'\(.*?\)', '', title)
    title_clean = re.sub(r'[^a-zA-Z0-9\s]', '', title_clean).strip()
    
    is_generic = any(w in title.lower() for w in ["original audio", "unknown", "song", "sound", "track", "music"]) or len(title_clean) < 3
    
    all_hashtags = set()
    for r in reels:
        tags = r.get("hashtags")
        if isinstance(tags, list):
            all_hashtags.update(tags)
            
    generic_tags = {"reels", "trending", "explore", "viral", "fyp", "instagram", "post", "reel", "trend", "love", "foryou", "foryoupage"}
    clean_tags = [t.lower() for t in all_hashtags if t.lower() not in generic_tags]
    
    if not is_generic:
        # Include artist if simple title might be too generic
        artist_clean = re.sub(r'[^a-zA-Z0-9\s]', '', audio_artist or "").strip()
        if artist_clean and len(title_clean) < 8:
            return f"{title_clean} {artist_clean}"
        return title_clean
    elif clean_tags:
        return clean_tags[0]
    else:
        return ""


def _evaluate_news_correlation(audio_title: str, audio_artist: str, reels: list[dict]) -> tuple[str, list | None]:
    query = _get_news_search_query(audio_title, audio_artist, reels)
    if not query:
        return "endogenous", None
        
    try:
        from news_client import NewsClient, check_keyword_overlap
        client = NewsClient()
        articles = client.get_trending_news(query)
    except Exception as e:
        logging.error(f"Error fetching trending news in TrendEngine: {e}")
        return "unknown", None
        
    if not articles:
        return "endogenous", None
        
    # Build trend keywords list
    title_clean = re.sub(r'[^a-zA-Z0-9\s]', '', audio_title or "").strip()
    keywords = title_clean.split()
    if audio_artist:
        keywords.extend(audio_artist.split())
    # Add top 3 hashtags
    all_hashtags = set()
    for r in reels:
        tags = r.get("hashtags")
        if isinstance(tags, list):
            all_hashtags.update(tags)
    generic_tags = {"reels", "trending", "explore", "viral", "fyp", "instagram", "post", "reel", "trend", "love", "foryou", "foryoupage"}
    clean_tags = [t.lower() for t in all_hashtags if t.lower() not in generic_tags]
    keywords.extend(clean_tags[:3])
    
    # Filter to words length >= 3
    keywords = [w.lower() for w in keywords if len(w) >= 3]
    
    matching_articles = []
    for art in articles:
        score = check_keyword_overlap(keywords, art)
        # If query word matches or overlap score is high
        if score >= 0.35 or any(w.lower() in art.get("title", "").lower() for w in query.split()):
            matching_articles.append(art)
            
    if not matching_articles:
        return "endogenous", None
        
    # Determine if exogenous vs mixed
    # Get oldest post time of reels
    oldest_post = None
    for r in reels:
        posted_str = r.get("posted_at")
        if posted_str:
            try:
                if posted_str.endswith("Z"):
                    posted_str = posted_str[:-1] + "+00:00"
                posted_dt = datetime.fromisoformat(posted_str)
                if oldest_post is None or posted_dt < oldest_post:
                    oldest_post = posted_dt
            except Exception as _dt_err:
                logging.debug(f"_detect_origin_signal: could not parse reel posted_at '{posted_str}': {_dt_err}")
                
    # Get oldest matching news pub date
    oldest_news = None
    for art in matching_articles:
        pub_str = art.get("publishedAt")
        if pub_str:
            try:
                if pub_str.endswith("Z"):
                    pub_str = pub_str[:-1] + "+00:00"
                pub_dt = datetime.fromisoformat(pub_str)
                if oldest_news is None or pub_dt < oldest_news:
                    oldest_news = pub_dt
            except Exception as _dt_err:
                logging.debug(f"_detect_origin_signal: could not parse article publishedAt '{pub_str}': {_dt_err}")
                
    if oldest_post and oldest_news:
        if oldest_post.tzinfo is None:
            oldest_post = oldest_post.replace(tzinfo=timezone.utc)
        if oldest_news.tzinfo is None:
            oldest_news = oldest_news.replace(tzinfo=timezone.utc)
            
        if oldest_post < oldest_news - timedelta(hours=12):
            return "mixed", matching_articles
            
    return "exogenous", matching_articles


@dataclass
class StageBudgetState:
    stage: str = "initializing"
    cutoff_reason: str | None = None




def generate_fallback_hook_text(trend: dict, hook_retention_score: float) -> str:
    """Generate hook advice when LLM is unavailable, based on score."""
    if hook_retention_score >= 0.8:
        return "This trend has strong early engagement. Start with the most surprising moment or visual hook in the first second."
    elif hook_retention_score >= 0.6:
        return "Good engagement potential. Open with a clear question or transformation that viewers will want to see through."
    elif hook_retention_score >= 0.4:
        return "Moderate engagement. Consider adding text overlay or a compelling statement in the first 2 seconds."
    else:
        return "Lower engagement signal. Test different opening patterns: POV, before/after, or direct address to camera."

def generate_fallback_content_description(trend: dict, creator_fit_score: float) -> str:
    """Generate content concept when LLM is unavailable, based on score."""
    category = trend.get("content_type", "general").lower()
    
    if creator_fit_score >= 0.8:
        return f"High fit for your niche. Create content that showcases {category} in your authentic style while matching the trend's rhythm."
    elif creator_fit_score >= 0.6:
        return f"Good fit potential. Adapt the {category} format to include elements specific to your audience and expertise."
    else:
        return f"Consider whether this {category} trend aligns with your content strategy. If posting, add your unique perspective to stand out."


# Fix #6: Extended dance word list includes Romanized Hindi/regional dance terms
_DANCE_WORDS = [
    "dance", "bhangra", "step", "groove", "naach", "nach", "naagin",
    "hookstep", "thumka", "giddha", "garba", "dandiya", "choreograph"
]

def classify_single_trend(trend):
    reels = trend["reels"]
    captions = [r.get("caption") for r in reels if r.get("caption")]
    all_hashtags = [tag for r in reels for tag in (r.get("hashtags") or [])]
    source_pool = _dominant_source_hashtag_pool(reels)

    # Fix #4: Always run keyword analysis — don't short-circuit on INDIA_TRENDING pool.
    # classify_niche() is updated to fall through for Indian pools instead of returning "general".
    niche_source = classify_niche(
        " ".join(captions),
        all_hashtags,
        source_hashtag_pool=source_pool,
        sample_size=len(reels),
    )
    trend["niche_tag"] = niche_source if niche_source else "general"
    trend["content_tone"] = _aggregate_content_tone(reels)
    trend["content_type"] = trend.get("content_type") or trend["niche_tag"]

    # Fix #6: Extended Romanized dance word detection
    title_lower = (trend["audio_title"] or "").lower()
    trend["is_dance"] = bool(any(word in title_lower for word in _DANCE_WORDS))

    trend["needs_filming"] = trend["is_dance"] or trend["content_tone"] in {"wholesome", "neutral"}
    trend["edit_style"] = "fast_cuts" if trend["is_dance"] else "slow_dissolve"
    trend["narrative_structure"] = "transformation" if trend["is_dance"] else "none"
    trend["text_overlay_template"] = None

    # Language detection via shared module (replaces inline _detect_language)
    _audio_text = f"{trend.get('audio_title', '')} {trend.get('audio_artist', '')}"
    _dominant_caption = max(captions, key=len) if captions else ""
    trend["language"] = _detect_audio_language(_audio_text, _dominant_caption)

    trend["cultural_context"] = "celebration" if trend["is_dance"] else "everyday"

    # Build a content-type-aware ideal description instead of the hardcoded generic sentence
    _niche = trend["niche_tag"]
    _NICHE_IDEAL_DESC = {
        "dance": "Choreography clips or hookstep videos matching the beat of the audio.",
        "comedy": "Relatable POV or reaction-style skits timed to the audio.",
        "food": "Aesthetic cooking or food reveal clips synced to the audio rhythm.",
        "fashion": "OOTD transitions or outfit reveals timed to the beat drop.",
        "fitness": "Workout montage or transformation clips set to this audio.",
        "travel": "Cinematic travel b-roll or destination reveals timed to the audio.",
        "beauty": "Makeup transformation or skincare routine clips synced to the audio.",
        "romance/relationship": "Couple moments or emotional photo-slideshows set to this audio.",
        "devotional": "Temple visits, puja moments, or devotional ambiance clips.",
        "narrative_edit": "Aesthetic photo/video edits with text overlays matching the audio energy.",
    }
    trend["ideal_content_description"] = _NICHE_IDEAL_DESC.get(
        _niche,
        f"Short creator clips that match the {_niche} niche rhythm and vibe of this audio."
    )

    trend["camera_style"] = "handheld" if trend["is_dance"] else "static"
    trend["window_hours_remaining"] = trend.get("window_hours_remaining") or 24
    trend["confidence"] = 0.75
    trend["saturation_score"] = min(1.0, max(0.0, trend.get("saturation_score") or 0.2))

    # Fix #5: Write top-3 reel captions as sample_captions for nightly LLM batch context
    sample_caps = [c for c in captions[:5] if c and len(c.strip()) > 10]
    trend["sample_captions"] = " | ".join(sample_caps[:3])[:500] if sample_caps else ""
    # Calculate dynamic optimal post time based on linked reels
    posted_hours = []
    for r in reels:
        posted_str = r.get("posted_at")
        if posted_str:
            try:
                if posted_str.endswith("Z"):
                    posted_str = posted_str[:-1] + "+00:00"
                from datetime import timedelta
                dt_posted = datetime.fromisoformat(posted_str)
                if dt_posted.tzinfo is None:
                    dt_posted = dt_posted.replace(tzinfo=timezone.utc)
                ist_dt = dt_posted + timedelta(hours=5.5)
                posted_hours.append(ist_dt.hour)
            except Exception:
                pass
    if posted_hours:
        from collections import Counter
        most_common_hour = Counter(posted_hours).most_common(1)[0][0]
        peak_slots = [8, 12, 15, 18, 20, 21]
        trend["optimal_post_hour_ist"] = peak_slots[min(range(len(peak_slots)), key=lambda i: abs(peak_slots[i] - most_common_hour))]
    else:
        # Use category-based default instead of arbitrary hash
        category = trend.get("content_type", "general").lower()
        if category in ["dance", "fitness"]:
            trend["optimal_post_hour_ist"] = 18
        elif category in ["food", "fashion"]:
            trend["optimal_post_hour_ist"] = 12
        else:
            trend["optimal_post_hour_ist"] = 20

    # Use local fallback defaults for LLM-enriched fields instead of leaving them
    # as 'pending' (which hides trends from the API until the nightly LLM batch runs).
    # The LLM batch can still upgrade these fields later by matching on status.
    trend.setdefault("why_this_works", f"The track {trend.get('audio_title') or 'this track'} is currently driving high engagement on short-form feeds.")
    trend.setdefault("audio_cue_second", 0)
    trend.setdefault("format_transferable", True)
    trend.setdefault("transfer_instructions", f"Adapt the visual style of {trend.get('audio_title') or 'the song'} to your niche.")
    trend["llm_classification_status"] = "skipped_local_fallback"
    
    # Custom classifiers for premium, targeted feeds
    try:
        from classification_rules import detect_voiceover, classify_vibe_tag
        all_hashtags = [tag for r in reels for tag in (r.get("hashtags") or [])]
        caption_combo = " ".join(captions)
        trend["is_voiceover"] = detect_voiceover(trend.get("audio_title"), caption_combo)
        trend["vibe_tag"] = classify_vibe_tag(trend["niche_tag"], caption_combo, all_hashtags)
        trend["saturation_count"] = 0 # Default starting count
        
        # Premium visual storyboards and CapCut/Instagram templates
        if trend["vibe_tag"] == "transition":
            trend["template_link"] = "https://www.capcut.com/t/Zs8R8888/"
            trend["visual_storyboard"] = [
                {"time": "0:00 - 0:02", "instruction": "Intro Hook: Set up a low-exposure, high-contrast shot with a bold overlay explaining the transition theme."},
                {"time": "0:02 - 0:03", "instruction": "Transition Point: Snap fingers, clap, or cover the camera lens exactly on the main beat drop."},
                {"time": "0:03 - 0:07", "instruction": "Reveal: Rapidly cut between 3 different high-quality angles showing the end result in slow motion."}
            ]
        elif trend["vibe_tag"] == "aesthetic":
            trend["template_link"] = "https://www.instagram.com/reels/templates/1234567/"
            trend["visual_storyboard"] = [
                {"time": "0:00 - 0:03", "instruction": "Calming Hook: A slow panning b-roll shot of your environment with warm lighting and minimal text overlay."},
                {"time": "0:03 - 0:06", "instruction": "Focus Action: Close-up detail shots showing a satisfying action (e.g. coffee pour, typing, sketch drawing)."},
                {"time": "0:06 - 0:10", "instruction": "Looping Outro: Pan out slowly to create a seamless loop that starts again with the intro panning."}
            ]
        elif trend["vibe_tag"] == "comedy":
            trend["template_link"] = "https://www.instagram.com/reels/audio/123456/"
            trend["visual_storyboard"] = [
                {"time": "0:00 - 0:04", "instruction": "Setup POV: Display a highly relatable text overlay showing a daily struggle, acting it out in a comical style."},
                {"time": "0:04 - 0:08", "instruction": "Punchline Reaction: Sync an exaggerated expression or funny reaction shot with the sound cue."}
            ]
        else:
            trend["template_link"] = "https://www.instagram.com/reels/templates/"
            trend["visual_storyboard"] = [
                {"time": "0:00 - 0:03", "instruction": "Visual Hook: Start with a bold text card presenting a question or value proposition."},
                {"time": "0:03 - 0:08", "instruction": "Demonstration: Steady b-roll of your activity matching the beat of the song."}
            ]
    except Exception as class_err:
        logging.error(f"Error during custom vibe classification: {class_err}")
        trend["is_voiceover"] = False
        trend["vibe_tag"] = "general"
        trend["saturation_count"] = 0
        trend["template_link"] = None
        trend["visual_storyboard"] = []
        
    return True


class TrendEngine:
    def __init__(self):
        load_dotenv()
        if not os.getenv("SUPABASE_URL"):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            backend_env = os.path.join(script_dir, ".env")
            if os.path.exists(backend_env):
                load_dotenv(backend_env)

        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        # Main trend detection is now deterministic; the nightly batch owns any
        # remaining LLM-backed enrichment.
        self.groq_key = os.getenv("GROQ_API_KEY")

        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self.last_run_stats = {
            "classification_success": 0,
            "classification_failed_429": 0,
            "pending_backfilled": 0,
        }

    def _calculate_creator_fit_score(
        self,
        title: str,
        artist: str,
        creator_count: int,
        avg_velocity: float,
        recent_6h_avg: float,
        recent_24h_avg: float,
        oldest_age_hours: float,
        niche_tag: str = "general",
        vibe_tag: str = "general",
    ) -> float:
        # Fix #10: Use niche_tag and vibe_tag in addition to title keywords
        # so trends with descriptive names (e.g. 'Teri Aankhon Mein') get correct classification.
        text = f"{title} {artist}".lower()

        # Dance: check extended word list + niche/vibe signals
        is_dance = (
            any(word in text for word in _DANCE_WORDS)
            or niche_tag == "dance"
            or vibe_tag in {"dance", "transition"}
        )
        # Visual: check title keywords + niche/vibe
        is_visual = (
            any(word in text for word in ["aesthetic", "cinematic", "vlog", "travel", "look", "style", "fashion"])
            or niche_tag in {"travel", "fashion", "beauty", "narrative_edit"}
            or vibe_tag == "aesthetic"
        )
        is_instructional = (
            any(word in text for word in ["tutorial", "how", "learn", "tips", "guide", "hack"])
            or niche_tag == "tech"
        )
        is_emotional = (
            any(word in text for word in ["love", "heart", "sad", "miss", "story", "pain", "broken"])
            or niche_tag == "romance/relationship"
            or vibe_tag == "romantic"
        )
        is_comedy = niche_tag == "comedy" or vibe_tag == "comedy"

        base = 0.45
        if is_dance:
            base += 0.18
        if is_visual:
            base += 0.14
        if is_instructional:
            base += 0.12
        if is_emotional:
            base += 0.08
        if is_comedy:
            base += 0.06
        momentum = min(0.25, (avg_velocity + recent_6h_avg + recent_24h_avg) / 30)
        breadth = min(0.15, creator_count * 0.03)
        freshness = max(0.0, 0.12 - (oldest_age_hours / 400))
        return max(0.0, min(1.0, base + momentum + breadth + freshness))

    def _calculate_saturation_penalty(self, creator_count: int, avg_velocity: float, max_velocity: float, oldest_age_hours: float) -> float:
        crowding = min(1.0, creator_count / 12)
        momentum_density = min(1.0, (avg_velocity * 0.5 + max_velocity * 0.3) / 8)
        age_pressure = min(1.0, oldest_age_hours / 72)
        return max(0.0, min(1.0, (crowding * 0.45) + (momentum_density * 0.35) + (age_pressure * 0.20)))

    def _estimate_hook_retention_score(self, reels: list[dict], title: str, recent_6h_avg: float, avg_velocity: float, max_velocity: float) -> float:
        engagement_rates = []
        for r in reels:
            views = r.get("view_count") or 0
            likes = r.get("like_count") or 0
            comments = r.get("comment_count") or 0
            if views > 0:
                er = (likes + comments) / views
                engagement_rates.append(er)
        if engagement_rates:
            avg_er = sum(engagement_rates) / len(engagement_rates)
            # base 0.40 + engagement rate * 4.0 (e.g. 5% ER -> 0.40 + 0.20 = 0.60, 10% ER -> 0.80)
            return min(0.95, max(0.35, 0.40 + avg_er * 4.0))

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
            # Check for scraper outage: skip only if 0 reels scraped in the last 6h.
            # Window extended from 3.5h to 6h to match the scheduled pipeline interval.
            time_threshold_3h = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
            new_reels_count_res = self.supabase.table("reels") \
                .select("reel_id", count="exact") \
                .gte("scraped_at", time_threshold_3h) \
                .execute()
            
            new_reels_scraped = new_reels_count_res.count or 0
            if new_reels_scraped < 1:
                logging.warning(f"Possible scraper outage detected (0 reels scraped in the last 6h). Proceeding anyway for manual backfill.")
                # return []

            # STEP 1: Load recent high-velocity reels (last 48h)
            # Note on filter semantics: PostgREST neq maps to SQL != which EXCLUDES NULLs.
            # audio_backfill_status is NULL for the majority of valid reels (those whose audio
            # was present at scrape time and never needed backfilling). Using neq("audio_backfill_status",
            # "unrecoverable") would silently drop all of them. The correct intent is SQL's
            # IS DISTINCT FROM — include rows where status is NULL or any non-unrecoverable value.
            # Implemented via PostgREST or_ filter: (status.is.null,status.neq.unrecoverable)
            time_threshold_48h = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
            time_threshold_6h = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()

            reels = []
            offset = 0
            _PAGE_SIZE = 1000
            while True:
                reels_res = self.supabase.table("reels") \
                    .select("*") \
                    .gt("velocity_score", 0.3) \
                    .gte("created_at", time_threshold_48h) \
                    .or_("audio_backfill_status.is.null,audio_backfill_status.neq.unrecoverable") \
                    .order("created_at", desc=True) \
                    .range(offset, offset + _PAGE_SIZE - 1) \
                    .execute()
                data = reels_res.data or []
                reels.extend(data)
                if len(data) < _PAGE_SIZE:
                    break
                offset += _PAGE_SIZE
            logging.info(f"Loaded {len(reels)} reels for evaluation")

            # STEP 2: Group by audio
            audio_groups = {}
            special_cased_original_audio = 0
            excluded_unidentifiable = 0
            proceeded_to_grouping = 0
            for reel in reels:
                group_key = _trend_group_key(reel)
                if group_key is None:
                    excluded_unidentifiable += 1
                    continue
                if reel.get("is_original_audio") is True:
                    special_cased_original_audio += 1
                proceeded_to_grouping += 1
                if group_key not in audio_groups:
                    audio_groups[group_key] = []
                audio_groups[group_key].append(reel)
            logging.info(
                "Audio grouping: special-cased %s original-audio reels and excluded %s unidentifiable reels. "
                "%s reels proceeded to grouping. Grouped into %s unique audio combinations.",
                special_cased_original_audio,
                excluded_unidentifiable,
                proceeded_to_grouping,
                len(audio_groups),
            )

            # STEP 3: Fetch ALL existing trends for dedup (all statuses).
            # On re-detection, update existing row in-place instead of inserting
            # a duplicate. Status uses never-downgrade rule (rising > emerging > peaked > expired).
            STATUS_PRIORITY = {"expired": 0, "peaked": 1, "emerging": 2, "rising": 3}
            all_trends_res = self.supabase.table("trends") \
                .select("audio_title, audio_artist, audio_id, status, id") \
                .execute()
            existing_named = {
                (normalize_audio_title(t.get("audio_title", "")).strip(), t.get("audio_artist", "").strip())
                for t in (all_trends_res.data or [])
                if t.get("audio_title")
                and (t.get("audio_title") or "").strip().lower() != "original audio"
            }
            existing_by_audio_id = {
                (t.get("audio_id") or "").strip(): t
                for t in (all_trends_res.data or [])
                if t.get("audio_id")
            }

            # STEP 4: Evaluate each audio group
            confirmed = []

            # Quality gate constants
            # 501034 is a known sentinel/fallback value used by the scraper when the
            # real audio_use_count is unavailable. It must NOT be treated as a real signal.
            SENTINEL_USE_COUNT = 501034

            for (title, artist), group_reels in audio_groups.items():
                representative_audio_id = next((r.get("audio_id") for r in group_reels if r.get("audio_id")), None)

                # ── Original Audio exclusion ──────────────────────────────────────────────
                # Exclude ALL original-audio from trend detection entirely.
                # Without fingerprinting, we can't match across posts reliably.
                # Surface original audio via the format/pattern track (when built).
                is_original_audio = (
                    title.lower() in ("original audio", "original sound", "")
                    or title.lower().startswith("original_audio::")
                    or any(r.get("is_original_audio") is True for r in group_reels)
                )

                # Check for TikTok migration breakout footprint:
                # 1. High use_count (>= 50)
                # 2. Or high view-to-follower ratio on the audio artist (> 15x with 50k+ views)
                max_use_cnt = max((r.get("audio_use_count") or 0 for r in group_reels), default=0)
                artist_followers = max((r.get("ownerFollowersCount") or 0 for r in group_reels), default=0)
                max_views = max((r.get("view_count") or 0 for r in group_reels), default=0)

                ratio = (max_views / max(artist_followers, 100)) if artist_followers > 0 else 0.0
                is_crossplatform_breakout = (ratio >= 15.0 and max_views >= 50000) or (max_use_cnt >= 50)

                if is_original_audio and not is_crossplatform_breakout:
                    logging.debug(
                        f"Original-audio excluded from trend detection (no breakout signal): '{title}' | {artist} — "
                        f"{len(group_reels)} reels"
                    )
                    continue
                # ────────────────────────────────────────────────────────────────────────

                # ── Sentinel use-count gate ──────────────────────────────────────────────
                # Scraper emits 501034 when real use_count is unavailable. Groups that
                # only have the sentinel value and fewer than 5 reels are too weak to trust.
                max_raw_use_count = max((r.get("audio_use_count") or 0 for r in group_reels), default=0)
                if max_raw_use_count == SENTINEL_USE_COUNT and len(group_reels) < 5:
                    logging.debug(
                        f"Sentinel use-count gate: skipping '{title}' | {artist} — "
                        f"use_count={max_raw_use_count} (sentinel) with only {len(group_reels)} reels"
                    )
                    continue
                # ────────────────────────────────────────────────────────────────────────

                # Check for existing trend by audio_id (primary) or title+artist (fallback)
                existing_match = None
                if representative_audio_id and representative_audio_id.strip() in existing_by_audio_id:
                    existing_match = existing_by_audio_id[representative_audio_id.strip()]
                elif title.lower() != "original audio" and (title, artist) in existing_named:
                    # Title+artist match without audio_id match — find by normalized name
                    for t in (all_trends_res.data or []):
                        if (normalize_audio_title(t.get("audio_title", "")).strip(), t.get("audio_artist", "").strip()) == (title, artist):
                            existing_match = t
                            break

                if existing_match:
                    # Update-in-place: never-downgrade status on re-detection.
                    # Only status is updated here — velocity/metrics are owned by
                    # trend_refresher.py via snapshot logic. No last_detected_at
                    # column exists; consider adding via migration for staleness tracking.
                    old_status = existing_match.get("status", "emerging")
                    new_detected_status = "emerging"
                    old_priority = STATUS_PRIORITY.get(old_status, 0)
                    new_priority = STATUS_PRIORITY.get(new_detected_status, 0)
                    final_status = old_status if old_priority >= new_priority else new_detected_status
                    if final_status != old_status:
                        update_payload = {"status": final_status}
                        if final_status in ("emerging", "rising"):
                            update_payload["window_hours_remaining"] = 48
                            
                        try:
                            self.supabase.table("trends") \
                                .update(update_payload) \
                                .eq("id", existing_match["id"]) \
                                .execute()
                            logging.info(
                                f"Updated existing trend '{title}' (id={existing_match['id']}): "
                                f"status {old_status} -> {final_status}"
                            )
                        except Exception as update_err:
                            logging.warning(f"Failed to update existing trend '{title}': {update_err}")
                    continue

                usernames = {r.get("owner_username") for r in group_reels if r.get("owner_username")}
                creator_count = len(usernames)
                velocities = [r.get("velocity_score", 0.0) for r in group_reels]
                avg_velocity = sum(velocities) / len(velocities) if velocities else 0.0
                max_velocity = max(velocities) if velocities else 0.0

                all_reels_for_audio_res = self.supabase.table("reels").select("*").eq("audio_id", representative_audio_id).gte("created_at", time_threshold_48h).execute()
                all_reels = all_reels_for_audio_res.data
                high_velocity_reels = [r for r in all_reels if r.get("velocity_score", 0) > 0.3]
                
                # We need at least 3 recently scraped high-velocity reels to confirm a trend
                if len(high_velocity_reels) < 3:
                    logging.debug(f"Audio {title} failed 3-reel threshold check (found {len(high_velocity_reels)} recent high-velocity reels)")
                    continue

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
                    except Exception as _dt_err:
                        logging.debug(f"detect_trends: could not parse reel created_at '{created_str}': {_dt_err}")

                recent_6h_avg = sum(recent_6h_velocities) / len(recent_6h_velocities) if recent_6h_velocities else 0.0
                recent_24h_avg = sum(recent_24h_velocities) / len(recent_24h_velocities) if recent_24h_velocities else avg_velocity
                recency_bonus = max(0.5, 1.5 - (oldest_age_hours / 48)) if oldest_age_hours else 1.0
                creator_bonus = 1.0 + min(0.6, creator_count * 0.08)
                
                # Creator Outlier Boost: 20% boost per creator outlier breakout, capped at 1.5x
                outlier_count = sum(1 for r in group_reels if r.get("is_creator_outlier") is True)
                outlier_boost = min(1.5, 1.0 + (outlier_count * 0.20))
                
                trend_score = ((avg_velocity * 0.45) + (max_velocity * 0.2) + (recent_6h_avg * 0.25) + (recent_24h_avg * 0.1)) * creator_bonus * recency_bonus * outlier_boost

                # Creator fit looks at what the trend is actually good for, not just raw momentum.
                # Fix #10: niche_tag and vibe_tag are derived from classify_single_trend() later;
                # use a quick keyword pass here since classify hasn't run yet for this candidate.
                _quick_niche = classify_niche(
                    " ".join(r.get("caption", "") for r in group_reels if r.get("caption")),
                    [tag for r in group_reels for tag in (r.get("hashtags") or [])],
                    source_hashtag_pool=_dominant_source_hashtag_pool(group_reels),
                    sample_size=len(group_reels),
                )
                creator_fit_score = self._calculate_creator_fit_score(
                    title=title,
                    artist=artist,
                    creator_count=creator_count,
                    avg_velocity=avg_velocity,
                    recent_6h_avg=recent_6h_avg,
                    recent_24h_avg=recent_24h_avg,
                    oldest_age_hours=oldest_age_hours,
                    niche_tag=_quick_niche or "general",
                    vibe_tag="general",  # vibe_tag computed after classify_single_trend runs
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
                    reels=group_reels,
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

                # Calculate creator velocity based on buckets: creators in last 3h vs 3-6h
                now_utc = datetime.now(timezone.utc)
                creators_0 = set()
                creators_1 = set()
                for r in group_reels:
                    posted_str = r.get("posted_at")
                    if not posted_str:
                        continue
                    try:
                        if posted_str.endswith("Z"):
                            posted_str = posted_str[:-1] + "+00:00"
                        posted_dt = datetime.fromisoformat(posted_str)
                        if posted_dt.tzinfo is None:
                            posted_dt = posted_dt.replace(tzinfo=timezone.utc)
                        diff_seconds = (now_utc - posted_dt).total_seconds()
                        if diff_seconds < 0:
                            diff_seconds = 0
                        username = r.get("owner_username")
                        if username:
                            if diff_seconds <= 3.0 * 3600.0:
                                creators_0.add(username)
                            elif diff_seconds <= 6.0 * 3600.0:
                                creators_1.add(username)
                    except Exception as _dt_err:
                        logging.debug(f"detect_trends: could not parse reel posted_at for creator velocity: {_dt_err}")

                creator_velocity = (len(creators_0) - len(creators_1)) / 3.0

                # Determine initial status using grounded Option B triggers
                # Grounded thresholds calibrated on 2026-07-29 against N=108 distinct audio_id values (p50 = 153k, p75 = 798k).
                # RISING_USE_THRESHOLD lowered from 800k to 500k on 2026-08-27 so trends actually graduate
                # from emerging → rising. The 800k bar was so high almost no Indian audio trends crossed it.
                EMERGING_USE_THRESHOLD = 150000
                RISING_USE_THRESHOLD = 500000

                # Engagement Quality Gate: At least one reel in the candidate group must have like_count >= 10.
                has_valid_engagement = any((r.get("like_count") or 0) >= 10 for r in group_reels)
                if not has_valid_engagement:
                    continue

                max_use_count = max((r.get("audio_use_count") or 0 for r in group_reels), default=0)

                has_strong_official_velocity = False
                if representative_audio_id:
                    try:
                        official_res = self.supabase.table("audio_official_counts") \
                            .select("official_count_velocity") \
                            .eq("audio_id", representative_audio_id) \
                            .order("checked_at", desc=True) \
                            .limit(1) \
                            .execute()
                        if official_res.data:
                            vel = official_res.data[0].get("official_count_velocity")
                            if vel and vel > 100.0:
                                has_strong_official_velocity = True
                    except Exception as _auc_err:
                        logging.debug(f"detect_trends: could not fetch official audio velocity for audio_id={representative_audio_id}: {_auc_err}")

                initial_status = None
                promotion_trigger = None

                if max_use_count >= RISING_USE_THRESHOLD:
                    initial_status = "rising"
                    promotion_trigger = "audio_use_count_rising"
                elif creator_count >= 3 and creator_velocity > 0:
                    # TODO: Investigate why creator_count_rising fired 0 times in backtests.
                    # Verify if condition is too strict or if creator velocity metrics need tuning.
                    initial_status = "rising"
                    promotion_trigger = "creator_count_rising"
                elif max_use_count >= EMERGING_USE_THRESHOLD:
                    initial_status = "emerging"
                    promotion_trigger = "audio_use_count_emerging"
                elif creator_count >= 2 and len(group_reels) >= 2:
                    initial_status = "emerging"
                    promotion_trigger = "creator_count_emerging"

                if not initial_status:
                    continue

                # Removed Hard minimum 2-reel gate to fix the chicken-and-egg bug.
                # If an audio has massive use_count (e.g. 50,000+) but we only scraped 1 reel using it,
                # we MUST track it so the scraper knows to look for it. Blocking it here creates
                # a loop where we never track it because we don't have enough reels, and we don't 
                # get more reels because we aren't tracking it.

                # Validate time window: all reels within 48h of each other
                posted_times = []
                for r in group_reels:
                    posted_str = r.get("posted_at")
                    if posted_str:
                        if posted_str.endswith("Z"):
                            posted_str = posted_str[:-1] + "+00:00"
                        try:
                            posted_times.append(datetime.fromisoformat(posted_str))
                        except Exception as _dt_err:
                            logging.debug(f"detect_trends: could not parse reel posted_at for time-window check: {_dt_err}")

                if posted_times:
                    if (max(posted_times) - min(posted_times)) > timedelta(hours=72):
                        continue

                # Clean up original_audio compound key for display — store human-readable title
                display_title = title
                if title.lower().startswith("original_audio::"):
                    display_title = "Original Audio"

                confirmed.append({
                    "audio_title": display_title,
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
                    "promotion_trigger": promotion_trigger,
                    "discovery_source": _trend_discovery_source({
                        "is_cross_cultural": any(r.get("is_cross_cultural") for r in group_reels),
                        "trend_origin": max(
                            (r.get("trend_origin") for r in group_reels if r.get("trend_origin")),
                            default="IN",
                        ),
                        "max_velocity": max_velocity,
                        "avg_velocity": avg_velocity,
                    }),
                })

            logging.info(f"Confirmed {len(confirmed)} new trends for Groq classification")

            # Keep all confirmed candidates. The old "top 7" slice silently dropped the
            # remainder with no queue or retry, so it was discarding qualified trends.
            confirmed = sorted(confirmed, key=lambda x: (x["composite_score"], x["trend_score"], x["avg_velocity"]), reverse=True)
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

            # Classify top 7 trends sequentially with stagger/delay to respect rate limits
            llm_classification_failures = 0
            for idx, trend in enumerate(confirmed):
                if idx > 0:
                    # 12s stagger: at 800 TPM/call and 2 keys, this gives token buckets more reset time
                    stagger_delay = float(os.getenv("TREND_CLASSIFICATION_STAGGER_DELAY", "12.0"))
                    logging.info(f"Rate limiting: sleeping {stagger_delay}s before next Groq classification...")
                    time.sleep(stagger_delay)
                success = classify_single_trend(trend)
                if not success:
                    llm_classification_failures += 1

            logging.info(
                f"Deterministic trend classification completed for {len(confirmed) - llm_classification_failures}/{len(confirmed)} trends."
            )

            # ── STEP 7: Save to Supabase ───────────────────────────────────────
            for trend in confirmed:
                confidence = trend.get("confidence", 0.0)
                if isinstance(confidence, str):
                    try:
                        confidence = float(confidence)
                    except Exception as _conf_err:
                        logging.warning(f"detect_trends: could not parse confidence string for '{trend.get('audio_title')}': {_conf_err}; defaulting to 0.0")
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
                global_sat = round(min(100.0, (audio_use_count / GLOBAL_SATURATION_THRESHOLD_REELS) * 100), 1)
                # India saturation: proportional to global saturation based on Indian creator ratio.
                # Raw count approach (india_use_count / 500) permanently yields ~0% because
                # max india_use_count across all audio is ~13. Instead, scale global saturation
                # by the fraction of scraped reels from Indian creators.
                if len(group_reels) > 0 and india_use_count > 0:
                    india_ratio = india_use_count / len(group_reels)
                    india_sat = round(min(100.0, global_sat * india_ratio * 2), 1)
                else:
                    india_sat = 0.0

                # Fix #9: Window hours — saturation-based baseline adjusted by velocity direction.
                # A trend with falling velocity gets 30% fewer hours regardless of saturation.
                if global_sat >= 90:
                    window_h = 0
                elif global_sat >= 75:
                    window_h = 8
                elif global_sat >= 50:
                    window_h = 16
                elif global_sat >= 20:
                    window_h = 24
                else:
                    window_h = 48

                # Velocity direction correction: if recent 6h avg is declining vs overall avg,
                # shrink the window to reflect faster-than-expected saturation.
                _avg_vel = trend.get("avg_velocity") or 1.0
                _recent_vel = trend.get("recent_6h_avg") or _avg_vel
                if window_h > 0 and _recent_vel < _avg_vel * 0.7:
                    window_h = max(8, int(window_h * 0.7))  # 30% reduction, floor at 8h

                opportunity_score = calculate_opportunity_score(
                    india_saturation_pct=india_sat,
                    window_hours_remaining=window_h,
                    confidence=confidence,
                )
                # Calculate unified trend state
                trend_state = calculate_trend_state(
                    velocity_avg=trend["avg_velocity"],
                    global_saturation_pct=global_sat,
                    india_saturation_pct=india_sat,
                    window_hours_remaining=window_h,
                    audio_use_count=audio_use_count,
                    confidence=confidence,
                    max_velocity=trend["max_velocity"],
                    discovery_source=trend.get("discovery_source", "regional"),
                )


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
                # trend_origin – majority vote across reels, with ties falling back to IN or unknown
                trend_origin = _select_trend_origin(group_reels)
                is_cross_cultural = any(r.get("is_cross_cultural") for r in group_reels)

                # Aggregate semantic niches from linked reels
                niche_counts = {}
                for r in group_reels:
                    r_niches = r.get("semantic_niches") or []
                    for n in r_niches:
                        niche_counts[n] = niche_counts.get(n, 0) + 1
                sorted_niches = [k for k, v in sorted(niche_counts.items(), key=lambda x: x[1], reverse=True) if k != "general"]
                if not sorted_niches:
                    sorted_niches = ["general"]

                # Evaluate news correlation
                virality_type, news_matches = _evaluate_news_correlation(
                    trend["audio_title"], trend["audio_artist"], group_reels
                )
                
                # Aggregate content tone, but never leave the trend row unknown.
                content_tone = _aggregate_content_tone(group_reels)
                if content_tone == "unknown":
                    caption_fallback = " ".join((r.get("caption") or "") for r in group_reels if r.get("caption"))
                    hashtag_fallback = [tag for r in group_reels for tag in (r.get("hashtags") or [])]
                    content_tone = classify_content_tone(caption_fallback, hashtag_fallback)

                # Regional crossover detection
                crossover_info = _detect_regional_crossover(trend.get("language") or "en", group_reels)
                
                # Trend classification for display differentiation
                trend_classification = _classify_trend_type(
                    title=trend["audio_title"],
                    artist=trend["audio_artist"],
                    avg_velocity=trend["avg_velocity"],
                    max_velocity=trend["max_velocity"],
                    audio_use_count=audio_use_count,
                    oldest_age_hours=oldest_age_hours
                )

                trend_data = {
                    "audio_title": trend["audio_title"],
                    "audio_artist": trend["audio_artist"],
                    "audio_id": audio_id,
                    "audio_use_count": audio_use_count,
                    "platform": "instagram",
                    "trend_type": trend.get("trend_type", "trend"),
                    "semantic_niches": sorted_niches,
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
                    "status": trend_state.lifecycle.value,
                    "saturation_score": trend.get("saturation_score", 0.2),
                    "global_saturation_pct": global_sat,
                    "india_saturation_pct": india_sat,
                    "niche_tag": _sanitize_niche_tag(niche_tag),
                    "hook_brief": hook_brief,
                    "format_patterns": format_patterns,
                    "trend_origin": trend_origin,
                    "is_cross_cultural": is_cross_cultural,
                    "discovery_source": trend.get("discovery_source", "regional"),
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
                    "promotion_reason": trend.get("promotion_trigger"),
                    "llm_classification_status": trend.get("llm_classification_status", "pending"),
                    "raw_llm_response": trend.get("raw_llm_response"),
                    "llm_classified_at": trend.get("llm_classified_at"),
                    "llm_retry_count": trend.get("llm_retry_count", 0),
                    "has_creator_outlier": any(r.get("is_creator_outlier") is True for r in group_reels),
                    "virality_type": virality_type,
                    "exogenous_correlation": news_matches,
                    "content_tone": content_tone,
                    "first_detected_at": datetime.now(timezone.utc).isoformat(),
                    # Trend classification for display differentiation
                    "trend_classification": trend_classification["trend_classification"],
                    "velocity_pattern": trend_classification["velocity_pattern"],
                    "is_evergreen": trend_classification["is_evergreen"],
                    "trend_age_hours": int(oldest_age_hours) if oldest_age_hours else 0,
                    # Crossover Detection Integration
                    "is_regional_crossover": crossover_info.get("is_crossover", False),
                    "crossover_from_language": crossover_info.get("from_language"),
                    "crossover_message": crossover_info.get("message"),
                    "opportunity_score": opportunity_score,
                    "niche_fit_score": float(trend.get("creator_fit_score") or 0.6) * 100.0,
                    "peaking_score": 0.0,  # Initial value, will be recalculated by trend_refresher when snapshots exist
                    "template_link": trend.get("template_link"),
                    "visual_storyboard": trend.get("visual_storyboard"),
                    "vibe_tag": trend.get("vibe_tag", "general"),
                    "is_voiceover": trend.get("is_voiceover", False),
                    "saturation_count": trend.get("saturation_count", 0),
                    # Fix #5: sample_captions written at detection time for nightly LLM batch context
                    "sample_captions": trend.get("sample_captions", ""),
                }

                try:
                    res = self.supabase.table("trends").insert(trend_data).execute()
                    if res.data:
                        tid = res.data[0].get("id")
                        new_trend_ids.append(tid)
                        logging.info(f"Saved '{trend['audio_title']}' as {trend.get('initial_status')} (id={tid})")
                        
                        # Try to calculate initial peaking score if we have snapshot data
                        # This is for existing trends that might already have snapshots
                        try:
                            initial_snapshots_res = self.supabase.table('trend_snapshots') \
                                .select('velocity_avg, captured_at') \
                                .eq('trend_id', tid) \
                                .order('captured_at', desc=True) \
                                .limit(10) \
                                .execute()
                            
                            initial_snapshots = initial_snapshots_res.data or []
                            if initial_snapshots and calculate_realistic_peaking_score:
                                initial_peaking = calculate_realistic_peaking_score(trend_data, initial_snapshots)
                                self.supabase.table("trends").update({"peaking_score": initial_peaking}).eq("id", tid).execute()
                                logging.info(f"Set initial peaking_score={initial_peaking} for trend {tid}")
                        except Exception as peaking_err:
                            logging.warning(f"Could not set initial peaking_score for trend {tid}: {peaking_err}")
                            
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

    def calculate_audio_trend_scores(self, budget_state: StageBudgetState | None = None):
        logging.info("=== Running calculate_audio_trend_scores ===")
        try:
            import math
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            started_at = time.monotonic()
            max_seconds = float(os.getenv("AUDIO_TREND_SCORE_MAX_SECONDS", "180.0"))
            if budget_state is None:
                budget_state = StageBudgetState(stage="audio_scoring")
            
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
                try:
                    res = self.classify_lifecycle(aid, reels=group, percentile_80=0.0)
                    v = res.get("creator_velocity")
                    if v is not None:
                        creator_velocities.append(v)
                except Exception as e:
                    logging.error(f"Error classifying lifecycle for percentile calculation on audio_id {aid}: {e}", exc_info=True)
            
            creator_velocities.sort()
            if creator_velocities:
                idx = int(len(creator_velocities) * 0.8)
                percentile_80 = creator_velocities[idx]
            else:
                percentile_80 = 0.0
                
            logging.info(f"80th percentile of creator velocity: {percentile_80:.4f}")
            
            scrape_cycle_at = datetime.now(timezone.utc).isoformat()
            for aid, group in audio_groups.items():
                if time.monotonic() - started_at >= max_seconds:
                    budget_state.cutoff_reason = f"audio scoring stopped at {max_seconds:.0f}s cutoff"
                    logging.warning(
                        f"Audio trend scoring stopped early at {max_seconds:.0f}s cutoff."
                    )
                    logging.warning(
                        "Stopping audio trend scoring early to stay within the pipeline time budget."
                    )
                    break
                try:
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
                    c_vel_val = res.get("creator_velocity")
                    c_vel_str = f"{c_vel_val:.4f}" if c_vel_val is not None else "None"
                    logging.info(f"Saved audio trend score for {aid}: stage={res['lifecycle_stage']}, total_creators={res['unique_creator_count']}, c_vel={c_vel_str}")
                except Exception as e:
                    logging.error(f"Error processing audio trend score for audio_id {aid}: {e}", exc_info=True)
                
        except Exception as e:
            logging.error(f"Critical error in calculate_audio_trend_scores: {e}", exc_info=True)

if __name__ == "__main__":
    engine = TrendEngine()
    ids = engine.detect_trends()
    print(f"New trend IDs: {ids}")

