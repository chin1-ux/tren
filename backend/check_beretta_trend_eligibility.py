#!/usr/bin/env python3
"""
Check why Beretta reels didn't become trends
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

# Load environment variables
load_dotenv()

# Initialize Supabase client
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
if not url or not key:
    raise RuntimeError('Supabase credentials not set in environment')
sb = create_client(url, key)

def check_beretta_trend_eligibility():
    """Check why Beretta reels didn't become trends"""
    
    # Get Beretta reels
    print("Fetching Beretta reels...")
    beretta_reels = sb.table('reels').select('*').ilike('audio_title', '%beretta%').execute()
    
    print(f"Found {len(beretta_reels.data)} Beretta reels")
    
    # Group by audio title + artist (matching trend_engine logic)
    audio_groups = {}
    for reel in beretta_reels.data:
        title = (reel.get("audio_title") or "").strip()
        artist = (reel.get("audio_artist") or "").strip()
        if not title:
            continue
        if not artist:
            artist = "Unknown Artist"
        group_key = (title, artist)
        if group_key not in audio_groups:
            audio_groups[group_key] = []
        audio_groups[group_key].append(reel)
    
    print(f"\n=== Audio Groups ===")
    print(f"Grouped into {len(audio_groups)} unique audio combinations")
    
    # Check each group against trend detection criteria
    EMERGING_USE_THRESHOLD = 150000
    RISING_USE_THRESHOLD = 800000
    
    for (title, artist), group_reels in audio_groups.items():
        print(f"\n=== Group: {title} by {artist} ===")
        print(f"Number of reels: {len(group_reels)}")
        
        # Get unique creators
        usernames = {r.get("owner_username") for r in group_reels if r.get("owner_username")}
        creator_count = len(usernames)
        print(f"Unique creators: {creator_count}")
        
        # Get max audio_use_count
        max_use_count = max((r.get("audio_use_count") or 0 for r in group_reels), default=0)
        print(f"Max audio_use_count: {max_use_count}")
        
        # Check velocity scores
        velocities = [r.get("velocity_score", 0.0) for r in group_reels]
        avg_velocity = sum(velocities) / len(velocities) if velocities else 0.0
        max_velocity = max(velocities) if velocities else 0.0
        print(f"Avg velocity: {avg_velocity:.2f}")
        print(f"Max velocity: {max_velocity:.2f}")
        
        # Check engagement quality gate
        has_valid_engagement = any((r.get("like_count") or 0) >= 10 for r in group_reels)
        print(f"Has valid engagement (like_count >= 10): {has_valid_engagement}")
        
        # Check time window
        posted_times = []
        for r in group_reels:
            posted_str = r.get("posted_at")
            if posted_str:
                if posted_str.endswith("Z"):
                    posted_str = posted_str[:-1] + "+00:00"
                try:
                    posted_times.append(datetime.fromisoformat(posted_str))
                except Exception as e:
                    print(f"Error parsing posted_at: {e}")
        
        time_window_valid = True
        if posted_times:
            time_span = (max(posted_times) - min(posted_times))
            print(f"Time span: {time_span}")
            if time_span > timedelta(hours=72):
                time_window_valid = False
                print(f"Time window INVALID: exceeds 72h")
        
        # Check creator velocity
        now_utc = datetime.now(timezone.utc)
        creators_0 = set()
        creators_1 = set()
        for r in group_reels:
            posted_str = r.get("posted_at")
            if not posted_str:
                continue
            try:
                if posted_str.endswith("Z"):
                    posted_str = posted_str[:-1] + "+00:00"
                posted_dt = datetime.fromisoformat(posted_str)
                if posted_dt.tzinfo is None:
                    posted_dt = posted_dt.replace(tzinfo=timezone.utc)
                diff_seconds = (now_utc - posted_dt).total_seconds()
                if diff_seconds < 0:
                    diff_seconds = 0
                username = r.get("owner_username")
                if username:
                    if diff_seconds <= 3.0 * 3600.0:
                        creators_0.add(username)
                    elif diff_seconds <= 6.0 * 3600.0:
                        creators_1.add(username)
            except Exception as e:
                print(f"Error calculating creator velocity: {e}")
        
        creator_velocity = (len(creators_0) - len(creators_1)) / 3.0
        print(f"Creator velocity: {creator_velocity:.2f}")
        
        # Determine eligibility
        print(f"\n=== Trend Eligibility Check ===")
        print(f"Thresholds: EMERGING_USE_THRESHOLD={EMERGING_USE_THRESHOLD}, RISING_USE_THRESHOLD={RISING_USE_THRESHOLD}")
        
        initial_status = None
        promotion_trigger = None
        
        if max_use_count >= RISING_USE_THRESHOLD:
            initial_status = "rising"
            promotion_trigger = "audio_use_count_rising"
        elif creator_count >= 3 and creator_velocity > 0:
            initial_status = "rising"
            promotion_trigger = "creator_count_rising"
        elif max_use_count >= EMERGING_USE_THRESHOLD:
            initial_status = "emerging"
            promotion_trigger = "audio_use_count_emerging"
        elif creator_count >= 2 and len(group_reels) >= 2:
            initial_status = "emerging"
            promotion_trigger = "creator_count_emerging"
        
        print(f"Eligible for status: {initial_status}")
        print(f"Trigger: {promotion_trigger}")
        
        if not initial_status:
            print("NOT ELIGIBLE - fails all trend detection criteria")
            print("Reasons:")
            if max_use_count < EMERGING_USE_THRESHOLD:
                print(f"  - audio_use_count ({max_use_count}) below EMERGING threshold ({EMERGING_USE_THRESHOLD})")
            if not (creator_count >= 2 and len(group_reels) >= 2):
                print(f"  - Insufficient creators/reels (need >=2 creators and >=2 reels, have {creator_count} creators and {len(group_reels)} reels)")
            if not (creator_count >= 3 and creator_velocity > 0):
                print(f"  - Creator velocity condition not met (need >=3 creators and positive velocity, have {creator_count} creators and {creator_velocity:.2f} velocity)")
            if not has_valid_engagement:
                print(f"  - Engagement quality gate failed (no reel with like_count >= 10)")
            if not time_window_valid:
                print(f"  - Time window invalid (reels span > 72h)")
        
        # Check if already exists as active trend
        print(f"\n=== Check if already exists as active trend ===")
        existing_trend = sb.table('trends').select('*').eq('audio_title', title).eq('audio_artist', artist).in_('status', ['emerging', 'rising']).execute()
        if existing_trend.data:
            print(f"ALREADY EXISTS as active trend: {existing_trend.data[0]['status']}")
        else:
            print("Does not exist as active trend")
        
        # Check if exists as expired/peaked trend
        existing_expired = sb.table('trends').select('*').eq('audio_title', title).eq('audio_artist', artist).in_('status', ['expired', 'peaked']).execute()
        if existing_expired.data:
            print(f"Exists as {existing_expired.data[0]['status']} trend - could be re-detected if it surges again")

if __name__ == '__main__':
    check_beretta_trend_eligibility()
