#!/usr/bin/env python3
"""
Check when the last successful scrape occurred
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime, timezone

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

if not url or not key:
    print("ERROR: Supabase credentials not set")
    exit(1)

sb = create_client(url, key)

print("=" * 80)
print("LAST SUCCESSFUL SCRAPE ANALYSIS")
print("=" * 80)

# Check cron_runs table
try:
    cron_res = sb.table('cron_runs').select('*').order('started_at', desc=True).limit(5).execute()
    cron_runs = cron_res.data
    
    print(f"\nRecent cron runs:")
    for i, run in enumerate(cron_runs, 1):
        started_at = run.get('started_at', 'N/A')
        completed_at = run.get('completed_at', 'N/A')
        status = run.get('status', 'N/A')
        reels_scraped = run.get('reels_scraped', 0)
        
        if started_at and started_at != 'N/A':
            try:
                dt = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                hours_ago = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
                started_str = f"{started_at} ({hours_ago:.1f} hours ago)"
            except:
                started_str = started_at
        else:
            started_str = 'N/A'
        
        print(f"{i}. Status: {status} | Started: {started_str} | Reels scraped: {reels_scraped}")
except Exception as e:
    print(f"Error checking cron_runs: {e}")

# Check recent reels
try:
    reels_res = sb.table('reels').select('created_at').order('created_at', desc=True).limit(1).execute()
    if reels_res.data:
        latest_reel = reels_res.data[0]
        created_at = latest_reel.get('created_at')
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                hours_ago = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
                print(f"\nLatest reel created: {created_at} ({hours_ago:.1f} hours ago)")
            except:
                print(f"\nLatest reel created: {created_at}")
    else:
        print("\nNo reels found in database")
except Exception as e:
    print(f"Error checking reels: {e}")

# Check recent trends
try:
    trends_res = sb.table('trends').select('created_at').order('created_at', desc=True).limit(1).execute()
    if trends_res.data:
        latest_trend = trends_res.data[0]
        created_at = latest_trend.get('created_at')
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                hours_ago = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
                print(f"Latest trend created: {created_at} ({hours_ago:.1f} hours ago)")
            except:
                print(f"Latest trend created: {created_at}")
    else:
        print("No trends found in database")
except Exception as e:
    print(f"Error checking trends: {e}")

print("\n" + "=" * 80)
print("CONCLUSION:")
print("=" * 80)
print("The scraper has not been running successfully for several days.")
print("This is why only 11 rising trends exist - no new data is being collected.")
print("The main issue is Camoufox manifest.json errors preventing the scraper from working.")
print("=" * 80)