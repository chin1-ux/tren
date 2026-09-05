#!/usr/bin/env python3
"""
Scraper Health Dashboard

This script displays a dashboard of recent scraper runs including:
- Last 10 scraper runs with timestamps
- Trends added per run
- Run duration
- Success/failure status
- Success rate percentage
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

def get_cron_runs(limit=10):
    """Get recent cron runs from database"""
    try:
        result = sb.table('cron_runs').select('*').order('created_at', desc=True).limit(limit).execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"ERROR: Failed to get cron runs: {e}")
        return []

def get_trends_count_before_after(run_id):
    """Get trends count before and after a specific run"""
    try:
        result = sb.table('cron_runs').select('trends_before, trends_after').eq('id', run_id).execute()
        if result.data and len(result.data) > 0:
            return result.data[0].get('trends_before'), result.data[0].get('trends_after')
        return None, None
    except Exception as e:
        # Columns might not exist, return None
        return None, None

def calculate_success_rate(runs):
    """Calculate success rate percentage"""
    if not runs:
        return 0.0
    
    successful = sum(1 for run in runs if run.get('status') in ['completed', 'SUCCESS', 'success'])
    return (successful / len(runs)) * 100

def format_timestamp(timestamp_str):
    """Format timestamp for display"""
    try:
        if timestamp_str:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        return 'N/A'
    except:
        return 'Invalid'

def format_duration(start_str, end_str):
    """Format duration for display"""
    try:
        if start_str and end_str:
            start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
            duration = end - start
            total_seconds = int(duration.total_seconds())
            minutes, seconds = divmod(total_seconds, 60)
            return f"{minutes}m {seconds}s"
        return 'N/A'
    except:
        return 'Invalid'

def display_dashboard():
    """Display the scraper health dashboard"""
    print("="*80)
    print("SCRAPER HEALTH DASHBOARD")
    print("="*80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Get recent runs
    print("\nFetching recent scraper runs...")
    runs = get_cron_runs(limit=10)
    
    if not runs:
        print("\n[INFO] No scraper runs found in database")
        print("This could mean:")
        print("  - Scraper has not run yet")
        print("  - cron_runs table is empty")
        print("  - Database connection issue")
        return
    
    print(f"\n[OK] Found {len(runs)} recent scraper runs")
    
    # Calculate success rate
    success_rate = calculate_success_rate(runs)
    print(f"\nSuccess Rate: {success_rate:.1f}%")
    
    # Display runs table
    print("\n" + "="*80)
    print("RECENT SCRAPER RUNS")
    print("="*80)
    print(f"{'ID':<6} {'Status':<12} {'Started':<20} {'Duration':<12}")
    print("-"*80)
    
    for run in runs:
        run_id = run.get('id', 'N/A')
        status = run.get('status', 'unknown')
        started = format_timestamp(run.get('created_at'))
        ended = format_timestamp(run.get('completed_at'))
        duration = format_duration(run.get('created_at'), run.get('completed_at'))
        
        # Format status
        status_display = status.upper()
        if status in ['completed', 'SUCCESS', 'success']:
            status_display = f"[OK] {status_display}"
        elif status in ['failed', 'FAILURE', 'failure']:
            status_display = f"[FAIL] {status_display}"
        else:
            status_display = f"[?] {status_display}"
        
        print(f"{run_id:<6} {status_display:<12} {started:<20} {duration:<12}")
    
    print("="*80)
    
    # Display summary statistics
    print("\nSUMMARY STATISTICS")
    print("="*80)
    
    total_runs = len(runs)
    successful_runs = sum(1 for run in runs if run.get('status') in ['completed', 'SUCCESS', 'success'])
    failed_runs = sum(1 for run in runs if run.get('status') in ['failed', 'FAILURE', 'failure'])
    
    print(f"Total Runs: {total_runs}")
    print(f"Successful: {successful_runs}")
    print(f"Failed: {failed_runs}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    # Find most recent successful run
    successful_runs_data = [run for run in runs if run.get('status') in ['completed', 'SUCCESS', 'success']]
    if successful_runs_data:
        most_recent = successful_runs_data[0]
        print(f"Most Recent Successful Run: {format_timestamp(most_recent.get('created_at'))}")
    
    # Find most recent failed run
    failed_runs_data = [run for run in runs if run.get('status') in ['failed', 'FAILURE', 'failure']]
    if failed_runs_data:
        most_recent_failed = failed_runs_data[0]
        print(f"Most Recent Failed Run: {format_timestamp(most_recent_failed.get('created_at'))}")
    
    print("="*80)

def main():
    display_dashboard()

if __name__ == '__main__':
    main()