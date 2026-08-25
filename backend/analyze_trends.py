#!/usr/bin/env python3
"""
Analyze trends data to understand why there are so few active trends
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Initialize Supabase client
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
if not url or not key:
    print("ERROR: Supabase credentials not set in environment")
    exit(1)

sb = create_client(url, key)

def analyze_trends():
    print("="*80)
    print("TRENDS DATA ANALYSIS")
    print("="*80)
    
    # Get all trends
    print("\n1. Fetching all trends...")
    result = sb.table('trends').select('*').execute()
    trends = result.data if result.data else []
    print(f"   Total trends: {len(trends)}")
    
    if not trends:
        print("   No trends found in database")
        return
    
    # Analyze by status
    print("\n2. Analyzing trends by status...")
    status_counts = {}
    for trend in trends:
        status = trend.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print("   Status distribution:")
    for status, count in sorted(status_counts.items()):
        print(f"   - {status}: {count}")
    
    # Analyze by created_at
    print("\n3. Analyzing trends by creation date...")
    now = datetime.now()
    time_ranges = {
        'Last 24 hours': 0,
        'Last 7 days': 0,
        'Last 30 days': 0,
        'Older than 30 days': 0
    }
    
    for trend in trends:
        created_at = trend.get('created_at')
        if created_at:
            try:
                # Handle both naive and aware datetimes
                if 'Z' in created_at or '+' in created_at:
                    created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if created_dt.tzinfo is not None:
                        now_aware = datetime.now(created_dt.tzinfo)
                        age = now_aware - created_dt
                    else:
                        age = now - created_dt
                else:
                    created_dt = datetime.fromisoformat(created_at)
                    age = now - created_dt
                
                hours = age.total_seconds() / 3600
                if hours <= 24:
                    time_ranges['Last 24 hours'] += 1
                elif hours <= 168:  # 7 days
                    time_ranges['Last 7 days'] += 1
                elif hours <= 720:  # 30 days
                    time_ranges['Last 30 days'] += 1
                else:
                    time_ranges['Older than 30 days'] += 1
            except Exception as e:
                print(f"   Warning: Invalid timestamp for trend {trend.get('id')}: {e}")
    
    print("   Time distribution:")
    for range_name, count in time_ranges.items():
        print(f"   - {range_name}: {count}")
    
    # Analyze rising vs emerging
    print("\n4. Analyzing active trends (rising + emerging)...")
    active_trends = [t for t in trends if t.get('status') in ['rising', 'emerging']]
    print(f"   Active trends: {len(active_trends)}")
    
    if active_trends:
        print("\n   Active trends details:")
        for trend in active_trends[:10]:  # Show first 10
            print(f"   - ID: {trend.get('id')}, Status: {trend.get('status')}, Song: {trend.get('song', 'N/A')[:50]}, Created: {trend.get('created_at', 'N/A')}")
    
    # Analyze peaked/expired trends
    print("\n5. Analyzing inactive trends (peaked + expired)...")
    inactive_trends = [t for t in trends if t.get('status') in ['peaked', 'expired']]
    print(f"   Inactive trends: {len(inactive_trends)}")
    
    # Check for trends without status
    print("\n6. Checking for trends without status...")
    no_status = [t for t in trends if not t.get('status')]
    print(f"   Trends without status: {len(no_status)}")
    
    # Check for trends without created_at
    print("\n7. Checking for trends without created_at...")
    no_created_at = [t for t in trends if not t.get('created_at')]
    print(f"   Trends without created_at: {len(no_created_at)}")
    
    # Analyze velocity scores
    print("\n8. Analyzing velocity scores...")
    velocities = [t.get('velocity_avg') for t in trends if t.get('velocity_avg')]
    if velocities:
        avg_velocity = sum(velocities) / len(velocities)
        max_velocity = max(velocities)
        min_velocity = min(velocities)
        print(f"   Average velocity: {avg_velocity:.2f}")
        print(f"   Max velocity: {max_velocity:.2f}")
        print(f"   Min velocity: {min_velocity:.2f}")
    
    # Check recent trends that should be active
    print("\n9. Checking recent trends that should be active...")
    recent_trends = []
    for trend in trends:
        created_at = trend.get('created_at')
        if created_at:
            try:
                if 'Z' in created_at or '+' in created_at:
                    created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if created_dt.tzinfo is not None:
                        now_aware = datetime.now(created_dt.tzinfo)
                        age = now_aware - created_dt
                    else:
                        age = now - created_dt
                else:
                    created_dt = datetime.fromisoformat(created_at)
                    age = now - created_dt
                
                hours = age.total_seconds() / 3600
                if hours <= 48:  # Trends from last 48 hours
                    recent_trends.append(trend)
            except:
                pass
    
    print(f"   Trends from last 48 hours: {len(recent_trends)}")
    if recent_trends:
        print("\n   Recent trends and their status:")
        for trend in recent_trends[:10]:
            print(f"   - ID: {trend.get('id')}, Status: {trend.get('status')}, Song: {trend.get('song', 'N/A')[:50]}, Age: {trend.get('created_at', 'N/A')}")
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)

if __name__ == '__main__':
    analyze_trends()