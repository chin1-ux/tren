#!/usr/bin/env python3
"""
Check if audio_use_count is populated for all reels or only trend-associated reels
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

def check_audio_use_count_population():
    """Check audio_use_count population patterns"""
    
    # Check all reels for audio_use_count
    print("=== Checking audio_use_count population across all reels ===")
    all_reels = sb.table('reels').select('id, audio_use_count, audio_title, created_at').order('created_at', desc=True).limit(100).execute()
    
    populated_count = 0
    null_count = 0
    zero_count = 0
    
    for reel in all_reels.data:
        audio_use_count = reel.get('audio_use_count')
        if audio_use_count is None:
            null_count += 1
        elif audio_use_count == 0:
            zero_count += 1
        else:
            populated_count += 1
    
    print(f"Total reels checked: {len(all_reels.data)}")
    print(f"audio_use_count IS NULL: {null_count}")
    print(f"audio_use_count = 0: {zero_count}")
    print(f"audio_use_count > 0: {populated_count}")
    
    # Check Beretta reels specifically
    print("\n=== Beretta reels audio_use_count ===")
    beretta_reels = sb.table('reels').select('id, audio_use_count, audio_title').ilike('audio_title', '%beretta%').execute()
    for reel in beretta_reels.data:
        print(f"Reel ID {reel['id']}: audio_use_count = {reel.get('audio_use_count')}")
    
    # Check if audio_use_count correlates with trend association
    print("\n=== Checking correlation with trend association ===")
    
    # Get reels that ARE associated with trends
    trending_audio_titles = sb.table('trends').select('audio_title, audio_artist').execute()
    trending_pairs = {(t.get('audio_title'), t.get('audio_artist')) for t in trending_audio_titles.data if t.get('audio_title')}
    
    # Check recent reels against trending pairs
    trend_associated_populated = 0
    trend_associated_zero = 0
    trend_associated_null = 0
    non_trend_associated_populated = 0
    non_trend_associated_zero = 0
    non_trend_associated_null = 0
    
    for reel in all_reels.data:
        title = reel.get('audio_title')
        artist = reel.get('audio_artist')
        is_trend_associated = (title, artist) in trending_pairs
        
        audio_use_count = reel.get('audio_use_count')
        if audio_use_count is None:
            if is_trend_associated:
                trend_associated_null += 1
            else:
                non_trend_associated_null += 1
        elif audio_use_count == 0:
            if is_trend_associated:
                trend_associated_zero += 1
            else:
                non_trend_associated_zero += 1
        else:
            if is_trend_associated:
                trend_associated_populated += 1
            else:
                non_trend_associated_populated += 1
    
    print(f"Trend-associated reels:")
    print(f"  Populated (>0): {trend_associated_populated}")
    print(f"  Zero: {trend_associated_zero}")
    print(f"  NULL: {trend_associated_null}")
    
    print(f"\nNon-trend-associated reels:")
    print(f"  Populated (>0): {non_trend_associated_populated}")
    print(f"  Zero: {non_trend_associated_zero}")
    print(f"  NULL: {non_trend_associated_null}")
    
    # Check audio_official_counts table
    print("\n=== Checking audio_official_counts table ===")
    try:
        official_counts = sb.table('audio_official_counts').select('*').order('checked_at', desc=True).limit(10).execute()
        print(f"Recent official count entries: {len(official_counts.data)}")
        for entry in official_counts.data:
            print(f"  audio_id: {entry.get('audio_id')}, official_count: {entry.get('official_count')}, official_count_velocity: {entry.get('official_count_velocity')}")
    except Exception as e:
        print(f"audio_official_counts table check failed: {e}")

if __name__ == '__main__':
    check_audio_use_count_population()
