#!/usr/bin/env python3
"""
Monitoring for pending trends growth
Alerts if pending trends are growing without corresponding drops
indicating the nightly LLM batch isn't processing them
"""

import os, sys
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
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
print("PENDING TRENDS MONITORING")
print("=" * 80)

try:
    # Get current pending trends count
    pending_res = sb.table("trends").select("id", count="exact").eq("is_seed_data", False).eq("llm_classification_status", "pending").execute()
    current_pending_count = pending_res.count or 0
    
    # Get pending trends by status (Emerging specifically for monitoring)
    emerging_pending_res = sb.table("trends").select("id", count="exact").eq("is_seed_data", False).eq("llm_classification_status", "pending").eq("status", "emerging").execute()
    emerging_pending_count = emerging_pending_res.count or 0
    
    # Get completed trends count in last 24 hours
    twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    completed_res = sb.table("trends").select("id", count="exact").eq("is_seed_data", False).eq("llm_classification_status", "completed").gte("llm_classified_at", twenty_four_hours_ago.isoformat()).execute()
    completed_last_24h = completed_res.count or 0
    
    # Get not_needed trends count
    not_needed_res = sb.table("trends").select("id", count="exact").eq("is_seed_data", False).eq("llm_classification_status", "not_needed").execute()
    not_needed_count = not_needed_res.count or 0
    
    print(f"\nCurrent pending trends: {current_pending_count}")
    print(f"Emerging pending trends: {emerging_pending_count}")
    print(f"Completed in last 24h: {completed_last_24h}")
    print(f"Total not_needed trends: {not_needed_count}")
    
    # Alert thresholds (lowered for proactive detection)
    HIGH_PENDING_THRESHOLD = 25  # Alert if >25 pending trends (lowered from 50)
    NO_PROCESSING_THRESHOLD = 10  # Alert if 0 completed in 24h but >10 pending
    EMERGING_PENDING_THRESHOLD = 3  # Alert if >3 emerging pending (lowered from 5)
    
    alert_reasons = []
    
    if current_pending_count > HIGH_PENDING_THRESHOLD:
        alert_reasons.append(f"High pending count: {current_pending_count} > {HIGH_PENDING_THRESHOLD}")
        alert_reasons.append("Note: Pending trends are NOT visible in API (24h fallback will convert to not_needed)")
    
    if current_pending_count > NO_PROCESSING_THRESHOLD and completed_last_24h == 0:
        alert_reasons.append(f"No processing in 24h: {current_pending_count} pending but 0 completed")
        alert_reasons.append("Note: 24h fallback will convert pending trends to not_needed for API visibility")
    
    if emerging_pending_count > EMERGING_PENDING_THRESHOLD:
        alert_reasons.append(f"Emerging pending buildup: {emerging_pending_count} > {EMERGING_PENDING_THRESHOLD} (processing cadence may be insufficient)")
    
    if alert_reasons:
        print("\nALERT TRIGGERED:")
        for reason in alert_reasons:
            print(f"  - {reason}")
        print("\nRecommended actions:")
        print("  1. Check if llm-classification workflow is running")
        print("  2. Verify GROQ_API_KEY secrets are set correctly")
        print("  3. Check GitHub Actions logs for classification failures")
        print("  4. Consider running nightly_llm_batch.py manually to clear backlog")
        print("  5. 24h fallback will convert pending trends to not_needed for API visibility")
        if emerging_pending_count > EMERGING_PENDING_THRESHOLD:
            print("  6. Consider increasing LLM classification frequency (currently 4x daily)")
            print("     Emerging pending buildup suggests processing cadence is insufficient")
        print("  7. Emergency workflow will auto-trigger if pending exceeds 20")
        exit(1)  # Exit with error code to trigger CI/CD alerting
    else:
        print("\nOK: Pending trends within normal limits")
        print("   - Classification pipeline appears healthy")
        exit(0)

except Exception as e:
    print(f"\nERROR: Error during monitoring: {e}")
    exit(1)

print("\n" + "=" * 80)