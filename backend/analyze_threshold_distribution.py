#!/usr/bin/env python3
"""
Analyze real data distribution for the new velocity-based enrollment thresholds.
Check what percentage of currently rejected single-reel entries would pass the new criteria.
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
    print(f"Loaded .env from: {backend_env}")
elif os.path.exists(project_env):
    load_dotenv(project_env)
    print(f"Loaded .env from: {project_env}")
else:
    load_dotenv()  # Fallback to current directory

def analyze_threshold_distribution():
    """Analyze what percentage of single-reel audio would pass new thresholds"""
    
    print("=== Threshold Distribution Analysis ===\n")
    
    # Initialize Supabase client
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    
    print(f"DEBUG: SUPABASE_URL = {url}")
    print(f"DEBUG: SUPABASE_SERVICE_ROLE_KEY = {key[:20] if key else 'None'}...")
    
    if not url or not key:
        print("ERROR: Supabase credentials not set")
        return False
    
    sb = create_client(url, key)
    
    # Get all audio_ids with exactly 1 reel (currently rejected for tracking)
    print("=== Finding single-reel audio entries ===")
    
    # First, get all audio_ids and their reel counts
    audio_reel_counts = {}
    
    # Get all reels grouped by audio_id
    reels_res = sb.table('reels') \
        .select('audio_id, velocity_score, view_count, like_count, scraped_at') \
        .not_.is_('audio_id', 'null') \
        .execute()
    
    for reel in reels_res.data:
        audio_id = reel.get('audio_id')
        if audio_id:
            if audio_id not in audio_reel_counts:
                audio_reel_counts[audio_id] = []
            audio_reel_counts[audio_id].append(reel)
    
    # Filter to single-reel audio
    single_reel_audio = {aid: reels for aid, reels in audio_reel_counts.items() if len(reels) == 1}
    
    print(f"Total unique audio_ids: {len(audio_reel_counts)}")
    print(f"Single-reel audio_ids: {len(single_reel_audio)}")
    print(f"Multi-reel audio_ids: {len(audio_reel_counts) - len(single_reel_audio)}")
    
    # Check which single-reel audio are already in tracked_audio
    tracked_audio_res = sb.table('tracked_audio').select('audio_id').execute()
    tracked_ids = {row['audio_id'] for row in tracked_audio_res.data}
    
    # Find single-reel audio NOT in tracked_audio (currently rejected)
    rejected_single_reel = {aid: reels for aid, reels in single_reel_audio.items() if aid not in tracked_ids}
    
    print(f"\nSingle-reel audio in tracked_audio: {len(single_reel_audio) - len(rejected_single_reel)}")
    print(f"Single-reel audio NOT in tracked_audio (currently rejected): {len(rejected_single_reel)}")
    
    if len(rejected_single_reel) == 0:
        print("No rejected single-reel audio to analyze.")
        return True
    
    # Analyze thresholds on rejected single-reel audio
    print(f"\n=== Threshold Analysis on {len(rejected_single_reel)} Rejected Single-Reel Audio ===")
    
    velocity_threshold = 5000
    likes_threshold = 1000
    views_threshold = 10000
    
    pass_velocity_count = 0
    pass_engagement_count = 0
    pass_any_count = 0
    fail_count = 0
    
    velocity_values = []
    engagement_values = []
    
    for audio_id, reels in rejected_single_reel.items():
        reel = reels[0]  # Single reel
        vel = reel.get('velocity_score', 0.0) or 0.0
        views = reel.get('view_count', 0) or 0
        likes = reel.get('like_count', 0) or 0
        
        velocity_values.append(vel)
        engagement_values.append((likes, views))
        
        passes_velocity = vel > velocity_threshold
        passes_engagement = likes > likes_threshold and views > views_threshold
        passes_any = passes_velocity or passes_engagement
        
        if passes_velocity:
            pass_velocity_count += 1
        if passes_engagement:
            pass_engagement_count += 1
        if passes_any:
            pass_any_count += 1
        else:
            fail_count += 1
    
    print(f"\nThreshold Results:")
    print(f"Velocity > {velocity_threshold}: {pass_velocity_count} ({pass_velocity_count/len(rejected_single_reel)*100:.1f}%)")
    print(f"Engagement (likes > {likes_threshold} AND views > {views_threshold}): {pass_engagement_count} ({pass_engagement_count/len(rejected_single_reel)*100:.1f}%)")
    print(f"Passes EITHER criteria: {pass_any_count} ({pass_any_count/len(rejected_single_reel)*100:.1f}%)")
    print(f"Fails both criteria: {fail_count} ({fail_count/len(rejected_single_reel)*100:.1f}%)")
    
    # Statistics
    if velocity_values:
        velocity_values.sort()
        print(f"\nVelocity Statistics:")
        print(f"  Min: {velocity_values[0]:.1f}")
        print(f"  25th percentile: {velocity_values[len(velocity_values)//4]:.1f}")
        print(f"  Median: {velocity_values[len(velocity_values)//2]:.1f}")
        print(f"  75th percentile: {velocity_values[3*len(velocity_values)//4]:.1f}")
        print(f"  Max: {velocity_values[-1]:.1f}")
        print(f"  Mean: {sum(velocity_values)/len(velocity_values):.1f}")
    
    # Sample some that would pass
    print(f"\n=== Sample Audio That Would Pass New Criteria ===")
    
    sample_count = 0
    for audio_id, reels in rejected_single_reel.items():
        if sample_count >= 5:
            break
            
        reel = reels[0]
        vel = reel.get('velocity_score', 0.0) or 0.0
        views = reel.get('view_count', 0) or 0
        likes = reel.get('like_count', 0) or 0
        
        passes_velocity = vel > velocity_threshold
        passes_engagement = likes > likes_threshold and views > views_threshold
        
        if passes_velocity or passes_engagement:
            # Get audio title
            audio_title = reel.get('audio_title', 'unknown')
            audio_artist = reel.get('audio_artist', 'unknown')
            
            print(f"\nAudio: {audio_title} by {audio_artist}")
            print(f"  Audio ID: {audio_id}")
            print(f"  Velocity: {vel:.1f} {'[PASS]' if passes_velocity else '[FAIL]'}")
            print(f"  Likes: {likes}, Views: {views} {'[PASS]' if passes_engagement else '[FAIL]'}")
            print(f"  Reason: {'High velocity' if passes_velocity else 'High engagement'}")
            
            sample_count += 1
    
    # Check if this is "huge percentage" or "small, sane percentage"
    pass_percentage = (pass_any_count / len(rejected_single_reel)) * 100
    
    print(f"\n=== Noise Assessment ===")
    print(f"Currently rejected single-reel audio: {len(rejected_single_reel)}")
    print(f"Would pass new criteria: {pass_any_count} ({pass_percentage:.1f}%)")
    
    if pass_percentage < 10:
        print("Assessment: SMALL, SANE percentage (<10%) - Good")
    elif pass_percentage < 25:
        print("Assessment: MODERATE percentage (10-25%) - Acceptable")
    elif pass_percentage < 50:
        print("Assessment: HIGH percentage (25-50%) - May introduce noise")
    else:
        print("Assessment: VERY HIGH percentage (>50%) - Likely too noisy")
    
    return True

if __name__ == '__main__':
    analyze_threshold_distribution()
