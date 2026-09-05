#!/usr/bin/env python3
"""
Check trends by status
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

print("=" * 80)
print("TREND STATUS BREAKDOWN")
print("=" * 80)

# Get trends by status
statuses = ['rising', 'emerging', 'peaked', 'expired']

for status in statuses:
    try:
        res = sb.table('trends').select('*').eq('status', status).execute()
        count = len(res.data)
        print(f"\n{status.upper()}: {count} trends")
        
        # Show some examples
        if count > 0:
            print("  Examples:")
            for i, trend in enumerate(res.data[:3], 1):
                audio_title = trend.get('audio_title', 'N/A')[:50]
                created_at = trend.get('created_at', 'N/A')
                print(f"    {i}. {audio_title} (created: {created_at})")
    except Exception as e:
        print(f"Error checking {status}: {e}")

# Total trends
try:
    total_res = sb.table('trends').select('id', count='exact').execute()
    total_count = total_res.count if hasattr(total_res, 'count') else len(total_res.data)
    print(f"\nTOTAL TRENDS: {total_count}")
except Exception as e:
    print(f"Error getting total: {e}")

print("\n" + "=" * 80)