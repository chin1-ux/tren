#!/usr/bin/env python3
"""
Monitor the impact of velocity-based tracked_audio enrollment.
Run this daily to track how many trends are discovered via the new high-velocity signal.
"""

import os
import sys
import io
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Load .env (try backend directory first, then project root)
backend_dir = os.path.dirname(os.path.abspath(__file__))
backend_env = os.path.join(backend_dir, '.env')
project_root = os.path.dirname(backend_dir)
project_env = os.path.join(project_root, '.env')

if os.path.exists(backend_env):
    load_dotenv(backend_env)
elif os.path.exists(project_env):
    load_dotenv(project_env)
else:
    load_dotenv()  # Fallback to current directory

def monitor_velocity_enrollment():
    """Monitor trends discovered via velocity-based enrollment"""
    
    print("=== Velocity-Based Enrollment Impact Monitor ===\n")
    
    # Calculate current dynamic threshold for reporting
    try:
        import numpy as np
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_reels = sb.table("reels") \
            .select("velocity_score") \
            .not_.is_("velocity_score", "null") \
            .gte("scraped_at", seven_days_ago.isoformat()) \
            .execute()
        
        velocities = [reel.get("velocity_score", 0.0) or 0.0 for reel in recent_reels.data]
        velocities = [v for v in velocities if v > 0]
        
        if len(velocities) >= 20:
            velocity_array = np.array(velocities)
            current_threshold = np.percentile(velocity_array, 95)
            print(f"Current dynamic velocity threshold: {current_threshold:.1f}")
        else:
            current_threshold = None
            print(f"Velocity-based enrollment: SKIPPED (insufficient data: {len(velocities)} samples)")
    except Exception as e:
        current_threshold = 5000.0
        print(f"Could not calculate dynamic threshold: {e}, using fallback {current_threshold}")
    
    print()
    
    # Initialize Supabase client
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("ERROR: Supabase credentials not set")
        return False
    
    sb = create_client(url, key)
    
    # Get tracked_audio entries added in the last 24 hours
    one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    
    print(f"=== Recent tracked_audio enrollments (since {one_day_ago.isoformat()}) ===")
    
    recent_tracked = sb.table('tracked_audio') \
        .select('audio_id, audio_title, audio_artist, first_seen_at') \
        .gte('first_seen_at', one_day_ago.isoformat()) \
        .order('first_seen_at', desc=True) \
        .execute()
    
    print(f"Total new tracked_audio entries: {len(recent_tracked.data)}")
    
    if not recent_tracked.data:
        print("No new tracked_audio entries in the last 24 hours.")
        return True
    
    # Analyze each new tracked audio
    velocity_based_count = 0
    reel_count_based_count = 0
    promoted_to_trends = 0
    
    for audio in recent_tracked.data:
        audio_id = audio['audio_id']
        audio_title = audio['audio_title']
        first_seen = audio['first_seen_at']
        
        # Check reel count at time of enrollment
        reels_res = sb.table('reels') \
            .select('reel_id, velocity_score, view_count, like_count, scraped_at') \
            .eq('audio_id', audio_id) \
            .lte('scraped_at', first_seen) \
            .execute()
        
        reel_count_at_enrollment = len(reels_res.data)
        
        # Check if this was velocity-based enrollment (using dynamic threshold)
        high_velocity_at_enrollment = False
        if current_threshold is not None:  # Only check if threshold calculation succeeded
            for reel in reels_res.data:
                vel = reel.get('velocity_score', 0.0) or 0.0
                views = reel.get('view_count', 0) or 0
                likes = reel.get('like_count', 0) or 0
                
                if vel > current_threshold or (likes > 1000 and views > 10000):
                    high_velocity_at_enrollment = True
                    break
        
        # If threshold is None, velocity-based enrollment couldn't have happened
        
        if current_threshold is None and high_velocity_at_enrollment:
            # This shouldn't happen since we skip velocity check when threshold is None
            logger.warning(f"Unexpected velocity-based enrollment when threshold was None for audio_id {audio_id}")
            reel_count_based_count += 1
            enrollment_type = "REEL_COUNT_BASED"
        elif high_velocity_at_enrollment:
            velocity_based_count += 1
            enrollment_type = "VELOCITY_BASED"
        else:
            reel_count_based_count += 1
            enrollment_type = "REEL_COUNT_BASED"
        
        # Check if this audio has been promoted to a trend
        trend_res = sb.table('trends') \
            .select('id, status, first_detected_at') \
            .eq('audio_title', audio_title) \
            .execute()
        
        is_trend = len(trend_res.data) > 0
        if is_trend:
            promoted_to_trends += 1
            trend_status = trend_res.data[0]['status']
            trend_detected = trend_res.data[0]['first_detected_at']
        else:
            trend_status = "NOT_PROMOTED"
            trend_detected = None
        
        print(f"\n[{enrollment_type}] {audio_title}")
        print(f"  Audio ID: {audio_id}")
        print(f"  First Seen: {first_seen}")
        print(f"  Reels at enrollment: {reel_count_at_enrollment}")
        print(f"  High velocity: {high_velocity_at_enrollment}")
        print(f"  Trend status: {trend_status}")
        if trend_detected:
            print(f"  Trend detected: {trend_detected}")
    
    # Summary statistics
    print(f"\n=== Summary (Last 24 Hours) ===")
    print(f"Total new tracked_audio: {len(recent_tracked.data)}")
    
    if current_threshold is None:
        print(f"Velocity-based enrollment: SKIPPED (insufficient data)")
        print(f"All enrollments used reel-count criteria: {reel_count_based_count}")
    else:
        print(f"Velocity-based enrollments: {velocity_based_count}")
        print(f"Reel-count-based enrollments: {reel_count_based_count}")
        if velocity_based_count > 0:
            velocity_promotion_rate = (promoted_to_trends / velocity_based_count) * 100
            print(f"Velocity-based promotion rate: {velocity_promotion_rate:.1f}%")
    
    print(f"Promoted to trends: {promoted_to_trends}")
    
    # Compare with previous week baseline
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    print(f"\n=== Week-over-Week Comparison ===")
    
    # Get tracked_audio from 7-8 days ago (before the fix)
    eight_days_ago = datetime.now(timezone.utc) - timedelta(days=8)
    
    baseline_tracked = sb.table('tracked_audio') \
        .select('audio_id, audio_title, first_seen_at') \
        .gte('first_seen_at', eight_days_ago.isoformat()) \
        .lt('first_seen_at', seven_days_ago.isoformat()) \
        .execute()
    
    print(f"Baseline tracked_audio (7-8 days ago): {len(baseline_tracked.data)}")
    print(f"Current tracked_audio (last 24 hours): {len(recent_tracked.data)}")
    
    if len(baseline_tracked.data) > 0:
        growth_rate = ((len(recent_tracked.data) - len(baseline_tracked.data)) / len(baseline_tracked.data)) * 100
        print(f"Growth rate: {growth_rate:+.1f}%")
    
    # Check for any Beretta-like cases (Latin/global music with Indian crossover)
    print(f"\n=== Global/Latin Music Detection ===")
    
    global_keywords = ['latin', 'spanish', 'beretta', 'corrido', 'reggaeton', 'salsa', 'bachata']
    
    for audio in recent_tracked.data:
        audio_title_lower = audio['audio_title'].lower()
        if any(keyword in audio_title_lower for keyword in global_keywords):
            print(f"Global/Latin candidate: {audio['audio_title']}")
            
            # Check for Indian creator crossover
            reels_res = sb.table('reels') \
                .select('owner_username, caption') \
                .eq('audio_id', audio['audio_id']) \
                .execute()
            
            indian_creators = []
            for reel in reels_res.data:
                username = reel.get('owner_username', '').lower()
                caption = reel.get('caption', '').lower()
                
                # Simple Indian name detection
                indian_indicators = ['singh', 'kaur', 'kumar', 'lal', 'dev', 'raj', 'priya', 'rahul', 'arjun']
                if any(indicator in username for indicator in indian_indicators):
                    indian_creators.append(username)
            
            if indian_creators:
                print(f"  Indian creators: {', '.join(set(indian_creators))}")
    
    return True

if __name__ == '__main__':
    monitor_velocity_enrollment()
