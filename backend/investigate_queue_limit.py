#!/usr/bin/env python3
"""
Investigate the queue limit (30) - is it arbitrary or tied to real constraints?
Model impact of raising it from 30 to 50 on scraper.yml runtime.
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

# Load .env (try backend directory first, then project root)
backend_dir = os.path.dirname(os.path.abspath(__file__))
backend_env = os.path.join(backend_dir, '.env')
project_root = os.path.dirname(backend_dir)
project_env = os.path.join(project_root, '.env')

if os.path.exists(backend_env):
    load_dotenv(backend_env)
elif os.path.exists(project_env):
    load_dotenv(project_env)
else:
    load_dotenv()  # Fallback to current directory

def investigate_queue_limit():
    """Investigate queue limit and model impact of increasing it"""
    
    print("=== Queue Limit Investigation ===\n")
    
    # Initialize Supabase client
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("ERROR: Supabase credentials not set")
        return False
    
    sb = create_client(url, key)
    
    # Current system parameters
    CURRENT_LIMIT = 30
    PROPOSED_LIMITS = [40, 50, 75, 100]
    
    print("=== Current System ===")
    print(f"Queue limit: {CURRENT_LIMIT} audio IDs per run")
    print(f"Activity window: 3 days")
    print(f"Priority: Most active audio (sorted by recent reel frequency)")
    
    # Get current tracked_audio and active audio
    tracked_res = sb.table('tracked_audio').select('audio_id, first_seen_at').execute()
    tracked_count = len(tracked_res.data)
    
    three_days_ago = datetime.now(timezone.utc) - timedelta(days=3)
    
    active_res = sb.table('reels') \
        .select('audio_id') \
        .eq('is_original_audio', False) \
        .not_.is_('audio_id', 'null') \
        .gte('scraped_at', three_days_ago.isoformat()) \
        .execute()
    
    # Count frequency per audio_id
    audio_frequency = {}
    for reel in active_res.data:
        aid = reel.get('audio_id')
        if aid:
            audio_frequency[aid] = audio_frequency.get(aid, 0) + 1
    
    # Filter to tracked audio only
    tracked_ids = {row['audio_id'] for row in tracked_res.data}
    tracked_active = {aid: freq for aid, freq in audio_frequency.items() if aid in tracked_ids}
    
    print(f"\nCurrent State:")
    print(f"  Total tracked_audio: {tracked_count}")
    print(f"  Active tracked audio (last 3 days): {len(tracked_active)}")
    print(f"  Current queue utilization: {min(len(tracked_active), CURRENT_LIMIT)}/{CURRENT_LIMIT} ({min(len(tracked_active), CURRENT_LIMIT)/CURRENT_LIMIT*100:.1f}%)")
    
    # Check for any rate limiting or cost references in the code
    print(f"\n=== Code Investigation ===")
    print("Checking instagram_scraper_browser.py for queue limit rationale...")
    
    import re
    scraper_file = os.path.join(backend_dir, 'instagram_scraper_browser.py')
    
    try:
        with open(scraper_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Search for limit=30 or QUEUE_LIMIT
        limit_matches = re.findall(r'limit\s*=\s*(\d+)', content)
        print(f"Found 'limit = X' patterns: {limit_matches}")
        
        # Search for comments about rate limiting, timeout, or cost
        comments = re.findall(r'#.*(?:rate|limit|timeout|cost|budget|constraint)', content, re.IGNORECASE)
        if comments:
            print(f"Relevant comments found:")
            for comment in comments[:5]:  # Show first 5
                print(f"  {comment}")
        else:
            print("No comments about rate limiting, timeout, or cost found")
        
        # Check the scrape_official_audio_counts function specifically
        if 'scrape_official_audio_counts_async' in content:
            print(f"\nFound scrape_official_audio_counts_async function")
            # Extract the function signature
            func_match = re.search(r'async def scrape_official_audio_counts_async\(self, limit:\s*int\s*=\s*(\d+)\)', content)
            if func_match:
                default_limit = func_match.group(1)
                print(f"  Default limit parameter: {default_limit}")
        
    except Exception as e:
        print(f"Error reading scraper file: {e}")
    
    # Model impact of increasing queue limit
    print(f"\n=== Queue Limit Impact Modeling ===")
    
    print(f"Current active tracked audio: {len(tracked_active)}")
    print(f"Current queue utilization: {min(len(tracked_active), CURRENT_LIMIT)}/{CURRENT_LIMIT}")
    
    for proposed_limit in PROPOSED_LIMITS:
        utilization = min(len(tracked_active), proposed_limit) / proposed_limit * 100
        headroom = proposed_limit - min(len(tracked_active), proposed_limit)
        additional_slots = max(0, proposed_limit - CURRENT_LIMIT)
        
        print(f"\nProposed limit: {proposed_limit}")
        print(f"  Utilization: {utilization:.1f}% ({min(len(tracked_active), proposed_limit)}/{proposed_limit})")
        print(f"  Headroom: {headroom} slots")
        print(f"  Additional slots vs current: +{additional_slots}")
        
        if utilization > 90:
            print(f"  Assessment: Still near capacity")
        elif utilization > 75:
            print(f"  Assessment: Better headroom")
        elif utilization > 50:
            print(f"  Assessment: Good headroom")
        else:
            print(f"  Assessment: Plenty of capacity")
    
    # Runtime impact estimation
    print(f"\n=== Runtime Impact Estimation ===")
    print("Assumptions:")
    print("  - Each audio ID count scrape takes ~30-60 seconds")
    print("  - Current: 30 audio IDs × 45s avg = 22.5 minutes")
    print("  - This runs 'every other run' per earlier audit")
    
    for proposed_limit in [40, 50]:
        current_runtime = CURRENT_LIMIT * 45  # seconds
        proposed_runtime = proposed_limit * 45  # seconds
        increase = proposed_runtime - current_runtime
        increase_pct = (increase / current_runtime) * 100
        
        print(f"\nProposed limit: {proposed_limit}")
        print(f"  Estimated runtime: {proposed_runtime/60:.1f} minutes")
        print(f"  Increase: +{increase/60:.1f} minutes ({increase_pct:+.1f}%)")
        
        if increase_pct < 50:
            print(f"  Assessment: Acceptable runtime increase")
        elif increase_pct < 100:
            print(f"  Assessment: Moderate runtime increase")
        else:
            print(f"  Assessment: Significant runtime increase")
    
    # Check if there are any GitHub Actions timeout settings
    print(f"\n=== GitHub Actions Timeout Check ===")
    workflow_file = os.path.join(project_root, '.github', 'workflows', 'scraper.yml')
    
    print(f"Looking for workflow file: {workflow_file}")
    print(f"File exists: {os.path.exists(workflow_file)}")
    
    if not os.path.exists(workflow_file):
        print("ERROR: scraper.yml not found")
        return True
    
    try:
        with open(workflow_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        timeout_matches = re.findall(r'timeout-minutes:\s*(\d+)', content)
        if timeout_matches:
            print(f"Found timeout settings: {timeout_matches}")
        else:
            print("No explicit timeout settings found in scraper.yml")
        
        # Check for any job-level or step-level timeouts
        job_timeout = re.search(r'jobs:.*?timeout-minutes:\s*(\d+)', content, re.DOTALL)
        if job_timeout:
            print(f"Job-level timeout: {job_timeout.group(1)} minutes")
            
    except Exception as e:
        print(f"Error reading workflow file: {e}")
    
    return True

if __name__ == '__main__':
    investigate_queue_limit()
