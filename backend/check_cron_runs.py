#!/usr/bin/env python3
"""
Check cron runs for the last few days
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
print("CRON RUNS ANALYSIS (Last 10 runs)")
print("=" * 80)

# Get recent cron runs
res = sb.table('cron_runs').select('*').order('run_at', desc=True).limit(10).execute()

print("\nRecent cron runs:")
for run in res.data:
    run_at = run.get('run_at', 'N/A')
    reels_scraped = run.get('reels_scraped', 0)
    new_reels_count = run.get('new_reels_count', 0)
    status = run.get('status', 'N/A')
    stage = run.get('stage', 'N/A')
    cutoff_reason = run.get('cutoff_reason', 'N/A')
    
    if run_at and run_at != 'N/A':
        try:
            dt = datetime.fromisoformat(run_at.replace('Z', '+00:00'))
            hours_ago = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
            run_at_str = f"{run_at} ({hours_ago:.1f} hours ago)"
        except:
            run_at_str = run_at
    else:
        run_at_str = 'N/A'
    
    print(f"Run: {run_at_str}")
    print(f"  Status: {status} | Stage: {stage}")
    print(f"  Reels scraped: {reels_scraped} | New reels: {new_reels_count}")
    if cutoff_reason and cutoff_reason != 'N/A':
        print(f"  Cutoff reason: {cutoff_reason}")
    print()

# Check reels ingested per day for last 5 days
print("=" * 80)
print("NEW REELS INGESTED PER DAY (Last 5 days)")
print("=" * 80)

for i in range(5):
    day_start = (datetime.now(timezone.utc) - timedelta(days=i+1)).replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = (datetime.now(timezone.utc) - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    reels_res = sb.table('reels').select('id', count='exact').gte('created_at', day_start.isoformat()).lt('created_at', day_end.isoformat()).execute()
    count = reels_res.count if hasattr(reels_res, 'count') else len(reels_res.data)
    
    print(f"{day_start.strftime('%Y-%m-%d')}: {count} new reels")

print("=" * 80)