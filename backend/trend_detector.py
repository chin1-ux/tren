"""
Trend Detector v1 — Baby trend detection engine.

Detects trends BEFORE they reach 'emerging' status by:
1. Scanning recent reels for velocity spikes (12x baseline)
2. Detecting cross-platform migration signals (TikTok -> Instagram)
3. Classifying trends by type (audio/format/meme/event/cross-platform)
4. Scoring saturation and estimating time windows

Lifecycle: baby -> emerging -> rising -> peaked -> expired
"""
import os
import sys
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    try:
        import codecs
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except Exception:
        pass

logger = logging.getLogger(__name__)

# Import Supabase client
try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None

# Configuration
BABY_VELOCITY_MULTIPLIER = 12.0  # A reel must be 12x its creator's baseline
BABY_MIN_CREATORS = 1            # Minimum unique creators to flag
BABY_MIN_REELS = 2               # Minimum reels in the group
BABY_CONFIDENCE_THRESHOLD = 0.5  # Minimum confidence to store
SATURATION_LOW = 0.2             # Below this = early window
SATURATION_MID = 0.5             # Below this = moderate window
SATURATION_HIGH = 0.8            # Below this = high saturation

# TikTok migration prediction times (days) from origin country to India
MIGRATION_TIMES = {
    "BR": 10,   # Brazilian sounds
    "MX": 8,    # Mexican sounds
    "ES": 8,    # Spanish sounds
    "US": 5,    # US sounds
    "GB": 5,    # UK sounds
    "FR": 7,    # French sounds
    "DE": 7,    # German sounds
    "JP": 14,   # Japanese sounds
    "KR": 7,    # Korean sounds
    "TR": 10,   # Turkish sounds
    "AR": 9,    # Argentine sounds
    "PT": 9,    # Portuguese sounds
    "IT": 8,    # Italian sounds
}

# Niche classification keywords
NICHE_KEYWORDS = {
    "dance": ["dance", "choreography", "moves", "groove", "step", "hiphop", "hip-hop", "bhangra", "garba"],
    "food": ["recipe", "cooking", "food", "kitchen", "chef", "meal", "snack", "street food", "chai", "biryani"],
    "fashion": ["outfit", "fashion", "style", "ootd", "haul", "thrift", "ethnic", "saree", "lehenga"],
    "beauty": ["makeup", "skincare", "beauty", "tutorial", "grwm", "routine", "glow"],
    "comedy": ["comedy", "funny", "skit", "pov", "relatable", "meme", "joke"],
    "fitness": ["workout", "gym", "fitness", "yoga", "exercise", "health", "diet"],
    "tech": ["tech", "gadget", "review", "unboxing", "phone", "laptop", "ai"],
    "travel": ["travel", "vlog", "trip", "explore", "adventure", "backpacking"],
    "education": ["learn", "tips", "howto", "tutorial", "education", "facts", "science"],
    "lifestyle": ["day in life", "morning routine", "room tour", "aesthetic", "vlog"],
}

# Trend type keywords
TREND_TYPE_KEYWORDS = {
    "audio": ["audio", "song", "music", "sound", "remix", " mashup"],
    "format": ["transition", "before after", "glow up", "glowup", "reveal", " transformation"],
    "meme": ["meme", "trending", "viral", "challenge", "trend"],
    "event": ["festival", "diwali", "holi", "christmas", "new year", "independence day", "republic day"],
}


