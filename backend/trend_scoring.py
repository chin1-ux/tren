from __future__ import annotations
import os
from dataclasses import dataclass
from enum import Enum

# Configurable thresholds/weights for urgency calculation
URGENCY_THRESHOLD_CRITICAL = float(os.getenv("URGENCY_THRESHOLD_CRITICAL", "70"))
URGENCY_THRESHOLD_HIGH = float(os.getenv("URGENCY_THRESHOLD_HIGH", "50"))
URGENCY_THRESHOLD_MODERATE = float(os.getenv("URGENCY_THRESHOLD_MODERATE", "30"))

URGENCY_WEIGHT_VELOCITY = float(os.getenv("URGENCY_WEIGHT_VELOCITY", "40"))
URGENCY_WEIGHT_SATURATION = float(os.getenv("URGENCY_WEIGHT_SATURATION", "35"))
URGENCY_WEIGHT_TIME = float(os.getenv("URGENCY_WEIGHT_TIME", "25"))

# Saturation threshold constants (Bug 7 fix)
# GLOBAL: audio_use_count is Instagram's OFFICIAL platform-wide count (can be millions).
# Old value of 100K caused every qualifying trend (emerging=150K+) to compute as >100%
# saturated, setting window_h=0, and getting immediately expired by TrendRefresher.
# 5M means: 150K uses = 3% sat (48h window), 800K = 16% (48h), 3M = 60% (16h), 10M = 200% (expired).
GLOBAL_SATURATION_THRESHOLD_REELS = int(os.getenv("GLOBAL_SATURATION_THRESHOLD_REELS", "5000000"))
# INDIA: india_use_count is our scraped reel count tagged as creator_country=IN.
# Old value of 8K was reasonable but still too low given our 12K total reel dataset.
INDIA_SATURATION_THRESHOLD_REELS = int(os.getenv("INDIA_SATURATION_THRESHOLD_REELS", "500"))
# NOTE (Aug 18, 2026): Live DB query shows max india_use_count across ALL audio is 13.
# Both 500 and 8K thresholds are 38-615x too high to ever trigger. This is inert until
# scraper pagination (P-PIPE-1) increases per-audio India reel counts. The scraper's
# calculate_saturation() at instagram_scraper_browser.py:34 uses 100K/8K — different from
# these values. Both sets are unvalidated guesses. Revisit after pagination is implemented.

# Viral multiplier scaling constant (Bug 8 fix)
VIRAL_MULTIPLIER_SCALE_FACTOR = float(os.getenv("VIRAL_MULTIPLIER_SCALE_FACTOR", "10000"))
VIRAL_MULTIPLIER_DISPLAY_MULTIPLIER = float(os.getenv("VIRAL_MULTIPLIER_DISPLAY_MULTIPLIER", "10"))

# Badge threshold constants (user requirement - need tuning)
MEGA_TREND_REEL_THRESHOLD = int(os.getenv("MEGA_TREND_REEL_THRESHOLD", "10000"))
MEGA_TREND_VELOCITY_THRESHOLD = float(os.getenv("MEGA_TREND_VELOCITY_THRESHOLD", "50000"))


