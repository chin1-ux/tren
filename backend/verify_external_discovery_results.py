#!/usr/bin/env python3
"""
Verify external trend discovery results after pipeline execution
"""

import os
import sys
import io
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

load_dotenv()

def verify_external_discovery_results():
    """Verify the results of the external trend discovery pipeline"""
    
    print("=== External Trend Discovery Results Verification ===\n")
    
    # Initialize Supabase client
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("ERROR: Supabase credentials not set")
        return False
    
    sb = create_client(url, key)
    
    # Check for recent external discovery trends
    print("1. Checking for recent external discovery trends...")
    time_threshold = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    
    external_trends = sb.table('trends').select('*').eq('discovery_source', 'GLOBAL_TO_INDIA_CROSSOVER').gte('first_detected_at', time_threshold).execute()
    
    if external_trends.data:
        print(f"✓ Found {len(external_trends.data)} external discovery trends in last 24h")
        for trend in external_trends.data:
            print(f"  - {trend.get('audio_title')} by {trend.get('audio_artist')} ({trend.get('status')})")
    else:
        print("✓ No external discovery trends in last 24h (expected if no global songs showed Indian signals)")
    
    # Check pipeline job logs
    print("\n2. Checking pipeline job logs...")
    time_threshold_jobs = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    
    recent_jobs = sb.table('jobs').select('*').eq('job_type', 'external_trend_discovery').gte('created_at', time_threshold_jobs).order('created_at', desc=True).limit(5).execute()
    
    if recent_jobs.data:
        print(f"✓ Found {len(recent_jobs.data)} recent pipeline jobs")
        for job in recent_jobs.data:
            print(f"  - {job.get('created_at')}: {job.get('status')}")
            print(f"    Input: {job.get('input_data', 'N/A')}")
            print(f"    Output: {job.get('output_url', 'N/A')}")
            if job.get('error_message'):
                print(f"    Error: {job.get('error_message')}")
    else:
        print("✗ No recent pipeline jobs found - pipeline may not have run")
    
    # Check for total external discovery trends
    print("\n3. Checking total external discovery trends...")
    all_external_trends = sb.table('trends').select('*', count='exact').eq('discovery_source', 'GLOBAL_TO_INDIA_CROSSOVER').execute()
    
    total_count = all_external_trends.count if hasattr(all_external_trends, 'count') else len(all_external_trends.data)
    print(f"✓ Total external discovery trends: {total_count}")
    
    # Check trends with discovery_source field
    print("\n4. Checking trends with discovery_source tracking...")
    trends_with_source = sb.table('trends').select('*', count='exact').not_('discovery_source', 'is', None).execute()
    
    tracked_count = trends_with_source.count if hasattr(trends_with_source, 'count') else len(trends_with_source.data)
    print(f"✓ Trends with discovery_source tracking: {tracked_count}")
    
    # Summary
    print("\n=== VERIFICATION SUMMARY ===")
    print(f"External discovery trends (24h): {len(external_trends.data) if external_trends.data else 0}")
    print(f"Recent pipeline jobs: {len(recent_jobs.data) if recent_jobs.data else 0}")
    print(f"Total external discovery trends: {total_count}")
    print(f"Trends with discovery_source tracking: {tracked_count}")
    
    # Health check
    if recent_jobs.data:
        latest_job = recent_jobs.data[0]
        if latest_job.get('status') == 'completed':
            print("\n✓ Pipeline health: HEALTHY (latest job completed successfully)")
        elif latest_job.get('status') == 'no_candidates':
            print("\n✓ Pipeline health: HEALTHY (latest job ran but found no candidates)")
        else:
            print(f"\n⚠ Pipeline health: CHECK NEEDED (latest job status: {latest_job.get('status')})")
    else:
        print("\n⚠ Pipeline health: UNKNOWN (no recent jobs found)")
    
    return True

if __name__ == '__main__':
    success = verify_external_discovery_results()
    sys.exit(0 if success else 1)
