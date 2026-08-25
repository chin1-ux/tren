#!/usr/bin/env python3
"""
Test percentile-based thresholds against the rejected audio dataset.
Calculate top 5% and top 1% velocity thresholds from last 7 days of data.
"""

import os
import sys
import io
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client
import numpy as np

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

def test_percentile_thresholds():
    """Test percentile-based thresholds against rejected audio dataset"""
    
    print("=== Percentile-Based Threshold Analysis ===\n")
    
    # Initialize Supabase client
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("ERROR: Supabase credentials not set")
        return False
    
    sb = create_client(url, key)
    
    # Get all reels from last 7 days to calculate velocity percentiles
    print("=== Step 1: Calculate Velocity Percentiles from Last 7 Days ===")
    
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    recent_reels = sb.table('reels') \
        .select('velocity_score') \
        .not_.is_('velocity_score', 'null') \
        .gte('scraped_at', seven_days_ago.isoformat()) \
        .execute()
    
    velocities = [reel.get('velocity_score', 0.0) or 0.0 for reel in recent_reels.data]
    velocities = [v for v in velocities if v > 0]  # Filter out zeros
    
    print(f"Total reels in last 7 days: {len(recent_reels.data)}")
    print(f"Valid velocity scores: {len(velocities)}")
    
    if len(velocities) == 0:
        print("ERROR: No valid velocity scores found")
        return False
    
    # Calculate percentiles
    velocity_array = np.array(velocities)
    top_1_percent_threshold = np.percentile(velocity_array, 99)
    top_5_percent_threshold = np.percentile(velocity_array, 95)
    top_10_percent_threshold = np.percentile(velocity_array, 90)
    
    print(f"\nVelocity Statistics:")
    print(f"  Min: {np.min(velocity_array):.1f}")
    print(f"  25th percentile: {np.percentile(velocity_array, 25):.1f}")
    print(f"  50th percentile (median): {np.percentile(velocity_array, 50):.1f}")
    print(f"  75th percentile: {np.percentile(velocity_array, 75):.1f}")
    print(f"  90th percentile: {np.percentile(velocity_array, 90):.1f}")
    print(f"  95th percentile: {np.percentile(velocity_array, 95):.1f}")
    print(f"  99th percentile: {np.percentile(velocity_array, 99):.1f}")
    print(f"  Max: {np.max(velocity_array):.1f}")
    
    print(f"\nProposed Thresholds:")
    print(f"  Top 1% threshold: {top_1_percent_threshold:.1f}")
    print(f"  Top 5% threshold: {top_5_percent_threshold:.1f}")
    print(f"  Top 10% threshold: {top_10_percent_threshold:.1f}")
    
    # Test against the 924 rejected single-reel audio
    print(f"\n=== Step 2: Test Against Rejected Single-Reel Audio Dataset ===")
    
    # Get single-reel audio NOT in tracked_audio (same as before)
    all_reels = sb.table('reels') \
        .select('audio_id, velocity_score, view_count, like_count') \
        .not_.is_('audio_id', 'null') \
        .execute()
    
    audio_reel_counts = {}
    for reel in all_reels.data:
        aid = reel.get('audio_id')
        if aid:
            if aid not in audio_reel_counts:
                audio_reel_counts[aid] = []
            audio_reel_counts[aid].append(reel)
    
    # Find single-reel audio not in tracked_audio
    tracked_res = sb.table('tracked_audio').select('audio_id').execute()
    tracked_ids = {row['audio_id'] for row in tracked_res.data}
    
    rejected_single_reel = {aid: reels for aid, reels in audio_reel_counts.items() 
                           if len(reels) == 1 and aid not in tracked_ids}
    
    print(f"Rejected single-reel audio count: {len(rejected_single_reel)}")
    
    # Test each percentile threshold
    print(f"\n=== Threshold Comparison Results ===")
    
    thresholds = [
        ("Top 1%", top_1_percent_threshold),
        ("Top 5%", top_5_percent_threshold),
        ("Top 10%", top_10_percent_threshold),
    ]
    
    for label, threshold in thresholds:
        pass_count = 0
        for audio_id, reels in rejected_single_reel.items():
            reel = reels[0]
            vel = reel.get('velocity_score', 0.0) or 0.0
            
            if vel > threshold:
                pass_count += 1
        
        pass_rate = (pass_count / len(rejected_single_reel)) * 100
        print(f"\n{label} (threshold: {threshold:.1f}):")
        print(f"  Would pass: {pass_count} out of {len(rejected_single_reel)}")
        print(f"  Pass rate: {pass_rate:.1f}%")
        
        if pass_rate < 15:
            print(f"  Assessment: GOOD - within 5-15% target range")
        elif pass_rate < 25:
            print(f"  Assessment: ACCEPTABLE - slightly above target")
        else:
            print(f"  Assessment: TOO HIGH - exceeds target range")
    
    # Also test the original engagement threshold alone
    print(f"\n=== Engagement-Only Threshold (Original) ===")
    likes_threshold = 1000
    views_threshold = 10000
    
    engagement_pass_count = 0
    for audio_id, reels in rejected_single_reel.items():
        reel = reels[0]
        views = reel.get('view_count', 0) or 0
        likes = reel.get('like_count', 0) or 0
        
        if likes > likes_threshold and views > views_threshold:
            engagement_pass_count += 1
    
    engagement_pass_rate = (engagement_pass_count / len(rejected_single_reel)) * 100
    print(f"Engagement threshold (likes > {likes_threshold} AND views > {views_threshold}):")
    print(f"  Would pass: {engagement_pass_count} out of {len(rejected_single_reel)}")
    print(f"  Pass rate: {engagement_pass_rate:.1f}%")
    
    # Combined approach: percentile OR engagement
    print(f"\n=== Combined Approach: Top 5% OR Engagement ===")
    combined_pass_count = 0
    for audio_id, reels in rejected_single_reel.items():
        reel = reels[0]
        vel = reel.get('velocity_score', 0.0) or 0.0
        views = reel.get('view_count', 0) or 0
        likes = reel.get('like_count', 0) or 0
        
        passes_velocity = vel > top_5_percent_threshold
        passes_engagement = likes > likes_threshold and views > views_threshold
        
        if passes_velocity or passes_engagement:
            combined_pass_count += 1
    
    combined_pass_rate = (combined_pass_count / len(rejected_single_reel)) * 100
    print(f"Combined (Top 5% OR engagement):")
    print(f"  Would pass: {combined_pass_count} out of {len(rejected_single_reel)}")
    print(f"  Pass rate: {combined_pass_rate:.1f}%")
    
    if combined_pass_rate < 15:
        print(f"  Assessment: GOOD - within 5-15% target range")
    elif combined_pass_rate < 25:
        print(f"  Assessment: ACCEPTABLE - slightly above target")
    else:
        print(f"  Assessment: TOO HIGH - exceeds target range")
    
    return True

if __name__ == '__main__':
    test_percentile_thresholds()
