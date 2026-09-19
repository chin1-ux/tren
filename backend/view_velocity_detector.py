"""
View-Velocity Outlier Detector

Pure functional module to evaluate view-velocity outlier virality for reels,
especially targeting early breakout micro-creators lacking entries in creator_baselines.
"""

from typing import Dict, Optional
try:
    from trend_constants import (
        CREATOR_OUTLIER_VIEW_MULTIPLIER,
        CREATOR_OUTLIER_MIN_VIEWS,
        VIEW_VELOCITY_UNTRACKED_MIN_VIEWS,
        VIEW_VELOCITY_HEURISTIC_MIN_VIEWS,
        VIEW_VELOCITY_HEURISTIC_REACH_MULT,
    )
except ImportError:
    from backend.trend_constants import (
        CREATOR_OUTLIER_VIEW_MULTIPLIER,
        CREATOR_OUTLIER_MIN_VIEWS,
        VIEW_VELOCITY_UNTRACKED_MIN_VIEWS,
        VIEW_VELOCITY_HEURISTIC_MIN_VIEWS,
        VIEW_VELOCITY_HEURISTIC_REACH_MULT,
    )



def evaluate_view_velocity_outlier(reel: dict, creator_baseline: Optional[dict] = None) -> dict:
    """
    Evaluates whether a reel exhibits view-velocity outlier virality across 3 tiers:

    Tier 1: Exact Baseline (Creator present in creator_baselines with post_count >= 6)
            Condition: reel_views >= 3.0 * median_views AND reel_views >= 1,000

    Tier 2: Heuristic Tier Baseline (1,000 <= followers < 10,000, missing/incomplete baseline)
            Condition: reel_views >= max(20,000, follower_count * 15)

    Tier 3: Untracked Micro-Creator Acceleration (followers < 1,000 or defaulted to 2500 fallback)
            Condition: reel_views >= 50,000

    Returns:
      {
        "is_view_velocity_outlier": bool,
        "outlier_tier": str | None ("exact_baseline", "heuristic_tier", "untracked_micro"),
        "needs_baseline_fetch": bool,
        "reason": str
      }
    """
    if not reel:
        return {
            "is_view_velocity_outlier": False,
            "outlier_tier": None,
            "needs_baseline_fetch": False,
            "reason": "Empty reel payload",
        }

    raw_views = reel.get("view_count") or reel.get("views") or reel.get("videoViewCount") or 0
    try:
        views = float(raw_views)
    except (ValueError, TypeError):
        views = 0.0

    raw_followers = reel.get("owner_follower_count") or reel.get("ownerFollowersCount") or reel.get("follower_count")
    try:
        followers = int(raw_followers) if raw_followers is not None else None
    except (ValueError, TypeError):
        followers = None

    # Check Tier 1: Exact baseline if creator_baseline exists with post_count >= 6
    if creator_baseline:
        post_count = creator_baseline.get("post_count") or 0
        median_views = float(creator_baseline.get("median_views") or 0.0)

        if post_count >= 6 and median_views > 0:
            if views >= (CREATOR_OUTLIER_VIEW_MULTIPLIER * median_views) and views >= CREATOR_OUTLIER_MIN_VIEWS:
                return {
                    "is_view_velocity_outlier": True,
                    "outlier_tier": "exact_baseline",
                    "needs_baseline_fetch": False,
                    "reason": f"Views ({int(views)}) >= {CREATOR_OUTLIER_VIEW_MULTIPLIER}x median views ({int(median_views)})",
                }
            else:
                return {
                    "is_view_velocity_outlier": False,
                    "outlier_tier": "exact_baseline",
                    "needs_baseline_fetch": False,
                    "reason": f"Views ({int(views)}) below exact baseline multiplier ({CREATOR_OUTLIER_VIEW_MULTIPLIER}x {int(median_views)})",
                }

    # If no valid exact baseline exists, evaluate Tier 2 vs Tier 3
    # Synthetic default fallback guard: 2,500 is a placeholder default for untracked hashtag reels.
    # Untracked reels MUST route to Tier 3 (untracked_micro, 50k view floor) rather than Tier 2 reach multiplier.
    is_default_fallback = (followers is None or followers == 2500)

    if not is_default_fallback and followers is not None and 1000 <= followers < 10000:
        threshold = max(VIEW_VELOCITY_HEURISTIC_MIN_VIEWS, float(followers * VIEW_VELOCITY_HEURISTIC_REACH_MULT))
        if views >= threshold:
            return {
                "is_view_velocity_outlier": True,
                "outlier_tier": "heuristic_tier",
                "needs_baseline_fetch": True,
                "reason": f"Views ({int(views)}) >= heuristic threshold ({int(threshold)}) for verified follower count {followers}",
            }
        else:
            return {
                "is_view_velocity_outlier": False,
                "outlier_tier": "heuristic_tier",
                "needs_baseline_fetch": False,
                "reason": f"Views ({int(views)}) below heuristic threshold ({int(threshold)}) for verified follower count {followers}",
            }

    # Tier 3: Untracked Micro-Creator (<1,000 followers or unknown / defaulted 2500 fallback)
    # Target: views >= 50,000 AND (followers < 1,000 OR followers is None OR followers == 2500)
    is_micro_or_untracked = (followers is None or followers == 2500 or followers < 1000)

    if is_micro_or_untracked:
        if views >= VIEW_VELOCITY_UNTRACKED_MIN_VIEWS:
            return {
                "is_view_velocity_outlier": True,
                "outlier_tier": "untracked_micro",
                "needs_baseline_fetch": True,
                "reason": f"Micro-creator views ({int(views)}) >= {int(VIEW_VELOCITY_UNTRACKED_MIN_VIEWS)} breakout floor",
            }
        else:
            return {
                "is_view_velocity_outlier": False,
                "outlier_tier": None,
                "needs_baseline_fetch": False,
                "reason": f"Micro-creator views ({int(views)}) below {int(VIEW_VELOCITY_UNTRACKED_MIN_VIEWS)} breakout floor",
            }


    return {
        "is_view_velocity_outlier": False,
        "outlier_tier": None,
        "needs_baseline_fetch": False,
        "reason": f"Views ({int(views)}) below all outlier detection thresholds",
    }
