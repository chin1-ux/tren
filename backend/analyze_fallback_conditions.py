#!/usr/bin/env python3
"""
Analyze when the <20 samples fallback would actually trigger.
Is 5000.0 a safe fallback or should we skip enrollment instead?
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

def analyze_fallback_conditions():
    """Analyze when <20 samples fallback would trigger"""
    
    print("=== Fallback Condition Analysis ===\n")
    
    # Initialize Supabase client
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("ERROR: Supabase credentials not set")
        return False
    
    sb = create_client(url, key)
    
    # Check current data volume over different time windows
    print("=== Current Data Volume Analysis ===")
    
    time_windows = [1, 3, 7, 14, 30]  # days
    
    for days in time_windows:
        time_ago = datetime.now(timezone.utc) - timedelta(days=days)
        
        reels_res = sb.table('reels') \
            .select('velocity_score') \
            .not_.is_('velocity_score', 'null') \
            .gte('scraped_at', time_ago.isoformat()) \
            .execute()
        
        velocities = [reel.get('velocity_score', 0.0) or 0.0 for reel in reels_res.data]
        velocities = [v for v in velocities if v > 0]
        
        print(f"Last {days} days: {len(velocities)} valid velocity scores")
        
        if len(velocities) < 20:
            print(f"  ⚠ WARNING: Would trigger fallback (<20 samples)")
    
    # Check recent scraping patterns
    print(f"\n=== Recent Scraping Pattern ===")
    
    # Get reels from last 24 hours to check current scraping rate
    one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    
    recent_reels = sb.table('reels') \
        .select('scraped_at') \
        .gte('scraped_at', one_day_ago.isoformat()) \
        .execute()
    
    print(f"Reels scraped in last 24 hours: {len(recent_reels.data)}")
    
    if len(recent_reels.data) > 0:
        # Estimate daily scraping rate
        daily_rate = len(recent_reels.data)
        print(f"Estimated daily scraping rate: {daily_rate} reels/day")
        
        # How many days to reach 20 samples?
        days_to_20 = 20 / daily_rate if daily_rate > 0 else float('inf')
        print(f"Days to reach 20 samples at current rate: {days_to_20:.1f}")
        
        if days_to_20 > 7:
            print(f"  ⚠ WARNING: Would take >7 days to accumulate 20 samples")
    
    # Historical check: has this ever been <20 in the last 30 days?
    print(f"\n=== Historical Fallback Risk Assessment ===")
    
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    
    # Check day by day for the last 30 days
    fallback_days = []
    
    for day_offset in range(30):
        day_start = datetime.now(timezone.utc) - timedelta(days=day_offset + 1)
        day_end = datetime.now(timezone.utc) - timedelta(days=day_offset)
        
        day_reels = sb.table('reels') \
            .select('velocity_score') \
            .not_.is_('velocity_score', 'null') \
            .gte('scraped_at', day_start.isoformat()) \
            .lt('scraped_at', day_end.isoformat()) \
            .execute()
        
        day_velocities = [reel.get('velocity_score', 0.0) or 0.0 for reel in day_reels.data]
        day_velocities = [v for v in day_velocities if v > 0]
        
        if len(day_velocities) < 20:
            fallback_days.append(day_start.strftime('%Y-%m-%d'))
    
    if fallback_days:
        print(f"Days in last 30 with <20 samples: {len(fallback_days)}")
        print(f"Affected dates: {fallback_days}")
    else:
        print(f"No days in last 30 with <20 samples")
        print(f"Fallback is unlikely to trigger in normal operation")
    
    # Fallback safety analysis
    print(f"\n=== Fallback Safety Analysis ===")
    
    print("Current fallback value: 5000.0")
    print("Known impact of 5000.0 threshold: 98.5% pass rate (TOO HIGH)")
    print()
    
    print("Fallback would trigger in these scenarios:")
    print("1. Cold start (new deployment with no historical data)")
    print("2. Major scraping interruption (>7 days)")
    print("3. Data corruption/loss affecting velocity scores")
    print()
    
    print("Assessment:")
    if len(fallback_days) == 0 and daily_rate > 20:
        print("✓ Fallback is LOW RISK:")
        print("  - Current scraping rate is healthy")
        print("  - No historical fallback triggers in last 30 days")
        print("  - 5000.0 fallback only in genuine edge cases")
        print("  - Cold start scenario: high enrollment rate is acceptable")
    else:
        print("⚠ Fallback is MODERATE RISK:")
        print("  - Fallback has triggered historically")
        print("  - Current scraping rate may be insufficient")
        print("  - 5000.0 fallback could cause enrollment flood")
    
    print()
    print("Alternative: Skip velocity-based enrollment when data insufficient")
    print("  - Safer: avoids known-bad threshold")
    print("  - Trade-off: misses some early high-velocity signals in cold start")
    print("  - Impact: relies on 2+ reels criteria during cold start")
    
    return True

if __name__ == '__main__':
    analyze_fallback_conditions()
