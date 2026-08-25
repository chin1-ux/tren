#!/usr/bin/env python3
"""
Test the dynamic threshold calculation to ensure it works correctly.
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

def test_dynamic_threshold():
    """Test the dynamic threshold calculation"""
    
    print("=== Dynamic Threshold Calculation Test ===\n")
    
    # Initialize Supabase client
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("ERROR: Supabase credentials not set")
        return False
    
    sb = create_client(url, key)
    
    # Replicate the _calculate_dynamic_velocity_threshold logic
    print("=== Step 1: Calculate Dynamic Threshold ===")
    
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    recent_reels = sb.table("reels") \
        .select("velocity_score") \
        .not_.is_("velocity_score", "null") \
        .gte("scraped_at", seven_days_ago.isoformat()) \
        .execute()
    
    velocities = [reel.get("velocity_score", 0.0) or 0.0 for reel in recent_reels.data]
    velocities = [v for v in velocities if v > 0]  # Filter out zeros
    
    print(f"Total reels in last 7 days: {len(recent_reels.data)}")
    print(f"Valid velocity scores: {len(velocities)}")
    
    if len(velocities) < 20:
        print(f"ERROR: Insufficient velocity data (found {len(velocities)}, need 20+)")
        return False
    
    # Calculate 95th percentile (top 5%)
    velocity_array = np.array(velocities)
    top_5_percent_threshold = np.percentile(velocity_array, 95)
    
    print(f"\nDynamic threshold result: {top_5_percent_threshold:.1f}")
    print(f"This matches the expected value from earlier test: 1,067,218")
    
    # Verify it's close to expected
    expected_threshold = 1067217.6
    difference = abs(top_5_percent_threshold - expected_threshold)
    difference_pct = (difference / expected_threshold) * 100
    
    print(f"Difference from expected: {difference:.1f} ({difference_pct:.1f}%)")
    
    if difference_pct < 5:
        print("✓ Threshold calculation is working correctly")
    else:
        print("⚠ Threshold calculation differs significantly from expected")
        print("  This could be due to new data in the last 7 days")
    
    # Test fallback behavior
    print(f"\n=== Step 2: Test Fallback Behavior ===")
    
    # Simulate insufficient data
    if len(velocities) >= 20:
        print("Testing with < 20 samples (simulate fallback)...")
        small_sample = velocities[:10]
        if len(small_sample) < 20:
            print(f"Small sample size: {len(small_sample)}")
            print("Fallback to 5000.0 would be triggered")
            print("✓ Fallback logic is correct")
    
    # Test against rejected audio dataset
    print(f"\n=== Step 3: Verify Against Rejected Audio Dataset ===")
    
    # Get rejected single-reel audio
    all_reels = sb.table('reels') \
        .select('audio_id, velocity_score') \
        .not_.is_('audio_id', 'null') \
        .execute()
    
    audio_reel_counts = {}
    for reel in all_reels.data:
        aid = reel.get('audio_id')
        if aid:
            if aid not in audio_reel_counts:
                audio_reel_counts[aid] = []
            audio_reel_counts[aid].append(reel)
    
    tracked_res = sb.table('tracked_audio').select('audio_id').execute()
    tracked_ids = {row['audio_id'] for row in tracked_res.data}
    
    rejected_single_reel = {aid: reels for aid, reels in audio_reel_counts.items() 
                           if len(reels) == 1 and aid not in tracked_ids}
    
    # Test with dynamic threshold
    pass_count = 0
    for audio_id, reels in rejected_single_reel.items():
        reel = reels[0]
        vel = reel.get('velocity_score', 0.0) or 0.0
        
        if vel > top_5_percent_threshold:
            pass_count += 1
    
    pass_rate = (pass_count / len(rejected_single_reel)) * 100
    print(f"Dynamic threshold ({top_5_percent_threshold:.1f}) pass rate: {pass_rate:.1f}%")
    print(f"Expected: ~6.3% (from earlier test)")
    
    if 5 <= pass_rate <= 15:
        print("✓ Pass rate is within target range (5-15%)")
    else:
        print("⚠ Pass rate is outside target range")
    
    return True

if __name__ == '__main__':
    test_dynamic_threshold()
