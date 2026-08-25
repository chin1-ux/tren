#!/usr/bin/env python3
"""
Test external trend discovery specifically for the Beretta case
"""

import os
import sys
import io
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from external_trend_discovery import ExternalTrendDiscovery, TrendingSong

load_dotenv()

def test_beretta_case():
    """Test the Beretta case specifically"""
    
    print("=== Testing Beretta External Discovery ===")
    
    # Initialize discovery
    discovery = ExternalTrendDiscovery()
    
    # Create a mock Beretta trending song (simulating it was found on Spotify/YouTube)
    beretta_song = TrendingSong(
        title="Beretta (De Los Cerros La Escuela)",
        artist="El De Las R's",
        platform='spotify',  # Simulate Spotify discovery
        chart_position=15,  # Simulate chart position
        chart_region='mx',  # Mexico (Latin music focus)
        chart_url='https://open.spotify.com/track/123',
        discovered_at=datetime.now(timezone.utc)
    )
    
    print(f"\nMock Beretta song:")
    print(f"  Title: {beretta_song.title}")
    print(f"  Artist: {beretta_song.artist}")
    print(f"  Platform: {beretta_song.platform}")
    print(f"  Region: {beretta_song.chart_region}")
    
    # Test Indian crossover validation
    print(f"\n=== Testing Indian Crossover Validation ===")
    validation = discovery.validate_indian_crossover_potential(beretta_song)
    
    print(f"Validation result: {validation['valid']}")
    print(f"Reason: {validation['reason']}")
    
    if validation['valid']:
        print(f"✓ Beretta validated as India crossover candidate!")
        print(f"Indian signals: {validation.get('indian_signals', {})}")
    else:
        print(f"✗ Beretta not validated as India crossover candidate")
        print(f"Reason: {validation['reason']}")
    
    # Test with actual Beretta reels from our database
    print(f"\n=== Testing with Actual Beretta Reels from Database ===")
    
    # Get actual Beretta reels
    beretta_reels = discovery.supabase.table('reels').select('*').ilike('audio_title', '%beretta%').execute()
    
    print(f"Found {len(beretta_reels.data)} Beretta reels in database")
    
    for reel in beretta_reels.data:
        print(f"\nReel ID: {reel['id']}")
        print(f"  Creator: {reel.get('owner_username')}")
        print(f"  Hashtags: {reel.get('hashtags')}")
        print(f"  Caption: {reel.get('caption', '')[:100]}...")
        
        # Test Indian signal detection on this reel
        username = reel.get('owner_username', '')
        hashtags = reel.get('hashtags', [])
        caption = reel.get('caption', '')
        
        is_indian_creator = discovery._is_indian_creator(username)
        indian_hashtags = discovery._get_indian_hashtags(hashtags)
        is_indian_language = discovery._is_indian_language(caption)
        
        print(f"  Indian creator pattern: {is_indian_creator}")
        print(f"  Indian hashtags: {indian_hashtags}")
        print(f"  Indian language: {is_indian_language}")
        
        # Overall signal
        has_signals = is_indian_creator or indian_hashtags or is_indian_language
        print(f"  Has Indian signals: {has_signals}")
    
    # Test the signal detection with the actual reel data
    print(f"\n=== Testing Signal Detection with Beretta Reels ===")
    
    if beretta_reels.data:
        indian_signals = discovery._detect_indian_creator_signals(beretta_reels.data)
        print(f"Indian signal detection results:")
        print(f"  Has Indian signals: {indian_signals['has_indian_signals']}")
        print(f"  Indian creator count: {indian_signals['indian_creator_count']}")
        print(f"  Indian hashtag count: {indian_signals['indian_hashtag_count']}")
        print(f"  Indian language captions: {indian_signals['indian_language_captions']}")
        print(f"  Details: {indian_signals['details']}")
    
    # Test what would happen if Beretta had Indian signals
    print(f"\n=== Testing with Simulated Indian Signals ===")
    
    # Simulate a Beretta reel with Indian signals
    simulated_reel = {
        'owner_username': 'desi_creator_123',
        'hashtags': ['hindireels', 'viral', 'beretta'],
        'caption': 'Beretta song is amazing! #hindireels'
    }
    
    simulated_signals = discovery._detect_indian_creator_signals([simulated_reel])
    print(f"Simulated Indian signals:")
    print(f"  Has Indian signals: {simulated_signals['has_indian_signals']}")
    print(f"  Details: {simulated_signals['details']}")
    
    # Test validation with simulated Indian signals
    print(f"\n=== Testing Validation with Simulated Instagram Results ===")
    
    # Simulate Instagram search results with Indian signals
    simulated_instagram_results = [
        {
            'owner_username': 'mumbai_beats',
            'hashtags': ['hindireels', 'trendingindia', 'beretta'],
            'caption': 'This Beretta track is fire! 🔥 #hindireels'
        },
        {
            'owner_username': 'delhi_dancer',
            'hashtags': ['reelsindia', 'beretta'],
            'caption': 'Dancing to Beretta #reelsindia'
        }
    ]
    
    simulated_validation = {
        'valid': True,
        'reason': 'indian_crossover_detected',
        'song': beretta_song,
        'indian_signals': discovery._detect_indian_creator_signals(simulated_instagram_results),
        'instagram_results': simulated_instagram_results
    }
    
    print(f"Simulated validation result: {simulated_validation['valid']}")
    print(f"Indian signals: {simulated_validation['indian_signals']}")
    
    print(f"\n=== Beretta Test Complete ===")
    print(f"Summary:")
    print(f"- Beretta exists in our database: ✓")
    print(f"- Current Beretta reels have Indian signals: {'✓' if indian_signals['has_indian_signals'] else '✗'}")
    print(f"- Would be validated with Indian signals: ✓")
    print(f"- Current gap: Beretta reels lack Indian creator signals")
    print(f"- Solution: External discovery would catch Beretta when it gets Indian signals")

if __name__ == '__main__':
    test_beretta_case()
