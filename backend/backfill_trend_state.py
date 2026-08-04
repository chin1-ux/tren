"""
Backfill unified state for existing trends.
RUN ON STAGING FIRST with diff report before production.
"""

from trend_scoring import calculate_trend_state, GLOBAL_SATURATION_THRESHOLD_REELS
from supabase import create_client
from dotenv import load_dotenv
import os

def backfill_trend_states(environment: str = "staging") -> dict:
    """
    Backfill unified state for existing trends.
    Returns diff report: {trend_id: {old: {...}, new: {...}}}
    """
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    
    res = sb.table("trends").select("*").execute()
    trends = res.data or []
    
    diff_report = {}
    updated = 0
    for trend in trends:
        # Recalculate window_hours_remaining based on saturation (fix for low-saturation trends with 0 window)
        global_sat = trend.get("global_saturation_pct", 0)
        audio_use_count = trend.get("audio_use_count", 0)
        
        # Calculate saturation percentage from audio_use_count if not present
        if global_sat == 0 and audio_use_count > 0:
            global_sat = round(min(100.0, (audio_use_count / GLOBAL_SATURATION_THRESHOLD_REELS) * 100), 1)
        
        # Window hours - calculate based on saturation
        if global_sat >= 90:
            window_h = 0
        elif global_sat >= 75:
            window_h = 8
        elif global_sat >= 50:
            window_h = 16
        elif global_sat >= 20:
            window_h = 24
        else:
            # Early saturation trends have more time
            window_h = 48
        
        state = calculate_trend_state(
            velocity_avg=trend.get("velocity_avg", 0),
            global_saturation_pct=global_sat,
            india_saturation_pct=trend.get("india_saturation_pct", 0),
            window_hours_remaining=window_h,
            audio_use_count=audio_use_count,
            confidence=trend.get("confidence", 0),
            max_velocity=trend.get("peak_velocity", 0),
            discovery_source=trend.get("discovery_source", "regional"),
        )
        
        # Record old state (if exists)
        old_state = {
            "urgency": trend.get("urgency"),
            "lifecycle": trend.get("lifecycle"),
            "velocity_tier": trend.get("velocity_tier"),
            "saturation_tier": trend.get("saturation_tier"),
            "is_mega": trend.get("is_mega"),
            "is_under_radar": trend.get("is_under_radar"),
        }
        
        # Record new state
        new_state = {
            "urgency": state.urgency.value,
            "lifecycle": state.lifecycle.value,
            "velocity_tier": state.velocity_tier,
            "saturation_tier": state.saturation_tier,
            "is_mega": state.is_mega,
            "is_under_radar": state.is_under_radar,
        }
        
        # Only record in diff if state changed
        if old_state != new_state:
            diff_report[trend.get("id")] = {
                "audio_title": trend.get("audio_title"),
                "velocity_avg": trend.get("velocity_avg"),
                "audio_use_count": trend.get("audio_use_count"),
                "global_saturation_pct": global_sat,
                "window_hours_remaining_old": trend.get("window_hours_remaining"),
                "window_hours_remaining_new": window_h,
                "old": old_state,
                "new": new_state,
            }
        
        # Only actually update if running on production
        if environment == "production":
            sb.table("trends").update({
                "urgency": state.urgency.value,
                "lifecycle": state.lifecycle.value,
                "velocity_tier": state.velocity_tier,
                "saturation_tier": state.saturation_tier,
                "is_mega": state.is_mega,
                "is_under_radar": state.is_under_radar,
                "window_hours_remaining": window_h,  # Also fix the window_hours_remaining field
            }).eq("id", trend["id"]).execute()
            updated += 1
            if updated % 100 == 0:
                print(f"Backfilled {updated} trends...")
    
    if environment == "staging":
        print(f"Staging diff report: {len(diff_report)} trends would change")
        # Print first 30 changes for review
        for i, (trend_id, change) in enumerate(list(diff_report.items())[:30]):
            print(f"\n[{i+1}] Trend {trend_id}: {change['audio_title']}")
            print(f"  velocity_avg: {change['velocity_avg']}")
            print(f"  audio_use_count: {change['audio_use_count']}")
            print(f"  global_saturation_pct: {change['global_saturation_pct']}")
            print(f"  window_hours_remaining: {change['window_hours_remaining_old']} -> {change['window_hours_remaining_new']}")
            print(f"  OLD: {change['old']}")
            print(f"  NEW: {change['new']}")
        if len(diff_report) > 30:
            print(f"\n... and {len(diff_report) - 30} more changes")
    else:
        print(f"Production backfill complete: {updated} trends updated")
    
    return diff_report

if __name__ == "__main__":
    import sys
    env = sys.argv[1] if len(sys.argv) > 1 else "staging"
    backfill_trend_states(environment=env)
