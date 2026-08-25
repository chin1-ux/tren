#!/usr/bin/env python3
"""
Check LLM classification history and failure patterns
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
print("LLM CLASSIFICATION HISTORY ANALYSIS")
print("=" * 80)

# Check trends by classification status and creation date
print("\nClassification status by creation date:")
try:
    all_trends = sb.table("trends").select("*").order("first_detected_at", desc=True).limit(100).execute()
    
    # Group by date
    from collections import defaultdict
    daily_classification = defaultdict(lambda: defaultdict(int))
    
    for trend in all_trends.data:
        created_at = trend.get('first_detected_at')
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                date_key = dt.strftime('%Y-%m-%d')
                status = trend.get('llm_classification_status', 'unknown')
                daily_classification[date_key][status] += 1
            except:
                pass
    
    # Show last 7 days
    print("\nLast 7 days of classification:")
    for date in sorted(daily_classification.keys(), reverse=True)[:7]:
        print(f"\n{date}:")
        for status, count in sorted(daily_classification[date].items()):
            print(f"  {status}: {count}")
            
except Exception as e:
    print(f"Error: {e}")

# Check retry counts for pending trends
print("\n" + "=" * 80)
print("RETRY COUNT ANALYSIS FOR PENDING TRENDS")
print("=" * 80)

try:
    pending_trends = sb.table("trends").select("*").eq("llm_classification_status", "pending").execute()
    
    retry_counts = {}
    for trend in pending_trends.data:
        retry_count = trend.get('llm_retry_count', 0)
        retry_counts[retry_count] = retry_counts.get(retry_count, 0) + 1
    
    print("\nRetry count distribution for pending trends:")
    for retry_count, count in sorted(retry_counts.items()):
        print(f"  {retry_count} retries: {count} trends")
        
    # Check if any have llm_classified_at set despite being pending
    classified_but_pending = sum(1 for t in pending_trends.data if t.get('llm_classified_at'))
    print(f"\nPending trends with llm_classified_at set: {classified_but_pending}")
    
except Exception as e:
    print(f"Error: {e}")

# Check when the last successfully classified trend was created
print("\n" + "=" * 80)
print("LAST SUCCESSFUL CLASSIFICATION TIME")
print("=" * 80)

try:
    completed_trends = sb.table("trends").select("*").in_("llm_classification_status", ["completed", "not_needed"]).order("llm_classified_at", desc=True).limit(5).execute()
    
    if completed_trends.data:
        print("\nLast 5 successfully classified trends:")
        for trend in completed_trends.data:
            classified_at = trend.get('llm_classified_at')
            created_at = trend.get('first_detected_at')
            status = trend.get('llm_classification_status')
            title = trend.get('audio_title', 'unknown')
            
            print(f"  Title: '{title}'")
            print(f"    Status: {status}")
            print(f"    Created: {created_at}")
            print(f"    Classified: {classified_at}")
            print()
    else:
        print("No successfully classified trends found")
        
except Exception as e:
    print(f"Error: {e}")

# Check llm_unavailable trends
print("\n" + "=" * 80)
print("LLM_UNAVAILABLE TRENDS")
print("=" * 80)

try:
    unavailable_trends = sb.table("trends").select("*").eq("llm_classification_status", "llm_unavailable").execute()
    print(f"\nTotal llm_unavailable trends: {len(unavailable_trends.data)}")
    
    if unavailable_trends.data:
        print("\nExamples of llm_unavailable trends:")
        for trend in unavailable_trends.data[:5]:
            retry_count = trend.get('llm_retry_count', 0)
            title = trend.get('audio_title', 'unknown')
            created_at = trend.get('first_detected_at')
            print(f"  Title: '{title}', Retries: {retry_count}, Created: {created_at}")
            
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 80)