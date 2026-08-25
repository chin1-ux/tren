#!/usr/bin/env python3
"""
Check recent trends in the database
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

if not url or not key:
    print("ERROR: Supabase credentials not set")
    exit(1)

sb = create_client(url, key)

print("=" * 60)
print("RECENT TRENDS CHECK")
print("=" * 60)

# Get total count
total_res = sb.table('trends').select('id', count='exact').execute()
total_count = total_res.count if hasattr(total_res, 'count') else len(total_res.data)
print(f"\nTotal trends in database: {total_count}")

# Get recent trends (without date filter first)
recent_res = sb.table('trends').select('*').order('id', desc=True).limit(10).execute()
recent_trends = recent_res.data

print(f"\nTop 10 most recent trends (by ID):")
for i, trend in enumerate(recent_trends, 1):
    trend_id = trend.get('id', 'N/A')
    audio_title = trend.get('audio_title', 'N/A')
    status = trend.get('status', 'N/A')
    # Try to find any date-like field
    date_field = None
    for key in trend.keys():
        if 'date' in key.lower() or 'time' in key.lower() or 'created' in key.lower():
            date_field = trend.get(key)
            break
    print(f"{i}. ID: {trend_id} | {audio_title} | status: {status} | date: {date_field or 'N/A'}")

# Check rising trends specifically
rising_res = sb.table('trends').select('*').eq('status', 'rising').order('id', desc=True).limit(5).execute()
rising_trends = rising_res.data

print(f"\nRising trends: {len(rising_trends)}")
for i, trend in enumerate(rising_trends, 1):
    trend_id = trend.get('id', 'N/A')
    audio_title = trend.get('audio_title', 'N/A')
    print(f"{i}. ID: {trend_id} | {audio_title}")

print("\n" + "=" * 60)
