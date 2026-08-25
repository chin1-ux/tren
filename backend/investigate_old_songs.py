"""
Investigate old song patterns in current trends.
This script analyzes trends to identify potentially old songs that may be evergreen vs genuine viral revivals.
"""
import os
import sys
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def load_environment():
    """Load environment variables from .env file"""
    load_dotenv()
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        sys.exit(1)
    
    return create_client(supabase_url, supabase_key)

def analyze_trend_patterns(supabase: Client):
    """Analyze current trends for old song patterns"""
    print("=== Investigating Old Song Patterns in Trends ===\n")
    
    # Fetch recent trends with relevant metadata
    try:
        res = supabase.table('trends').select(
            'id, audio_title, audio_artist, first_detected_at, status, '
            'audio_use_count, velocity_avg, composite_score'
        ).order('first_detected_at', desc=True).limit(50).execute()
        
        trends = res.data
        print(f"Found {len(trends)} recent trends to analyze\n")
        
        # Analyze patterns
        now = datetime.now(timezone.utc)
        old_song_candidates = []
        recent_trends = []
        
        for trend in trends:
            audio_title = trend.get('audio_title', 'Unknown')
            audio_artist = trend.get('audio_artist', 'Unknown')
            first_detected = trend.get('first_detected_at')
            status = trend.get('status', 'unknown')
            audio_use_count = trend.get('audio_use_count', 0)
            velocity_avg = trend.get('velocity_avg', 0)
            
            # Parse first_detected_at
            if first_detected:
                try:
                    if first_detected.endswith('Z'):
                        first_detected = first_detected[:-1] + '+00:00'
                    detected_dt = datetime.fromisoformat(first_detected)
                    if detected_dt.tzinfo is None:
                        detected_dt = detected_dt.replace(tzinfo=timezone.utc)
                    age_hours = (now - detected_dt).total_seconds() / 3600
                except Exception as e:
                    print(f"Error parsing date for {audio_title}: {e}")
                    age_hours = 0
            else:
                age_hours = 0
            
            # Check for potential old song indicators
            old_song_indicators = []
            
            # Indicator 1: High usage count but low velocity (evergreen pattern)
            if audio_use_count > 500000 and velocity_avg < 2.0:
                old_song_indicators.append("High usage + low velocity (evergreen pattern)")
            
            # Indicator 2: Very old first detection (but still active)
            if age_hours > 168:  # More than 1 week old
                old_song_indicators.append(f"Old detection ({age_hours:.1f}h ago)")
            
            # Indicator 3: Generic title patterns
            generic_titles = ['original audio', 'unknown', 'instrumental', 'background music']
            if any(gt in audio_title.lower() for gt in generic_titles):
                old_song_indicators.append("Generic title pattern")
            
            # Indicator 4: Classic artist names (heuristic)
            classic_artists = ['ar rahman', 'arijit singh', 'shreya ghoshal', 'sonu nigam', 'lata mangeshkar']
            if any(ca in audio_artist.lower() for ca in classic_artists):
                old_song_indicators.append("Classic artist (potential evergreen)")
            
            trend_info = {
                'title': audio_title,
                'artist': audio_artist,
                'status': status,
                'age_hours': age_hours,
                'use_count': audio_use_count,
                'velocity': velocity_avg,
                'indicators': old_song_indicators
            }
            
            if old_song_indicators:
                old_song_candidates.append(trend_info)
            else:
                recent_trends.append(trend_info)
        
        # Print analysis results
        print("=== POTENTIAL OLD SONG / EVERGREEN CANDIDATES ===")
        print(f"Found {len(old_song_candidates)} potential old song candidates\n")
        
        for i, candidate in enumerate(old_song_candidates, 1):
            print(f"{i}. {candidate['title']} - {candidate['artist']}")
            print(f"   Status: {candidate['status']}")
            print(f"   Age: {candidate['age_hours']:.1f} hours since detection")
            print(f"   Use Count: {candidate['use_count']:,}")
            print(f"   Velocity: {candidate['velocity']:.2f}")
            print(f"   Indicators: {', '.join(candidate['indicators'])}")
            print()
        
        print("\n=== RECENT GENUINE TRENDS ===")
        print(f"Found {len(recent_trends)} recent genuine trends\n")
        
        for i, trend in enumerate(recent_trends[:10], 1):
            print(f"{i}. {trend['title']} - {trend['artist']}")
            print(f"   Status: {trend['status']}")
            print(f"   Age: {trend['age_hours']:.1f} hours since detection")
            print(f"   Use Count: {trend['use_count']:,}")
            print(f"   Velocity: {trend['velocity']:.2f}")
            print()
        
        # Summary statistics
        print("\n=== SUMMARY STATISTICS ===")
        print(f"Total trends analyzed: {len(trends)}")
        print(f"Potential old song/evergreen: {len(old_song_candidates)}")
        print(f"Recent genuine trends: {len(recent_trends)}")
        
        if old_song_candidates:
            avg_velocity_old = sum(c['velocity'] for c in old_song_candidates) / len(old_song_candidates)
            avg_use_old = sum(c['use_count'] for c in old_song_candidates) / len(old_song_candidates)
            print(f"\nOld song averages:")
            print(f"  Velocity: {avg_velocity_old:.2f}")
            print(f"  Use Count: {avg_use_old:,.0f}")
        
        if recent_trends:
            avg_velocity_new = sum(t['velocity'] for t in recent_trends) / len(recent_trends)
            avg_use_new = sum(t['use_count'] for t in recent_trends) / len(recent_trends)
            print(f"\nRecent trend averages:")
            print(f"  Velocity: {avg_velocity_new:.2f}")
            print(f"  Use Count: {avg_use_new:,.0f}")
        
    except Exception as e:
        print(f"Error analyzing trends: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    supabase = load_environment()
    analyze_trend_patterns(supabase)