def _get_supabase_client() -> Optional[Client]:
    """Get Supabase client from environment."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key or not create_client:
        return None
    try:
        return create_client(url, key)
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        return None


def _classify_niche(audio_title: str, audio_artist: str, captions: List[str] = None) -> str:
    """Classify a trend into a niche based on audio title, artist, and captions."""
    text = f"{audio_title} {audio_artist}".lower()
    if captions:
        text += " " + " ".join(captions).lower()

    scores = {}
    for niche, keywords in NICHE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[niche] = score

    if scores:
        return max(scores, key=scores.get)
    return "lifestyle"  # default


def _classify_trend_type(audio_title: str, captions: List[str] = None) -> str:
    """Classify the trend type (audio, format, meme, event)."""
    text = audio_title.lower()
    if captions:
        text += " " + " ".join(captions).lower()

    for trend_type, keywords in TREND_TYPE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return trend_type

    return "audio"  # default — most Instagram trends are audio-driven


def _detect_language(text: str) -> str:
    """Detect language from text using Unicode script ranges."""
    if not text:
        return "en"

    # Count characters by script
    devanagari = sum(1 for c in text if '\u0900' <= c <= '\u097F')
    tamil = sum(1 for c in text if '\u0B80' <= c <= '\u0BFF')
    telugu = sum(1 for c in text if '\u0C00' <= c <= '\u0C7F')
    bengali = sum(1 for c in text if '\u0980' <= c <= '\u09FF')
    arabic = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    cjk = sum(1 for c in text if '\u4E00' <= c <= '\u9FFF')
    hangul = sum(1 for c in text if '\uAC00' <= c <= '\uD7AF')

    total = len(text)
    if total == 0:
        return "en"

    # Check ratios
    if devanagari / total > 0.3:
        return "hi"
    if tamil / total > 0.3:
        return "ta"
    if telugu / total > 0.3:
        return "te"
    if bengali / total > 0.3:
        return "bn"
    if arabic / total > 0.3:
        return "ar"
    if cjk / total > 0.3:
        return "zh"
    if hangul / total > 0.3:
        return "ko"

    return "en"


def _calculate_saturation(reel_count: int, audio_use_count: int, creator_count: int) -> float:
    """
    Calculate saturation score (0.0 to 1.0).
    Based on: number of unique creators, total use count, and reel velocity.
    """
    # Creator-based saturation (more creators = more saturated)
    creator_sat = min(1.0, creator_count / 50.0)

    # Use count-based saturation (Instagram audio use count)
    use_sat = min(1.0, audio_use_count / 5_000_000.0)

    # Reel count saturation
    reel_sat = min(1.0, reel_count / 100.0)

    # Weighted average
    return (creator_sat * 0.5) + (use_sat * 0.3) + (reel_sat * 0.2)


def _estimate_window_hours(saturation: float, velocity: float) -> int:
    """
    Estimate remaining window in hours.
    Lower saturation = larger window. Higher velocity = faster burn.
    """
    if saturation >= SATURATION_HIGH:
        return max(0, int(6 - (velocity * 0.5)))
    elif saturation >= SATURATION_MID:
        return max(0, int(18 - (velocity * 1.0)))
    elif saturation >= SATURATION_LOW:
        return max(0, int(36 - (velocity * 1.5)))
    else:
        return max(0, int(48 - (velocity * 2.0)))


def _calculate_confidence(
    creator_count: int,
    reel_count: int,
    avg_velocity: float,
    saturation: float,
    has_official_count: bool
) -> float:
    """Calculate confidence score for a baby trend detection."""
    # Base confidence from creator diversity
    creator_conf = min(0.4, creator_count * 0.15)

    # Velocity confidence
    velocity_conf = min(0.3, avg_velocity / 10.0 * 0.3)

    # Volume confidence
    volume_conf = min(0.15, reel_count * 0.05)

    # Official count bonus
    official_bonus = 0.1 if has_official_count else 0.0

    # Saturation penalty (too saturated = less confidence it's "baby")
    sat_penalty = saturation * 0.2

    return min(1.0, max(0.0, creator_conf + velocity_conf + volume_conf + official_bonus - sat_penalty))


def _detect_cross_platform_migration(
    audio_title: str,
    audio_artist: str,
    supabase: Client
) -> Optional[Dict]:
    """
    Check if this audio is trending on TikTok in other countries but not yet in India.
    Returns migration signal if detected, None otherwise.
    """
    try:
        # Check if we have TikTok data for this audio
        # For now, return None — TikTok integration is Phase 2
        return None
    except Exception as e:
        logger.warning(f"Cross-platform migration check failed: {e}")
        return None


def detect_baby_trends(supabase: Client = None) -> List[Dict]:
    """
    Main detection function. Scans recent reels for velocity spikes
    that indicate a "baby" trend — before it reaches 'emerging' status.

    Returns list of detected baby trends with metadata.
    """
    if not supabase:
        supabase = _get_supabase_client()
    if not supabase:
        logger.error("Supabase client not available")
        return []

    now = datetime.now(timezone.utc)
    cutoff_48h = now - timedelta(hours=48)
    cutoff_6h = now - timedelta(hours=6)

    # 1. Fetch recent high-velocity reels (last 48h)
    try:
        reels_res = supabase.table("reels").select(
            "id, audio_title, audio_artist, audio_id, audio_use_count, "
            "velocity_score, creator_username, caption, posted_at, "
            "likes_count, comments_count, views_count"
        ).gte("posted_at", cutoff_48h.isoformat()).gt("velocity_score", 0.5).execute()

        reels = reels_res.data or []
        if not reels:
            logger.info("No high-velocity reels found in last 48h")
            return []
    except Exception as e:
        logger.error(f"Failed to fetch reels: {e}")
        return []

    # 2. Group reels by audio
    audio_groups = defaultdict(list)
    for reel in reels:
        key = _trend_group_key(reel)
        audio_groups[key].append(reel)

    logger.info(f"Scanned {len(reels)} reels, found {len(audio_groups)} audio groups")

    # 3. Fetch existing trends to avoid duplicates
    try:
        existing_res = supabase.table("trends").select("id, audio_id, title, artist, status").execute()
        existing_trends = existing_res.data or []
        existing_audios = {
            t.get("audio_id"): t for t in existing_trends if t.get("audio_id")
        }
        existing_titles = {
            (t.get("title", "").lower(), t.get("artist", "").lower()): t
            for t in existing_trends if t.get("title")
        }
    except Exception as e:
        logger.error(f"Failed to fetch existing trends: {e}")
        existing_audios = {}
        existing_titles = {}

    # 4. Evaluate each audio group
    baby_trends = []
    for group_key, group_reels in audio_groups.items():
        try:
            trend = _evaluate_group(
                group_key, group_reels, existing_audios, existing_titles, now
            )
            if trend:
                baby_trends.append(trend)
        except Exception as e:
            logger.warning(f"Error evaluating group {group_key}: {e}")
            continue

    # 5. Save to database
    saved_count = 0
    for trend in baby_trends:
        try:
            _save_baby_trend(trend, supabase)
            saved_count += 1
        except Exception as e:
            logger.warning(f"Failed to save baby trend: {e}")

    logger.info(f"Detected {len(baby_trends)} baby trends, saved {saved_count}")
    return baby_trends


def _trend_group_key(reel: dict) -> str:
    """Generate a grouping key for a reel based on audio."""
    title = (reel.get("audio_title") or "").strip()
    artist = (reel.get("audio_artist") or "").strip()

    if not title or title.lower() in ("original audio", ""):
        return f"original:{reel.get('creator_username', 'unknown')}"

    return f"{title.lower()}|{artist.lower()}"


def _evaluate_group(
    group_key: str,
    group_reels: List[Dict],
    existing_audios: Dict,
    existing_titles: Dict,
    now: datetime
) -> Optional[Dict]:
    """Evaluate a group of reels with the same audio to determine if it's a baby trend."""

    # Skip if too few reels
    if len(group_reels) < BABY_MIN_REELS:
        return None

    # Get unique creators
    creators = set(r.get("creator_username") for r in group_reels if r.get("creator_username"))
    if len(creators) < BABY_MIN_CREATORS:
        return None

    # Check if already tracked as emerging/rising/peaked
    first_reel = group_reels[0]
    audio_id = first_reel.get("audio_id")
    audio_title = first_reel.get("audio_title", "")
    audio_artist = first_reel.get("audio_artist", "")

    if audio_id and audio_id in existing_audios:
        existing = existing_audios[audio_id]
        if existing.get("status") in ("emerging", "rising", "peaked"):
            return None  # Already tracked at a higher level

    title_lower = audio_title.lower().strip()
    artist_lower = audio_artist.lower().strip()
    if (title_lower, artist_lower) in existing_titles:
        existing = existing_titles[(title_lower, artist_lower)]
        if existing.get("status") in ("emerging", "rising", "peaked"):
            return None

    # Calculate metrics
    velocities = [r.get("velocity_score", 0) for r in group_reels]
    avg_velocity = sum(velocities) / len(velocities) if velocities else 0
    max_velocity = max(velocities) if velocities else 0

    # Check for velocity spike (12x baseline)
    # We don't have per-creator baselines in this simplified version,
    # so we use absolute velocity thresholds
    has_spike = max_velocity >= BABY_VELOCITY_MULTIPLIER or avg_velocity >= (BABY_VELOCITY_MULTIPLIER * 0.7)

    if not has_spike:
        return None

    # Calculate other metrics
    audio_use_count = max(r.get("audio_use_count", 0) or 0 for r in group_reels)
    total_likes = sum(r.get("likes_count", 0) or 0 for r in group_reels)
    total_comments = sum(r.get("comments_count", 0) or 0 for r in group_reels)
    total_views = sum(r.get("views_count", 0) or 0 for r in group_reels)

    # Find oldest and newest reel
    posted_times = []
    for r in group_reels:
        pa = r.get("posted_at")
        if pa:
            if isinstance(pa, str):
                try:
                    posted_times.append(datetime.fromisoformat(pa.replace("Z", "+00:00")))
                except:
                    pass
            elif isinstance(pa, datetime):
                posted_times.append(pa)

    if not posted_times:
        return None

    oldest_reel = min(posted_times)
    newest_reel = max(posted_times)
    trend_age_hours = int((now - oldest_reel).total_seconds() / 3600)

    # Classify
    captions = [r.get("caption", "") for r in group_reels if r.get("caption")]
    niche = _classify_niche(audio_title, audio_artist, captions)
    trend_type = _classify_trend_type(audio_title, captions)
    language = _detect_language(audio_title + " " + " ".join(captions[:3]))
    saturation = _calculate_saturation(len(group_reels), audio_use_count, len(creators))
    window_hours = _estimate_window_hours(saturation, avg_velocity)
    confidence = _calculate_confidence(
        len(creators), len(group_reels), avg_velocity, saturation,
        audio_use_count > 0
    )

    if confidence < BABY_CONFIDENCE_THRESHOLD:
        return None

    # Determine trend origin (simplified — use language as proxy)
    origin = "IN"  # Default to India
    if language == "pt":
        origin = "BR"
    elif language == "es":
        origin = "MX"
    elif language == "ko":
        origin = "KR"
    elif language == "ja":
        origin = "JP"
    elif language == "ar":
        origin = "TR"

    # Check cross-platform migration
    migration_signal = _detect_cross_platform_migration(audio_title, audio_artist, None)

    return {
        "audio_title": audio_title,
        "audio_artist": audio_artist,
        "audio_id": audio_id,
        "audio_use_count": audio_use_count,
        "platform": "instagram",
        "status": "baby",
        "niche_tag": niche,
        "trend_type": trend_type,
        "language": language,
        "trend_origin": origin,
        "reel_count": len(group_reels),
        "creator_count": len(creators),
        "creators": list(creators),
        "avg_velocity": round(avg_velocity, 3),
        "max_velocity": round(max_velocity, 3),
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_views": total_views,
        "saturation_score": round(saturation, 3),
        "window_hours_remaining": window_hours,
        "confidence": round(confidence, 3),
        "trend_age_hours": trend_age_hours,
        "first_detected_at": now.isoformat(),
        "is_cross_cultural": migration_signal is not None,
        "migration_signal": migration_signal,
        "content_type": trend_type,
        "cultural_context": "celebration" if any(
            kw in audio_title.lower()
            for kw in ["festival", "diwali", "holi", "christmas", "new year"]
        ) else "everyday",
    }


