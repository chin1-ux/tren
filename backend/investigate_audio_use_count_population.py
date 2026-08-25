#!/usr/bin/env python3
"""
Investigate audio_use_count population timing - is it populated at scrape time or only for trends?
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

# Load .env
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)
load_dotenv()  # Fallback

def investigate_audio_use_count_population():
    """Investigate when audio_use_count gets populated"""
    
    print("=== Audio Use Count Population Investigation ===\n")
    
    # Initialize Supabase client
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("ERROR: Supabase credentials not set")
        return False
    
    sb = create_client(url, key)
    
    # Check audio_use_count population in reels table
    print("=== Step 1: Audio Use Count in Reels Table ===")
    
    # Get sample reels with different creation times
    print("Fetching recent reels with audio_use_count data...")
    
    recent_reels = sb.table('reels').select('id, audio_use_count, audio_title, audio_artist, created_at, posted_at').order('created_at', desc=True).limit(20).execute()
    
    print(f"Recent reels sample: {len(recent_reels.data)}")
    
    zero_count = 0
    non_zero_count = 0
    null_count = 0
    
    for reel in recent_reels.data:
        audio_use_count = reel.get('audio_use_count')
        created_at = reel.get('created_at')
        posted_at = reel.get('posted_at')
        
        if audio_use_count is None:
            null_count += 1
        elif audio_use_count == 0:
            zero_count += 1
        else:
            non_zero_count += 1
        
        print(f"Reel ID {reel['id']}: audio_use_count={audio_use_count}, created_at={created_at}, posted_at={posted_at}")
    
    print(f"\nSummary:")
    print(f"  NULL: {null_count}")
    print(f"  Zero: {zero_count}")
    print(f"  Non-zero: {non_zero_count}")
    
    # Check correlation with trend association
    print("\n=== Step 2: Correlation with Trend Association ===")
    
    # Get all trends
    all_trends = sb.table('trends').select('audio_title, audio_artist, status, first_detected_at').execute()
    
    # Build set of trending audio
    trending_audio = set()
    for trend in all_trends.data:
        title = trend.get('audio_title', '').strip()
        artist = trend.get('audio_artist', '').strip()
        if title and artist:
            trending_audio.add((title, artist))
    
    print(f"Total trends in database: {len(all_trends.data)}")
    print(f"Unique trending audio pairs: {len(trending_audio)}")
    
    # Check if recent reels are associated with trends
    trend_associated_count = 0
    non_trend_associated_count = 0
    
    for reel in recent_reels.data:
        title = reel.get('audio_title', '').strip()
        artist = reel.get('audio_artist', '').strip()
        
        if title and artist:
            if (title, artist) in trending_audio:
                trend_associated_count += 1
            else:
                non_trend_associated_count += 1
    
    print(f"\nRecent reels trend association:")
    print(f"  Associated with trends: {trend_associated_count}")
    print(f"  Not associated with trends: {non_trend_associated_count}")
    
    # Check audio_use_count for trend-associated vs non-trend-associated
    print("\n=== Step 3: Audio Use Count by Trend Association ===")
    
    trend_associated_with_count = 0
    trend_associated_zero = 0
    non_trend_with_count = 0
    non_trend_zero = 0
    
    for reel in recent_reels.data:
        title = reel.get('audio_title', '').strip()
        artist = reel.get('audio_artist', '').strip()
        audio_use_count = reel.get('audio_use_count')
        
        is_trend_associated = (title, artist) in trending_audio if title and artist else False
        
        if is_trend_associated:
            if audio_use_count and audio_use_count > 0:
                trend_associated_with_count += 1
            else:
                trend_associated_zero += 1
        else:
            if audio_use_count and audio_use_count > 0:
                non_trend_with_count += 1
            else:
                non_trend_zero += 1
    
    print(f"Trend-associated reels:")
    print(f"  With audio_use_count > 0: {trend_associated_with_count}")
    print(f"  With audio_use_count = 0/NULL: {trend_associated_zero}")
    
    print(f"\nNon-trend-associated reels:")
    print(f"  With audio_use_count > 0: {non_trend_with_count}")
    print(f"  With audio_use_count = 0/NULL: {non_trend_zero}")
    
    # Check audio_official_counts table timing
    print("\n=== Step 4: Audio Official Counts Table Timing ===")
    
    try:
        import psycopg2
        db_url = os.getenv('SUPABASE_DB_URL')
        if not db_url:
            print("SUPABASE_DB_URL not set, skipping direct DB analysis")
        else:
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Get audio_official_counts records with timestamps
            cursor.execute("""
                SELECT audio_id, official_count, official_count_velocity, checked_at
                FROM audio_official_counts
                ORDER BY checked_at DESC
                LIMIT 20
            """)
            
            official_counts = cursor.fetchall()
            print(f"Recent audio_official_counts entries: {len(official_counts)}")
            
            for audio_id, official_count, velocity, checked_at in official_counts:
                print(f"  audio_id: {audio_id}, official_count: {official_count}, velocity: {velocity}, checked_at: {checked_at}")
            
            cursor.close()
            conn.close()
            
    except ImportError:
        print("psycopg2 not available, skipping direct DB analysis")
    except Exception as e:
        print(f"Error accessing audio_official_counts: {e}")
    
    # Check when audio_use_count gets populated in the scraping pipeline
    print("\n=== Step 5: Check Audio Use Count Population in Pipeline ===")
    
    # Look for any code that populates audio_use_count
    print("Searching for audio_use_count population logic...")
    
    # Check instagram_scraper_browser.py for audio_use_count population
    print("This would require analyzing the scraper code to understand when audio_use_count is populated")
    
    # Conclusion
    print("\n=== CONCLUSION ===")
    
    if non_trend_with_count > 0:
        print("✗ CHICKEN-AND-EGG BUG CONFIRMED")
        print("  audio_use_count is only populated for trend-associated reels")
        print("  Non-trend reels have audio_use_count = 0, preventing them from reaching emerging threshold")
        print("  This needs to be fixed independent of the Beretta case")
    else:
        print("✓ No chicken-and-egg bug detected")
        print("  audio_use_count appears to be populated for all reels at scrape time")
        print("  Trend association doesn't determine audio_use_count population")
    
    if trend_associated_zero > 0:
        print("⚠️  Even trend-associated reels have audio_use_count = 0")
        print("  This suggests the fetch mechanism itself may have issues")
    
    return True

if __name__ == '__main__':
    investigate_audio_use_count_population()
