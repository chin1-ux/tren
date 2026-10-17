"""
Stage Tag Engine: Single source of truth for trends.stage and stage_computed_at.
Defined in Order 79D:
  - Just starting
  - Blowing up
  - Still going
  - Comeback
  - Fading
  - Expired
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

STAGE_JUST_STARTING = "Just starting"
STAGE_BLOWING_UP = "Blowing up"
STAGE_STILL_GOING = "Still going"
STAGE_COMEBACK = "Comeback"
STAGE_FADING = "Fading"
STAGE_EXPIRED = "Expired"

ALL_STAGES = [
    STAGE_JUST_STARTING,
    STAGE_BLOWING_UP,
    STAGE_STILL_GOING,
    STAGE_COMEBACK,
    STAGE_FADING,
    STAGE_EXPIRED,
]

def parse_dt(dt_val) -> Optional[datetime]:
    if not dt_val:
        return None
    if isinstance(dt_val, datetime):
        return dt_val if dt_val.tzinfo else dt_val.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(dt_val).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None

def compute_single_stage(
    trend: Dict[str, Any],
    recent_reels: List[Dict[str, Any]],
    now_dt: Optional[datetime] = None
) -> str:
    """
    Computes honest stage tag for a single trend.
    Rules:
    1. Expired: newest real reel observation is >= 14 days old (or 0 reels in last 14 days).
    2. Comeback: 
       - newest real observation <= 7 days ago
       - previously declined (status in ['peaked', 'expired', 'resurging'] or decline signal)
       - >= 3 DISTINCT creators in the last 7 days
    3. Blowing up:
       - newest observation <= 3 days ago
       - velocity_avg >= 1500 or status == 'rising'
       - >= 2 distinct creators
    4. Just starting:
       - discovered <= 3 days ago OR status == 'emerging'
       - newest observation <= 3 days ago
       - >= 2 distinct creators
    5. Still going:
       - newest observation <= 7 days ago
       - active reels, not meeting Blowing up velocity
    6. Fading:
       - newest observation between 7 and 14 days ago, or declining velocity
    """
    if now_dt is None:
        now_dt = datetime.now(timezone.utc)

    # Analyze real reels observed in the last 14 days and last 7 days
    reels_7d = []
    creators_7d = set()
    newest_reel_dt = None

    for r in recent_reels:
        r_dt = parse_dt(r.get("scraped_at") or r.get("posted_at"))
        if r_dt:
            if newest_reel_dt is None or r_dt > newest_reel_dt:
                newest_reel_dt = r_dt
            if (now_dt - r_dt).total_seconds() <= 7 * 86400:
                reels_7d.append(r)
                owner = (r.get("owner_username") or "").strip().lower()
                if owner:
                    creators_7d.add(owner)

    # 1. Check Expired: No reel in >= 14 days
    if newest_reel_dt is None or (now_dt - newest_reel_dt).total_seconds() >= 14 * 86400:
        return STAGE_EXPIRED

    age_newest_days = (now_dt - newest_reel_dt).total_seconds() / 86400.0
    status = (trend.get("status") or "").lower()
    velocity = float(trend.get("velocity_avg") or 0.0)
    distinct_creators_7d = len(creators_7d)
    
    # 2. Check Comeback (Order 79D Approved Definition):
    # - last real observation <= 7 days ago
    # - previously declined (was peaked, expired, or resurging from old baseline)
    # - >= 3 DISTINCT creators in the last 7 days
    if age_newest_days <= 7.0 and distinct_creators_7d >= 3:
        # Check prior decline signal
        is_prior_decline = status in ["peaked", "expired", "resurging"]
        if not is_prior_decline:
            # Check if velocity dropped by > 50% from peak
            peak_vel = float(trend.get("peak_velocity") or 0.0)
            if peak_vel > 3000 and velocity < peak_vel * 0.5:
                is_prior_decline = True
        if is_prior_decline:
            return STAGE_COMEBACK

    # 3. Check Blowing up:
    if age_newest_days <= 3.0 and distinct_creators_7d >= 2:
        if velocity >= 1500.0 or status == "rising":
            return STAGE_BLOWING_UP

    # 4. Check Just starting:
    first_detected = parse_dt(trend.get("first_detected_at") or trend.get("created_at"))
    is_recent_discovery = first_detected and (now_dt - first_detected).total_seconds() <= 3 * 86400
    if (is_recent_discovery or status == "emerging") and age_newest_days <= 3.0 and distinct_creators_7d >= 2:
        return STAGE_JUST_STARTING

    # 5. Check Still going:
    if age_newest_days <= 7.0 and (distinct_creators_7d >= 1 or len(recent_reels) >= 1):
        return STAGE_STILL_GOING

    # 6. Default to Fading if observed between 7 and 14 days ago
    return STAGE_FADING

def recompute_all_stages(sb_client, dry_run: bool = False) -> Dict[str, Any]:
    """
    Recomputes stage for all trends and updates trends.stage and trends.stage_computed_at.
    """
    now = datetime.now(timezone.utc)
    logger.info(f"Starting stage recomputation at {now.isoformat()} (dry_run={dry_run})")

    # Fetch all trends with pagination
    trends = []
    t_offset = 0
    t_page_size = 1000
    while True:
        res = sb_client.table("trends").select(
            "id, audio_id, audio_title, audio_artist, status, velocity_avg, "
            "peak_velocity, first_detected_at, created_at, stage"
        ).range(t_offset, t_offset + t_page_size - 1).execute()
        batch = res.data or []
        if not batch:
            break
        trends.extend(batch)
        t_offset += t_page_size
        if len(batch) < t_page_size:
            break

    # Fetch reels from last 14 days
    fourteen_days_ago = (now - timedelta(days=14)).isoformat()
    reels_by_audio = {}
    
    page_size = 1000
    offset = 0
    while True:
        r_res = sb_client.table("reels").select(
            "audio_id, scraped_at, posted_at, owner_username"
        ).gte("scraped_at", fourteen_days_ago).range(offset, offset + page_size - 1).execute()
        batch = r_res.data or []
        if not batch:
            break
        for r in batch:
            aid = str(r.get("audio_id") or "")
            if aid not in reels_by_audio:
                reels_by_audio[aid] = []
            reels_by_audio[aid].append(r)
        offset += page_size
        if len(batch) < page_size:
            break

    counts = {s: 0 for s in ALL_STAGES}
    updates = []

    for t in trends:
        aid = str(t.get("audio_id") or "")
        t_reels = reels_by_audio.get(aid, [])
        new_stage = compute_single_stage(t, t_reels, now_dt=now)
        counts[new_stage] += 1

        if not dry_run and t.get("stage") != new_stage:
            updates.append({"id": t["id"], "stage": new_stage, "stage_computed_at": now.isoformat()})

    if not dry_run and updates:
        logger.info(f"Applying {len(updates)} stage updates to database...")
        for u in updates:
            try:
                sb_client.table("trends").update({
                    "stage": u["stage"],
                    "stage_computed_at": u["stage_computed_at"]
                }).eq("id", u["id"]).execute()
            except Exception as e:
                logger.warning(f"Could not update stage for trend {u['id']}: {e}")

    logger.info(f"Stage recomputation complete: {counts}")
    return {"timestamp": now.isoformat(), "counts": counts, "total": len(trends), "updated": len(updates)}
