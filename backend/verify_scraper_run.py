#!/usr/bin/env python3
"""
Scraper Run Verification Script

This script verifies that the scraper run was successful by:
1. Checking if new trends were added to the database
2. Verifying the most recent trends have recent timestamps
3. Ensuring trends have created_at field
4. Outputting detailed verification results
5. Logging results to file for historical tracking
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Initialize Supabase client
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
if not url or not key:
    print("ERROR: Supabase credentials not set in environment")
    sys.exit(1)

sb = create_client(url, key)

def get_trend_count():
    """Get total count of trends in database"""
    try:
        result = sb.table('trends').select('id', count='exact').execute()
        return result.count if hasattr(result, 'count') else len(result.data)
    except Exception as e:
        print(f"ERROR: Failed to get trend count: {e}")
        return None

def get_recent_trends(limit=10):
    """Get the most recent trends from database"""
    try:
        result = sb.table('trends').select('*').order('created_at', desc=True).limit(limit).execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"ERROR: Failed to get recent trends: {e}")
        return []

def verify_timestamps(trends, max_age_hours=30):
    """Verify that trends have recent timestamps.

    Window must match scrape cadence (every 2 days at 02:00 UTC) plus margin
    for GitHub cron jitter and LLM classification lag. A 9h window can never
    pass on a 48h cadence; 30h covers a run landing mid-cycle on fresh data.
    Note: revisit if cadence changes (P-WORK-5 revert decision pending).
    """
    if not trends:
        return True, "No trends to verify"
    
    now = datetime.now()
    max_age = timedelta(hours=max_age_hours)
    
    for trend in trends:
        if not trend.get('created_at'):
            return False, f"Trend {trend.get('id')} missing created_at field"
        
        try:
            created_at_str = trend['created_at']
            # Handle both naive and aware datetimes
            if 'Z' in created_at_str or '+' in created_at_str:
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                # Make now timezone-aware if created_at is aware
                if created_at.tzinfo is not None:
                    now = datetime.now(created_at.tzinfo)
            else:
                created_at = datetime.fromisoformat(created_at_str)
                now = datetime.now()
            
            age = now - created_at
            
            if age > max_age:
                return False, f"Trend {trend.get('id')} is too old: {age.total_seconds() / 3600:.1f} hours"
        except Exception as e:
            return False, f"Trend {trend.get('id')} has invalid timestamp: {e}"
    
    return True, f"All {len(trends)} trends have recent timestamps"

def verify_created_at_field(trends):
    """Verify that trends have created_at field"""
    if not trends:
        return True, "No trends to verify"
    
    missing_count = sum(1 for trend in trends if not trend.get('created_at'))
    
    if missing_count > 0:
        return False, f"{missing_count} trends missing created_at field"
    
    return True, f"All {len(trends)} trends have created_at field"

def log_verification_result(result, log_file='backend/scraper_verification.log'):
    """Log verification result to file"""
    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        with open(log_file, 'a') as f:
            timestamp = datetime.now().isoformat()
            f.write(f"\n{'='*60}\n")
            f.write(f"Verification Run: {timestamp}\n")
            f.write(f"{'='*60}\n")
            f.write(f"Status: {result['status']}\n")
            f.write(f"Total Trends: {result['total_trends']}\n")
            f.write(f"Timestamp Check: {result['timestamp_check']['status']} - {result['timestamp_check']['message']}\n")
            f.write(f"Created_at Check: {result['created_at_check']['status']} - {result['created_at_check']['message']}\n")
            f.write(f"Recent Trends Count: {result['recent_trends_count']}\n")
            f.write(f"\n")
    except Exception as e:
        print(f"WARNING: Failed to log verification result: {e}")

def main():
    print("="*60)
    print("SCRAPER RUN VERIFICATION")
    print("="*60)
    
    result = {
        'status': 'UNKNOWN',
        'total_trends': 0,
        'timestamp_check': {'status': 'UNKNOWN', 'message': ''},
        'created_at_check': {'status': 'UNKNOWN', 'message': ''},
        'recent_trends_count': 0,
    }
    
    # Get total trend count
    print("\n1. Checking total trend count...")
    total_trends = get_trend_count()
    if total_trends is None:
        print("   [ERROR] Failed to get trend count")
        result['status'] = 'ERROR'
        log_verification_result(result)
        sys.exit(1)
    
    print(f"   [OK] Total trends: {total_trends}")
    result['total_trends'] = total_trends
    
    # Get recent trends
    print("\n2. Getting recent trends...")
    recent_trends = get_recent_trends(limit=10)
    print(f"   [OK] Found {len(recent_trends)} recent trends")
    result['recent_trends_count'] = len(recent_trends)
    
    # Verify timestamps
    print("\n3. Verifying trend timestamps...")
    timestamp_ok, timestamp_msg = verify_timestamps(recent_trends, max_age_hours=9)
    if timestamp_ok:
        print(f"   [OK] {timestamp_msg}")
        result['timestamp_check'] = {'status': 'PASS', 'message': timestamp_msg}
    else:
        print(f"   [FAIL] {timestamp_msg}")
        result['timestamp_check'] = {'status': 'FAIL', 'message': timestamp_msg}
    
    # Verify created_at field
    print("\n4. Verifying created_at field...")
    created_at_ok, created_at_msg = verify_created_at_field(recent_trends)
    if created_at_ok:
        print(f"   [OK] {created_at_msg}")
        result['created_at_check'] = {'status': 'PASS', 'message': created_at_msg}
    else:
        print(f"   [FAIL] {created_at_msg}")
        result['created_at_check'] = {'status': 'FAIL', 'message': created_at_msg}
    
    # Determine overall status
    if timestamp_ok and created_at_ok:
        result['status'] = 'PASS'
        print("\n" + "="*60)
        print("VERIFICATION: PASS")
        print("="*60)
    else:
        result['status'] = 'FAIL'
        print("\n" + "="*60)
        print("VERIFICATION: FAIL")
        print("="*60)
    
    # Log result
    log_verification_result(result)
    
    # Exit with appropriate code
    sys.exit(0 if result['status'] == 'PASS' else 1)

if __name__ == '__main__':
    main()