class TrendUrgency(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"

class TrendLifecycle(Enum):
    EMERGING = "emerging"
    RISING = "rising"
    PEAKED = "peaked"
    EXPIRED = "expired"

@dataclass
class TrendState:
    urgency: TrendUrgency
    lifecycle: TrendLifecycle
    velocity_tier: str
    saturation_tier: str
    is_mega: bool
    is_under_radar: bool
    confidence: float
    velocity_avg: float
    global_saturation_pct: float
    india_saturation_pct: float
    window_hours_remaining: float
    audio_use_count: int


def calculate_trend_state(
    velocity_avg: float,
    global_saturation_pct: float,
    india_saturation_pct: float,
    window_hours_remaining: float,
    audio_use_count: int,
    confidence: float,
    max_velocity: float,
    discovery_source: str,
) -> TrendState:
    """
    Single source of truth for trend state.
    All UI elements (status copy, badges, CTAs) derive from this.
    Uses configurable thresholds/weights from environment variables.
    """
    
    # 1. Determine velocity tier
    # velocity_avg is in the range of thousands to millions (e.g., 30841, 86139, 1290523)
    # Adjusted thresholds to match actual data scale
    if velocity_avg >= 100000:
        velocity_tier = "accelerating"
    elif velocity_avg >= 20000:
        velocity_tier = "stable"
    else:
        velocity_tier = "declining"
    
    if global_saturation_pct < 20:
        saturation_tier = "early"
    elif global_saturation_pct < 50:
        saturation_tier = "moderate"
    elif global_saturation_pct < 75:
        saturation_tier = "high"
    else:
        saturation_tier = "saturated"
    
    # 3. Determine lifecycle (emerging/rising/peaked/expired)
    if window_hours_remaining <= 0 or global_saturation_pct >= 90:
        lifecycle = TrendLifecycle.EXPIRED
    elif velocity_tier == "declining" and saturation_tier in ["high", "saturated"]:
        lifecycle = TrendLifecycle.PEAKED
    elif saturation_tier == "early" and velocity_tier in ["accelerating", "stable"]:
        lifecycle = TrendLifecycle.EMERGING
    else:
        lifecycle = TrendLifecycle.RISING
    
    # 4. Determine urgency (drives status copy)
    urgency_score = 0.0
    
    if velocity_tier == "accelerating":
        urgency_score += URGENCY_WEIGHT_VELOCITY
    elif velocity_tier == "stable":
        urgency_score += URGENCY_WEIGHT_VELOCITY * 0.625
    else:
        urgency_score += URGENCY_WEIGHT_VELOCITY * 0.125
    
    if saturation_tier == "early":
        urgency_score += URGENCY_WEIGHT_SATURATION
    elif saturation_tier == "moderate":
        urgency_score += URGENCY_WEIGHT_SATURATION * 0.571
    elif saturation_tier == "high":
        urgency_score += URGENCY_WEIGHT_SATURATION * 0.286
    else:
        urgency_score += 0
    
    time_factor = max(0, min(1, window_hours_remaining / 48))
    urgency_score += (1 - time_factor) * URGENCY_WEIGHT_TIME
    
    # EXPIRED trends should always have LOW urgency (validation rule)
    if lifecycle == TrendLifecycle.EXPIRED:
        urgency = TrendUrgency.LOW
    else:
        if urgency_score >= URGENCY_THRESHOLD_CRITICAL:
            urgency = TrendUrgency.CRITICAL
        elif urgency_score >= URGENCY_THRESHOLD_HIGH:
            urgency = TrendUrgency.HIGH
        elif urgency_score >= URGENCY_THRESHOLD_MODERATE:
            urgency = TrendUrgency.MODERATE
        else:
            urgency = TrendUrgency.LOW
    
    is_mega = audio_use_count > MEGA_TREND_REEL_THRESHOLD or velocity_avg >= MEGA_TREND_VELOCITY_THRESHOLD
    
    is_under_radar = (
        not is_mega and
        discovery_source == "unexpected_candidate" and
        saturation_tier == "early"
    )
    
    return TrendState(
        urgency=urgency,
        lifecycle=lifecycle,
        velocity_tier=velocity_tier,
        saturation_tier=saturation_tier,
        is_mega=is_mega,
        is_under_radar=is_under_radar,
        confidence=confidence,
        velocity_avg=velocity_avg,
        global_saturation_pct=global_saturation_pct,
        india_saturation_pct=india_saturation_pct,
        window_hours_remaining=window_hours_remaining,
        audio_use_count=audio_use_count,
    )


def calculate_opportunity_score(*, india_saturation_pct: float, window_hours_remaining: float, confidence: float) -> float:
    sat_factor = max(0.0, (100.0 - float(india_saturation_pct or 0.0)) / 100.0)
    win_factor = max(0.0, float(window_hours_remaining or 0.0) / 24.0)
    conf = max(0.0, float(confidence or 0.0))
    return round(((sat_factor * 60.0) + (win_factor * 40.0)) * conf, 1)


def calculate_realistic_peaking_score(trend: dict, snapshots: list) -> float:
    """
    Calculate peaking score using data that actually exists:
    - Velocity acceleration (50%): from trend_snapshots
    - Window efficiency (30%): (window_remaining / 48) * 100
    - Creator count score (20%): from reel_count
    
    Args:
        trend: Trend data dictionary
        snapshots: List of trend_snapshots for this trend (pre-fetched to avoid N+1)
    
    Returns:
        Peaking score (0-100)
    """
    # Calculate velocity acceleration from snapshots
    velocity_score = 0
    if len(snapshots) >= 2:
        recent_velocity = snapshots[0]['velocity_avg']
        older_velocity = snapshots[-1]['velocity_avg']
        if older_velocity > 0:
            acceleration = ((recent_velocity - older_velocity) / older_velocity) * 100
            # Normalize to 0-100 (assume 100% acceleration = 100 points)
            velocity_score = min(100, max(0, acceleration))
    
    # Calculate window efficiency (strictly 0-100 scale)
    window_remaining = trend.get('window_hours_remaining', 0)
    window_efficiency = min(100.0, (window_remaining / 48.0) * 100.0) if window_remaining > 0 else 0
    
    # Calculate creator count score
    reel_count = trend.get('reel_count', 0)
    creator_score = min(100.0, (reel_count / 1000.0) * 100.0)  # 1000 reels = 100 points
    
    # Combined score
    peaking_score = (velocity_score * 0.50) + (window_efficiency * 0.30) + (creator_score * 0.20)
    return round(peaking_score, 2)

