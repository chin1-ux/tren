#!/usr/bin/env python3
"""
Check snapshot persistence and RLS policies on trends/rising table
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
print("SNAPSHOT PERSISTENCE CHECK")
print("=" * 80)

# Check recent trend snapshots
print("\nRecent trend snapshots (last 24 hours):")
try:
    twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    snapshots_res = sb.table('trend_snapshots').select('*').gte('captured_at', twenty_four_hours_ago.isoformat()).order('captured_at', desc=True).limit(20).execute()
    snapshots = snapshots_res.data
    
    print(f"Total snapshots in last 24 hours: {len(snapshots)}")
    
    # Group by captured_at to see runs
    from collections import defaultdict
    snapshot_groups = defaultdict(list)
    for snap in snapshots:
        captured_at = snap.get('captured_at', 'unknown')
        # Round to nearest hour for grouping
        if captured_at != 'unknown':
            try:
                dt = datetime.fromisoformat(captured_at.replace('Z', '+00:00'))
                hour_key = dt.strftime('%Y-%m-%d %H:00')
                snapshot_groups[hour_key].append(snap)
            except:
                snapshot_groups[captured_at].append(snap)
        else:
            snapshot_groups[captured_at].append(snap)
    
    print("\nSnapshots by hour:")
    for hour, snaps in sorted(snapshot_groups.items()):
        print(f"  {hour}: {len(snaps)} snapshots")
        
except Exception as e:
    print(f"Error checking snapshots: {e}")

# Check snapshot coverage for current rising trends
print("\n" + "=" * 80)
print("SNAPSHOT COVERAGE FOR CURRENT RISING TRENDS")
print("=" * 80)

rising_trends = sb.table('trends').select('*').eq('status', 'rising').execute()
print(f"\nTotal rising trends: {len(rising_trends.data)}")

trends_with_snapshots = 0
trends_without_snapshots = 0

for trend in rising_trends.data:
    trend_id = trend.get('id')
    snapshots_res = sb.table('trend_snapshots').select('*').eq('trend_id', trend_id).execute()
    if snapshots_res.data:
        trends_with_snapshots += 1
    else:
        trends_without_snapshots += 1
        audio_title = trend.get('audio_title', 'unknown')
        print(f"  Trend ID {trend_id} ('{audio_title}'): NO snapshots")

print(f"\nTrends with snapshots: {trends_with_snapshots}")
print(f"Trends without snapshots: {trends_without_snapshots}")

# Check RLS policies (we can't directly check RLS, but we can test access)
print("\n" + "=" * 80)
print("RLS POLICY ACCESS TEST")
print("=" * 80)

print("\nTesting access to trends table with current credentials:")
try:
    test_res = sb.table('trends').select('id', count='exact').eq('status', 'rising').execute()
    rising_count_via_api = len(test_res.data)
    print(f"  Rising trends count via API: {rising_count_via_api}")
except Exception as e:
    print(f"  Error accessing trends table: {e}")

# Compare with direct count
print("\nDirect count from trends table:")
try:
    all_rising = sb.table('trends').select('*').eq('status', 'rising').execute()
    print(f"  Rising trends count direct: {len(all_rising.data)}")
except Exception as e:
    print(f"  Error: {e}")

print("\n" + "=" * 80)