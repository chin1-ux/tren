#!/usr/bin/env python3
"""
Check attribution details for Beretta reels
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

def check_beretta_attribution():
    """Check attribution details for Beretta reels"""
    
    # Get the specific Beretta reels
    print("Fetching Beretta reels...")
    beretta_reels = sb.table('reels').select('*').ilike('audio_title', '%beretta%').execute()
    
    print(f"Found {len(beretta_reels.data)} Beretta reels")
    
    for reel in beretta_reels.data:
        print(f"\n=== Reel ID: {reel['id']} ===")
        print(f"audio_title: {reel.get('audio_title')}")
        print(f"audio_artist: {reel.get('audio_artist')}")
        print(f"hashtags: {reel.get('hashtags')}")
        print(f"caption: {reel.get('caption', '')[:100]}...")
        print(f"posted_at: {reel.get('posted_at')}")
        print(f"created_at: {reel.get('created_at')}")
        print(f"view_count: {reel.get('view_count')}")
        print(f"like_count: {reel.get('like_count')}")
        print(f"velocity_score: {reel.get('velocity_score')}")
        print(f"source_hashtag_pool: {reel.get('source_hashtag_pool')}")
        print(f"language: {reel.get('language')}")
        
        # Check if audio_id field exists
        if 'audio_id' in reel:
            print(f"audio_id: {reel.get('audio_id')}")
        else:
            print("audio_id: FIELD NOT PRESENT IN SCHEMA")
    
    # Check if Beretta exists in trends table
    print("\n=== Checking trends table for Beretta ===")
    beretta_trends = sb.table('trends').select('*').ilike('audio_title', '%beretta%').execute()
    print(f"Found {len(beretta_trends.data)} trends with 'Beretta' in audio_title")
    
    if beretta_trends.data:
        for trend in beretta_trends.data:
            print(f"\n=== Trend ID: {trend['id']} ===")
            print(f"audio_title: {trend.get('audio_title')}")
            print(f"audio_artist: {trend.get('audio_artist')}")
            print(f"status: {trend.get('status')}")
            print(f"reel_count: {trend.get('reel_count')}")
            print(f"first_detected_at: {trend.get('first_detected_at')}")
            print(f"confidence: {trend.get('confidence')}")
    else:
        print("No trends found for Beretta - THIS IS THE PROBLEM")
    
    # Check current tracked hashtags
    print("\n=== Checking tracked hashtags ===")
    hashtag_pools = sb.table('hashtag_performance').select('*').execute()
    print(f"Total tracked hashtags: {len(hashtag_pools.data)}")
    
    # Check if the hashtags used by Beretta reels are in our tracked pools
    beretta_hashtags = set()
    for reel in beretta_reels.data:
        if reel.get('hashtags'):
            beretta_hashtags.update(reel.get('hashtags'))
    
    print(f"\nHashtags used by Beretta reels: {beretta_hashtags}")
    
    print("\nChecking which of these hashtags are in our tracked pools...")
    for hashtag in beretta_hashtags:
        result = sb.table('hashtag_performance').select('*').eq('hashtag', hashtag.lstrip('#')).execute()
        if result.data:
            print(f"  ✓ {hashtag} - TRACKED (pool: {result.data[0].get('pool_name')})")
        else:
            print(f"  ✗ {hashtag} - NOT TRACKED")
    
    # Check reels table structure for audio_id
    print("\n=== Checking reels table structure ===")
    # Try to get column info by examining a sample reel
    sample_reel = sb.table('reels').select('*').limit(1).execute()
    if sample_reel.data:
        print("Available columns in reels table:")
        for column in sample_reel.data[0].keys():
            print(f"  - {column}")

if __name__ == '__main__':
    check_beretta_attribution()
