#!/usr/bin/env python3
"""
Check queue capacity headroom for official-count refresh.
Current system: limit=30 audio IDs per run, prioritized by recent activity.
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

def check_queue_capacity():
    """Check if expanding enrollment risks crowding out refresh slots"""
    
    print("=== Official Count Refresh Queue Capacity Analysis ===\n")
    
    # Initialize Supabase client
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("ERROR: Supabase credentials not set")
        return False
    
    sb = create_client(url, key)
    
    # Current system parameters
    QUEUE_LIMIT = 30  # From scrape_official_audio_counts(limit=30)
    ACTIVITY_WINDOW_DAYS = 3  # From three_days_ago calculation
    
    print(f"Current System Parameters:")
    print(f"  Queue limit per run: {QUEUE_LIMIT} audio IDs")
    print(f"  Activity window: {ACTIVITY_WINDOW_DAYS} days")
    print(f"  Priority: Most active audio (sorted by recent reel frequency)\n")
    
    # Get current tracked_audio count
    tracked_res = sb.table('tracked_audio').select('audio_id, first_seen_at').execute()
    tracked_count = len(tracked_res.data)
    
    print(f"Current tracked_audio count: {tracked_count}")
    
    # Get active tracked audio (with recent reels)
    three_days_ago = datetime.now(timezone.utc) - timedelta(days=ACTIVITY_WINDOW_DAYS)
    
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
    tracked_active = {aid: freq for aid, freq in audio_frequency.items() if aid in {row['audio_id'] for row in tracked_res.data}}
    
    print(f"Active tracked audio (last {ACTIVITY_WINDOW_DAYS} days): {len(tracked_active)}")
    
    # Calculate queue utilization
    if len(tracked_active) > 0:
        queue_utilization = min(len(tracked_active), QUEUE_LIMIT) / QUEUE_LIMIT * 100
        print(f"Queue utilization: {queue_utilization:.1f}% ({min(len(tracked_active), QUEUE_LIMIT)}/{QUEUE_LIMIT} slots)")
    else:
        queue_utilization = 0
        print(f"Queue utilization: 0% (0/{QUEUE_LIMIT} slots)")
    
    # Calculate headroom
    headroom = QUEUE_LIMIT - min(len(tracked_active), QUEUE_LIMIT)
    print(f"Queue headroom: {headroom} slots")
    
    # Estimate impact of new enrollments
    print(f"\n=== Impact Analysis ===")
    
    # Get single-reel audio that would pass new thresholds
    all_reels = sb.table('reels') \
        .select('audio_id, velocity_score, view_count, like_count') \
        .not_.is_('audio_id', 'null') \
        .execute()
    
    audio_reel_counts = {}
    for reel in all_reels.data:
        aid = reel.get('audio_id')
        if aid:
            if aid not in audio_reel_counts:
                audio_reel_counts[aid] = []
            audio_reel_counts[aid].append(reel)
    
    # Find single-reel audio not in tracked_audio
    tracked_ids = {row['audio_id'] for row in tracked_res.data}
    single_reel_not_tracked = []
    
    for aid, reels in audio_reel_counts.items():
        if len(reels) == 1 and aid not in tracked_ids:
            reel = reels[0]
            vel = reel.get('velocity_score', 0.0) or 0.0
            views = reel.get('view_count', 0) or 0
            likes = reel.get('like_count', 0) or 0
            
            if vel > 5000 or (likes > 1000 and views > 10000):
                single_reel_not_tracked.append(aid)
    
    estimated_new_enrollments = len(single_reel_not_tracked)
    print(f"Estimated new enrollments from velocity criteria: {estimated_new_enrollments}")
    
    # Estimate future active tracked audio
    future_tracked_count = tracked_count + estimated_new_enrollments
    print(f"Future tracked_audio count: {future_tracked_count} (current: {tracked_count})")
    
    # Estimate queue utilization with new enrollments
    # Assume 70% of newly enrolled audio becomes active (conservative estimate)
    estimated_new_active = int(estimated_new_enrollments * 0.7)
    future_active_count = len(tracked_active) + estimated_new_active
    future_utilization = min(future_active_count, QUEUE_LIMIT) / QUEUE_LIMIT * 100
    
    print(f"Estimated future active tracked audio: {future_active_count}")
    print(f"Estimated future queue utilization: {future_utilization:.1f}%")
    
    if future_utilization > 90:
        print("\nAssessment: HIGH RISK - Queue would be near capacity")
        print("Recommendation: Increase QUEUE_LIMIT or reduce enrollment criteria")
    elif future_utilization > 75:
        print("\nAssessment: MODERATE RISK - Queue would be heavily utilized")
        print("Recommendation: Monitor closely, consider increasing QUEUE_LIMIT")
    elif future_utilization > 50:
        print("\nAssessment: LOW RISK - Adequate headroom remains")
        print("Recommendation: Proceed with monitoring")
    else:
        print("\nAssessment: NO RISK - Plenty of queue capacity")
        print("Recommendation: Safe to proceed")
    
    # Check if existing high-priority trends would get crowded out
    print(f"\n=== Priority Queue Analysis ===")
    
    # Get current top 30 active audio
    sorted_active = sorted(tracked_active.items(), key=lambda x: x[1], reverse=True)
    current_top_30 = [aid for aid, freq in sorted_active[:QUEUE_LIMIT]]
    
    print(f"Current top {QUEUE_LIMIT} active audio (by frequency):")
    for i, (aid, freq) in enumerate(sorted_active[:10], 1):  # Show top 10
        print(f"  {i}. Audio ID {aid}: {freq} recent reels")
    
    if len(sorted_active) > 10:
        print(f"  ... and {len(sorted_active) - 10} more")
    
    # Simulate adding new enrollments
    # New enrollments would start with frequency=1, so they'd be at the bottom
    print(f"\nNew enrollments would start at bottom of priority queue (frequency=1)")
    print(f"Existing high-frequency trends would maintain priority")
    
    return True

if __name__ == '__main__':
    check_queue_capacity()