def _save_baby_trend(trend: Dict, supabase: Client):
    """Save a detected baby trend to the database."""
    # Check if already exists by audio_id or title+artist
    audio_id = trend.get("audio_id")
    title = trend.get("audio_title", "")
    artist = trend.get("audio_artist", "")

    existing = None
    if audio_id:
        res = supabase.table("trends").select("id, status").eq("audio_id", audio_id).execute()
        if res.data:
            existing = res.data[0]

    if not existing and title:
        res = supabase.table("trends").select("id, status").eq("title", title).eq("artist", artist).execute()
        if res.data:
            existing = res.data[0]

    if existing:
        # Update only if current status is lower priority
        STATUS_PRIORITY = {"expired": 0, "peaked": 1, "baby": 1.5, "emerging": 2, "rising": 3}
        current_priority = STATUS_PRIORITY.get(existing.get("status", ""), 0)
        new_priority = STATUS_PRIORITY.get("baby", 1.5)
        if new_priority > current_priority:
            supabase.table("trends").update({
                "status": "baby",
                "velocity_avg": trend["avg_velocity"],
                "peak_velocity": trend["max_velocity"],
                "reel_count": trend["reel_count"],
                "saturation_score": trend["saturation_score"],
                "window_hours_remaining": trend["window_hours_remaining"],
                "confidence": trend["confidence"],
            }).eq("id", existing["id"]).execute()
        return

    # Insert new trend
    trend_data = {
        "audio_title": trend["audio_title"],
        "audio_artist": trend["audio_artist"],
        "audio_id": trend.get("audio_id"),
        "audio_use_count": trend["audio_use_count"],
        "platform": "instagram",
        "trend_type": "trend",
        "status": "baby",
        "niche_tag": trend["niche_tag"],
        "content_type": trend["trend_type"],
        "language": trend["language"],
        "trend_origin": trend["trend_origin"],
        "reel_count": trend["reel_count"],
        "velocity_avg": trend["avg_velocity"],
        "peak_velocity": trend["max_velocity"],
        "saturation_score": trend["saturation_score"],
        "global_saturation_pct": round(trend["saturation_score"] * 100, 1),
        "window_hours_remaining": trend["window_hours_remaining"],
        "confidence": trend["confidence"],
        "is_cross_cultural": trend["is_cross_cultural"],
        "cultural_context": trend["cultural_context"],
        "first_detected_at": trend["first_detected_at"],
        "trend_age_hours": trend["trend_age_hours"],
        "is_dance": any(kw in (trend["audio_title"] + " " + trend["audio_artist"]).lower()
                        for kw in ["dance", "choreography", "moves"]),
        "needs_filming": trend["trend_type"] in ("format", "meme"),
    }

    supabase.table("trends").insert(trend_data).execute()


def get_baby_trends(
    supabase: Client = None,
    niche: str = None,
    limit: int = 20
) -> List[Dict]:
    """
    Query baby trends from the database, optionally filtered by niche.
    """
    if not supabase:
        supabase = _get_supabase_client()
    if not supabase:
        return []

    try:
        query = supabase.table("trends").select("*").eq("status", "baby")
        if niche:
            query = query.eq("niche_tag", niche)
        query = query.order("confidence", desc=True).limit(limit)
        result = query.execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Failed to fetch baby trends: {e}")
        return []


def get_trends_by_status(
    supabase: Client = None,
    status: str = "emerging",
    niche: str = None,
    limit: int = 20
) -> List[Dict]:
    """
    Query trends by status, optionally filtered by niche.
    """
    if not supabase:
        supabase = _get_supabase_client()
    if not supabase:
        return []

    try:
        query = supabase.table("trends").select("*").eq("status", status)
        if niche:
            query = query.eq("niche_tag", niche)
        query = query.order("confidence", desc=True).limit(limit)
        result = query.execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Failed to fetch {status} trends: {e}")
        return []
