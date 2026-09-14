import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from trend_constants import CREATOR_OUTLIER_VIEW_MULTIPLIER, CREATOR_OUTLIER_MIN_VIEWS

logger = logging.getLogger(__name__)


def classify_creator_tier(follower_count: Optional[int]) -> str:
    """
    Classifies creator into watchlist tier based on exact follower count boundaries.
    NULL or None follower counts are safely classified as 'tier_3b_nano' (matching SQL verification).
    """
    if follower_count is None:
        return "tier_3b_nano"
    
    try:
        fc = int(follower_count)
    except (ValueError, TypeError):
        return "tier_3b_nano"

    if fc < 1000:
        return "tier_3b_nano"
    elif 1000 <= fc < 10000:
        return "tier_2_micro"
    elif 10000 <= fc < 100000:
        return "tier_1_mid"
    else:  # fc >= 100000
        return "tier_3a_macro"


def classify_and_sync_creator_tiers(sb) -> Dict[str, int]:
    """
    Scans creator_baselines and populates watchlist_tier across all existing creator rows.
    Executes a deploy-time backfill pass across all creators.
    """
    if not sb:
        logger.warning("Supabase client is null. Skipping creator tier backfill.")
        return {}

    logger.info("Starting creator watchlist tier classification backfill...")
    summary = {
        "tier_1_mid": 0,
        "tier_2_micro": 0,
        "tier_3a_macro": 0,
        "tier_3b_nano": 0
    }

    try:
        res = sb.table("creator_baselines").select("username, follower_count").execute()
        creators = res.data or []
        
        for c in creators:
            username = c.get("username")
            if not username:
                continue
            
            fc = c.get("follower_count")
            tier = classify_creator_tier(fc)
            summary[tier] = summary.get(tier, 0) + 1
            
            # Update watchlist_tier in database
            sb.table("creator_baselines") \
                .update({"watchlist_tier": tier}) \
                .eq("username", username) \
                .execute()

        logger.info(f"Creator watchlist tier backfill complete. Summary: {summary}")
        return summary
    except Exception as e:
        logger.error(f"Error executing creator watchlist tier backfill: {e}")
        return summary


def poll_creator_watchlist(sb, limit: int = 15) -> List[Dict[str, Any]]:
    """
    Queries creators due for watchlist polling based on tier-reserved allocations with dynamic spillover:
    - Target Budget: limit (default 15 creators per 3h cycle)
    - Reserved Allocation: 10 slots for Tier 1 (Mid-Tier), 5 slots for Tier 2 (Micro)
    - Dynamic Spillover: Unused slots in one tier automatically spill over to the other tier.
    """
    if not sb:
        logger.warning("Supabase client is null. Skipping creator watchlist polling.")
        return []

    t1_target = 10
    t2_target = 5

    # 1. Fetch due Tier 1 creators
    t1_creators = []
    try:
        res1 = sb.table("creator_baselines") \
            .select("username, follower_count, median_views, last_watchlist_scraped_at") \
            .eq("watchlist_tier", "tier_1_mid") \
            .eq("watchlist_status", "active") \
            .limit(limit) \
            .execute()
        t1_creators = res1.data or []
    except Exception as e:
        logger.warning(f"Error querying Tier 1 watchlist creators: {e}")

    # 2. Fetch due Tier 2 creators
    t2_creators = []
    try:
        res2 = sb.table("creator_baselines") \
            .select("username, follower_count, median_views, last_watchlist_scraped_at") \
            .eq("watchlist_tier", "tier_2_micro") \
            .eq("watchlist_status", "active") \
            .limit(limit) \
            .execute()
        t2_creators = res2.data or []
    except Exception as e:
        logger.warning(f"Error querying Tier 2 watchlist creators: {e}")

    # 3. Calculate slot allocation with dynamic spillover
    n_t1 = len(t1_creators)
    n_t2 = len(t2_creators)

    if n_t1 <= t1_target:
        # Tier 1 has fewer due than reserved quota -> Tier 1 gets all n_t1, Tier 2 gets remainder
        t1_take = n_t1
        t2_take = min(n_t2, limit - t1_take)
    elif n_t2 <= t2_target:
        # Tier 2 has fewer due than reserved quota -> Tier 2 gets all n_t2, Tier 1 gets remainder
        t2_take = n_t2
        t1_take = min(n_t1, limit - t2_take)
    else:
        # Both tiers have full queues -> strictly enforce reserved allocations (10 T1, 5 T2)
        t1_take = t1_target
        t2_take = t2_target

    selected = t1_creators[:t1_take] + t2_creators[:t2_take]
    logger.info(f"[WATCHLIST_POLLER] Selected {len(selected)} creators for polling ({t1_take} Tier 1, {t2_take} Tier 2).")
    return selected


def evaluate_creator_outlier_virality(reel_data: dict, creator_baseline: dict) -> bool:
    """
    Evaluates whether a reel exhibits creator outlier virality.
    Returns True if:
    1. reel_views >= CREATOR_OUTLIER_VIEW_MULTIPLIER * median_views (3.0x multiplier)
    2. reel_views >= CREATOR_OUTLIER_MIN_VIEWS (1,000 view floor)
    """
    if not reel_data or not creator_baseline:
        return False

    views = float(reel_data.get("view_count") or reel_data.get("views") or 0)
    median_views = float(creator_baseline.get("median_views") or 0.0)

    # Floor guard: Reel views must meet or exceed CREATOR_OUTLIER_MIN_VIEWS (1,000 views)
    if views < CREATOR_OUTLIER_MIN_VIEWS:
        return False

    # Multiplier guard: Reel views must meet or exceed 3.0x creator's median views
    if median_views <= 0:
        # If creator has no median_views baseline yet, fallback to floor check
        return views >= CREATOR_OUTLIER_MIN_VIEWS

    return views >= (CREATOR_OUTLIER_VIEW_MULTIPLIER * median_views)
