#!/usr/bin/env python3
"""
Check hashtag coverage and configuration
"""

import os
import sys
import io
from dotenv import load_dotenv
from supabase import create_client

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Load environment variables
load_dotenv()

# Initialize Supabase client
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
if not url or not key:
    raise RuntimeError('Supabase credentials not set in environment')
sb = create_client(url, key)

def check_hashtag_coverage():
    """Check hashtag coverage and configuration"""
    
    # Get all tracked hashtags
    print("=== Tracked Hashtags ===")
    hashtag_pools = sb.table('hashtag_performance').select('*').execute()
    print(f"Total tracked hashtags: {len(hashtag_pools.data)}")
    
    # Group by pool
    pools = {}
    for hashtag in hashtag_pools.data:
        pool_name = hashtag.get('pool_name', 'unknown')
        if pool_name not in pools:
            pools[pool_name] = []
        pools[pool_name].append(hashtag.get('hashtag'))
    
    print("\nHashtag pools:")
    for pool_name, hashtags in pools.items():
        print(f"\n{pool_name}:")
        for hashtag in hashtags:
            print(f"  - #{hashtag}")
    
    # Check which hashtags are most commonly used
    print("\n=== Most Common Hashtags in Reels ===")
    # Sample recent reels to see hashtag usage
    recent_reels = sb.table('reels').select('hashtags').order('created_at', desc=True).limit(100).execute()
    
    hashtag_counts = {}
    for reel in recent_reels.data:
        hashtags = reel.get('hashtags', [])
        for hashtag in hashtags:
            hashtag_counts[hashtag] = hashtag_counts.get(hashtag, 0) + 1
    
    # Sort by count
    sorted_hashtags = sorted(hashtag_counts.items(), key=lambda x: -x[1])
    print(f"Top 20 most common hashtags in recent reels:")
    for hashtag, count in sorted_hashtags[:20]:
        tracked = "TRACKED" if any(h.get('hashtag') == hashtag.lstrip('#') for h in hashtag_pools.data) else "NOT TRACKED"
        print(f"  #{hashtag}: {count} uses [{tracked}]")
    
    # Check GLOBAL_DISCOVERY pool specifically
    print("\n=== GLOBAL_DISCOVERY Pool Details ===")
    global_discovery = [h for h in hashtag_pools.data if h.get('pool_name') == 'GLOBAL_DISCOVERY']
    print(f"Hashtags in GLOBAL_DISCOVERY pool: {len(global_discovery)}")
    for hashtag in global_discovery:
        print(f"  - #{hashtag.get('hashtag')} (performance_score: {hashtag.get('performance_score')})")

if __name__ == '__main__':
    check_hashtag_coverage()
