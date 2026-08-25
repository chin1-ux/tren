#!/usr/bin/env python3
"""
Timeout fallback for pending trends
Promotes trends stuck in 'pending' status for >24h to 'not_needed'
This ensures graceful degradation if the nightly batch fails silently
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
print("PENDING TRENDS TIMEOUT FALLBACK")
print("=" * 80)

# Find trends stuck in pending for >24 hours
twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)

try:
    pending_trends = sb.table("trends").select("*").eq("llm_classification_status", "pending").execute()
    
    if not pending_trends.data:
        print("\nNo pending trends found.")
        exit(0)
    
    print(f"\nTotal pending trends: {len(pending_trends.data)}")
    
    # Filter trends stuck for >24 hours
    stuck_trends = []
    for trend in pending_trends.data:
        created_at = trend.get('first_detected_at')
        if created_at:
            try:
                created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                # Handle offset-naive datetimes by assuming UTC
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=timezone.utc)
                if created_dt < twenty_four_hours_ago:
                    stuck_trends.append(trend)
            except Exception as e:
                pass  # Skip trends with unparseable dates
    
    print(f"\nTrends stuck in pending for >24 hours: {len(stuck_trends)}")
    
    if not stuck_trends:
        print("No trends stuck for >24 hours. No action needed.")
        exit(0)
    
    # Promote stuck trends to 'not_needed'
    print("\nPromoting stuck trends to 'not_needed' status:")
    promoted_count = 0
    
    for trend in stuck_trends:
        tid = trend.get('id')
        title = trend.get('audio_title', 'unknown')
        created_at = trend.get('first_detected_at')
        
        try:
            sb.table("trends").update({
                "llm_classification_status": "not_needed",
                "llm_retry_count": (trend.get('llm_retry_count') or 0) + 1
            }).eq("id", tid).execute()
            
            promoted_count += 1
            print(f"  ✓ Promoted ID {tid}: '{title}' (created: {created_at})")
        except Exception as e:
            print(f"  ✗ Failed to promote ID {tid}: {e}")
    
    print(f"\nSuccessfully promoted {promoted_count}/{len(stuck_trends)} trends")
    print("\nThis ensures trends remain visible in the API even if LLM enrichment fails.")
    
except Exception as e:
    print(f"Error: {e}")
    exit(1)

print("\n" + "=" * 80)