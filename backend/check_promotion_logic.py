#!/usr/bin/env python3
"""
Check emerging->rising promotion logic - candidates evaluated vs promoted per day
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime, timezone, timedelta

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

if not url or not key:
    print("ERROR: Supabase credentials not set")
    exit(1)

sb = create_client(url, key)

print("=" * 80)
print("EMERGING->RISING PROMOTION LOGIC ANALYSIS")
print("=" * 80)

# Check current status distribution
print("\nCurrent trend status distribution:")
try:
    status_res = sb.table('trends').select('status', count='exact').execute()
    # Since count might not work as expected, let's get all and count manually
    all_trends = sb.table('trends').select('status').execute()
    status_counts = {}
    for trend in all_trends.data:
        status = trend.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")
except Exception as e:
    print(f"Error checking status distribution: {e}")

# Check trends created in last 3 days vs current rising trends
print("\n" + "=" * 80)
print("TRENDS CREATED IN LAST 3 DAYS VS CURRENT RISING")
print("=" * 80)

three_days_ago = datetime.now(timezone.utc) - timedelta(days=3)
recent_trends_res = sb.table('trends').select('*').gte('first_detected_at', three_days_ago.isoformat()).execute()
recent_trends = recent_trends_res.data

print(f"\nTotal trends created in last 3 days: {len(recent_trends)}")

# Count how many of these are currently rising vs emerging
currently_rising = sum(1 for t in recent_trends if t.get('status') == 'rising')
currently_emerging = sum(1 for t in recent_trends if t.get('status') == 'emerging')

print(f"Currently rising (from last 3 days): {currently_rising}")
print(f"Currently emerging (from last 3 days): {currently_emerging}")

# Check promotion reasons for rising trends
print("\n" + "=" * 80)
print("PROMOTION REASONS FOR CURRENT RISING TRENDS")
print("=" * 80)

rising_trends = sb.table('trends').select('*').eq('status', 'rising').execute()
promotion_reasons = {}
for trend in rising_trends.data:
    reason = trend.get('promotion_reason', 'unknown')
    promotion_reasons[reason] = promotion_reasons.get(reason, 0) + 1

print("\nPromotion reasons:")
for reason, count in sorted(promotion_reasons.items()):
    print(f"  {reason}: {count}")

# Check velocity distribution for all trends
print("\n" + "=" * 80)
print("VELOCITY DISTRIBUTION FOR ALL TRENDS (Last 3 days)")
print("=" * 80)

velocities = [t.get('velocity_avg', 0) for t in recent_trends if isinstance(t.get('velocity_avg'), (int, float))]
if velocities:
    velocities_sorted = sorted(velocities)
    print(f"\nTotal velocity scores: {len(velocities)}")
    print(f"Min: {min(velocities):.2f}")
    print(f"Max: {max(velocities):.2f}")
    print(f"Mean: {sum(velocities)/len(velocities):.2f}")
    
    # Calculate percentiles
    import statistics
    p50 = statistics.median(velocities)
    p75 = velocities_sorted[int(len(velocities) * 0.75)] if len(velocities) > 0 else 0
    p90 = velocities_sorted[int(len(velocities) * 0.90)] if len(velocities) > 0 else 0
    p95 = velocities_sorted[int(len(velocities) * 0.95)] if len(velocities) > 0 else 0
    
    print(f"50th percentile (median): {p50:.2f}")
    print(f"75th percentile: {p75:.2f}")
    print(f"90th percentile: {p90:.2f}")
    print(f"95th percentile: {p95:.2f}")
    
    # Current rising baseline calculation
    print(f"\nRising baseline (1.5x median): {p50 * 1.5:.2f}")
else:
    print("No velocity data available")

# Check for NULL values in critical fields
print("\n" + "=" * 80)
print("NULL VALUE CHECKS IN CRITICAL FIELDS")
print("=" * 80)

null_audio_title = sum(1 for t in recent_trends if not t.get('audio_title'))
null_audio_artist = sum(1 for t in recent_trends if not t.get('audio_artist'))
null_velocity = sum(1 for t in recent_trends if t.get('velocity_avg') is None)
null_first_detected = sum(1 for t in recent_trends if not t.get('first_detected_at'))

print(f"\nTrends with NULL audio_title: {null_audio_title}")
print(f"Trends with NULL audio_artist: {null_audio_artist}")
print(f"Trends with NULL velocity_avg: {null_velocity}")
print(f"Trends with NULL first_detected_at: {null_first_detected}")

print("\n" + "=" * 80)