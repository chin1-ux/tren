#!/usr/bin/env python3
"""
Check rising trends in detail
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
print("RISING TRENDS ANALYSIS")
print("=" * 80)

# Get rising trends
rising_res = sb.table('trends').select('*').eq('status', 'rising').order('id', desc=True).execute()
rising_trends = rising_res.data

print(f"\nTotal rising trends: {len(rising_trends)}")

if rising_trends:
    print("\nRising trends details:")
    for i, trend in enumerate(rising_trends, 1):
        trend_id = trend.get('id', 'N/A')
        audio_title = trend.get('audio_title', 'N/A')
        created_at = trend.get('created_at', 'N/A')
        discovery_source = trend.get('discovery_source', 'N/A')
        
        # Parse and format date
        if created_at and created_at != 'N/A':
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                time_ago = datetime.now(timezone.utc) - dt
                hours_ago = time_ago.total_seconds() / 3600
                created_str = f"{created_at} ({hours_ago:.1f} hours ago)"
            except:
                created_str = created_at
        else:
            created_str = 'N/A'
        
        print(f"{i}. ID: {trend_id}")
        print(f"   Title: {audio_title}")
        print(f"   Status: rising")
        print(f"   Created: {created_str}")
        print(f"   Discovery Source: {discovery_source}")
        print()

# Check recent reels
reels_res = sb.table('reels').select('audio_id, created_at').order('created_at', desc=True).limit(20).execute()
recent_reels = reels_res.data

print(f"\nRecent 20 reels:")
for i, reel in enumerate(recent_reels, 1):
    audio_id = reel.get('audio_id', 'N/A')
    created_at = reel.get('created_at', 'N/A')
    
    if created_at and created_at != 'N/A':
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            time_ago = datetime.now(timezone.utc) - dt
            hours_ago = time_ago.total_seconds() / 3600
            created_str = f"{hours_ago:.1f} hours ago"
        except:
            created_str = created_at
    else:
        created_str = 'N/A'
    
    print(f"{i}. Audio ID: {audio_id} | Created: {created_str}")

print("\n" + "=" * 80)