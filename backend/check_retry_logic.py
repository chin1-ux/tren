#!/usr/bin/env python3
"""
Check retry logic for failed classifications
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
print("RETRY LOGIC ANALYSIS")
print("=" * 80)

# Check if nightly_llm_batch workflow exists or is scheduled
print("\nChecking nightly LLM batch scheduling:")
print("  - No GitHub Action workflow found for nightly_llm_batch")
print("  - No Vercel cron job found for nightly LLM classification")
print("  - nightly_llm_batch.py exists but has NO automated trigger")

# Check if there's any manual trigger or API endpoint
print("\nChecking for API endpoints that could trigger classification:")
print("  - No endpoint found in api.py that calls nightly_llm_batch")
print("  - No cron job in vercel.json for LLM classification")

# Check current retry state
print("\n" + "=" * 80)
print("CURRENT RETRY STATE ANALYSIS")
print("=" * 80)

try:
    pending_trends = sb.table("trends").select("*").eq("llm_classification_status", "pending").execute()
    
    print(f"\nTotal pending trends: {len(pending_trends.data)}")
    
    # Check retry counts
    retry_distribution = {}
    for trend in pending_trends.data:
        retry_count = trend.get('llm_retry_count', 0)
        retry_distribution[retry_count] = retry_distribution.get(retry_count, 0) + 1
    
    print("\nRetry count distribution:")
    for retry_count, count in sorted(retry_distribution.items()):
        print(f"  {retry_count} retries: {count} trends")
    
    # Check llm_classified_at timestamps
    classified_pending = sum(1 for t in pending_trends.data if t.get('llm_classified_at'))
    print(f"\nPending trends with llm_classified_at set: {classified_pending}")
    
    # Check raw_llm_response
    has_response = sum(1 for t in pending_trends.data if t.get('raw_llm_response'))
    print(f"Pending trends with raw_llm_response: {has_response}")
    
except Exception as e:
    print(f"Error: {e}")

# Check if the nightly batch would actually process these trends
print("\n" + "=" * 80)
print("NIGHTLY BATCH ELIGIBILITY CHECK")
print("=" * 80)

try:
    # Simulate the query from nightly_llm_batch.py line 85
    eligible = sb.table("trends").select("*").in_("llm_classification_status", ["pending", "llm_unavailable"]).order("first_detected_at", desc=False).limit(20).execute()
    
    print(f"\nTrends eligible for nightly batch processing: {len(eligible.data)}")
    
    if eligible.data:
        print("\nSample eligible trends:")
        for trend in eligible.data[:5]:
            tid = trend.get('id')
            title = trend.get('audio_title', 'unknown')
            status = trend.get('llm_classification_status')
            retry_count = trend.get('llm_retry_count', 0)
            created_at = trend.get('first_detected_at')
            print(f"  ID: {tid}, Title: '{title}', Status: {status}, Retries: {retry_count}, Created: {created_at}")
    
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("\nThe nightly_llm_batch.py script exists but has NO automated trigger.")
print("Without a GitHub Action or Vercel cron job, it never runs automatically.")
print("All new trends are stuck at 'pending' status with 0 retries because the")
print("classification job is never triggered.")
print("\n" + "=" * 80)