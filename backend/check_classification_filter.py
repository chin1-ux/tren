#!/usr/bin/env python3
"""
Check the llm_classification_status filter issue
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
print("LLM_CLASSIFICATION_STATUS FILTER ANALYSIS")
print("=" * 80)

# Check all rising trends and their classification status
print("\nClassification status distribution for all rising trends:")
try:
    all_rising = sb.table("trends").select("*").eq("status", "rising").execute()
    
    status_counts = {}
    for trend in all_rising.data:
        status = trend.get('llm_classification_status', 'NULL')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print("\nStatus distribution:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")
    
    # Show specific examples of trends that are being filtered out
    print("\nExamples of trends being filtered out (status not in ['completed', 'not_needed']):")
    filtered_count = 0
    for trend in all_rising.data:
        status = trend.get('llm_classification_status', 'NULL')
        if status not in ["completed", "not_needed"]:
            if filtered_count < 5:  # Show first 5 examples
                print(f"  ID: {trend.get('id')}, Title: '{trend.get('audio_title', 'unknown')}', Status: {status}")
            filtered_count += 1
    
    print(f"\nTotal trends filtered out: {filtered_count}")
    print(f"Total trends passing filter: {len(all_rising.data) - filtered_count}")
    
except Exception as e:
    print(f"Error: {e}")

# Check if this is a recent regression
print("\n" + "=" * 80)
print("REGRESSION CHECK - WHEN DID THIS START?")
print("=" * 80)

print("\nChecking trends created in last 3 days vs older trends:")
from datetime import datetime, timezone, timedelta

three_days_ago = datetime.now(timezone.utc) - timedelta(days=3)
recent_trends = sb.table("trends").select("*").gte("first_detected_at", three_days_ago.isoformat()).eq("status", "rising").execute()
older_trends = sb.table("trends").select("*").lt("first_detected_at", three_days_ago.isoformat()).eq("status", "rising").execute()

print(f"\nRecent rising trends (last 3 days): {len(recent_trends.data)}")
print(f"Older rising trends: {len(older_trends.data)}")

# Check classification status for recent vs older
recent_status_counts = {}
for trend in recent_trends.data:
    status = trend.get('llm_classification_status', 'NULL')
    recent_status_counts[status] = recent_status_counts.get(status, 0) + 1

older_status_counts = {}
for trend in older_trends.data:
    status = trend.get('llm_classification_status', 'NULL')
    older_status_counts[status] = older_status_counts.get(status, 0) + 1

print("\nRecent trends classification status:")
for status, count in sorted(recent_status_counts.items()):
    print(f"  {status}: {count}")

print("\nOlder trends classification status:")
for status, count in sorted(older_status_counts.items()):
    print(f"  {status}: {count}")

print("\n" + "=" * 80)