#!/usr/bin/env python3
"""
Check for Beretta/El De Las R's references in the reels table
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

def check_beretta_references():
    """Query reels table for Beretta/El De Las R's references"""
    
    # Search for Beretta in audio_title (case-insensitive)
    print("Searching for 'Beretta' in audio_title...")
    beretta_audio_title = sb.table('reels').select('*').ilike('audio_title', '%beretta%').execute()
    print(f"Found {len(beretta_audio_title.data)} reels with 'Beretta' in audio_title")
    if beretta_audio_title.data:
        for reel in beretta_audio_title.data[:3]:  # Show first 3 samples
            print(f"  - ID: {reel['id']}, audio_title: {reel.get('audio_title')}, audio_artist: {reel.get('audio_artist')}, hashtags: {reel.get('hashtags')}")
    
    # Search for Beretta in audio_artist (case-insensitive)
    print("\nSearching for 'Beretta' in audio_artist...")
    beretta_audio_artist = sb.table('reels').select('*').ilike('audio_artist', '%beretta%').execute()
    print(f"Found {len(beretta_audio_artist.data)} reels with 'Beretta' in audio_artist")
    if beretta_audio_artist.data:
        for reel in beretta_audio_artist.data[:3]:  # Show first 3 samples
            print(f"  - ID: {reel['id']}, audio_title: {reel.get('audio_title')}, audio_artist: {reel.get('audio_artist')}, hashtags: {reel.get('hashtags')}")
    
    # Search for Beretta in caption (case-insensitive)
    print("\nSearching for 'Beretta' in caption...")
    beretta_caption = sb.table('reels').select('*').ilike('caption', '%beretta%').execute()
    print(f"Found {len(beretta_caption.data)} reels with 'Beretta' in caption")
    if beretta_caption.data:
        for reel in beretta_caption.data[:3]:  # Show first 3 samples
            print(f"  - ID: {reel['id']}, audio_title: {reel.get('audio_title')}, audio_artist: {reel.get('audio_artist')}, caption: {reel.get('caption')[:100]}...")
    
    # Search for El De Las R's in audio_title (case-insensitive)
    print("\nSearching for 'El De Las R' in audio_title...")
    el_de_las_r_audio_title = sb.table('reels').select('*').ilike('audio_title', '%el de las r%').execute()
    print(f"Found {len(el_de_las_r_audio_title.data)} reels with 'El De Las R' in audio_title")
    if el_de_las_r_audio_title.data:
        for reel in el_de_las_r_audio_title.data[:3]:  # Show first 3 samples
            print(f"  - ID: {reel['id']}, audio_title: {reel.get('audio_title')}, audio_artist: {reel.get('audio_artist')}, hashtags: {reel.get('hashtags')}")
    
    # Search for El De Las R's in audio_artist (case-insensitive)
    print("\nSearching for 'El De Las R' in audio_artist...")
    el_de_las_r_audio_artist = sb.table('reels').select('*').ilike('audio_artist', '%el de las r%').execute()
    print(f"Found {len(el_de_las_r_audio_artist.data)} reels with 'El De Las R' in audio_artist")
    if el_de_las_r_audio_artist.data:
        for reel in el_de_las_r_audio_artist.data[:3]:  # Show first 3 samples
            print(f"  - ID: {reel['id']}, audio_title: {reel.get('audio_title')}, audio_artist: {reel.get('audio_artist')}, hashtags: {reel.get('hashtags')}")
    
    # Search for El De Las R's in caption (case-insensitive)
    print("\nSearching for 'El De Las R' in caption...")
    el_de_las_r_caption = sb.table('reels').select('*').ilike('caption', '%el de las r%').execute()
    print(f"Found {len(el_de_las_r_caption.data)} reels with 'El De Las R' in caption")
    if el_de_las_r_caption.data:
        for reel in el_de_las_r_caption.data[:3]:  # Show first 3 samples
            print(f"  - ID: {reel['id']}, audio_title: {reel.get('audio_title')}, audio_artist: {reel.get('audio_artist')}, caption: {reel.get('caption')[:100]}...")
    
    # Search for Slowed + Reverb variants
    print("\nSearching for 'Slowed + Reverb' in audio_title...")
    slowed_reverb = sb.table('reels').select('*').ilike('audio_title', '%slowed%').execute()
    print(f"Found {len(slowed_reverb.data)} reels with 'Slowed' in audio_title")
    if slowed_reverb.data:
        for reel in slowed_reverb.data[:3]:  # Show first 3 samples
            print(f"  - ID: {reel['id']}, audio_title: {reel.get('audio_title')}, audio_artist: {reel.get('audio_artist')}, hashtags: {reel.get('hashtags')}")
    
    # Search for Electro House variants
    print("\nSearching for 'Electro House' in audio_title...")
    electro_house = sb.table('reels').select('*').ilike('audio_title', '%electro%').execute()
    print(f"Found {len(electro_house.data)} reels with 'Electro' in audio_title")
    if electro_house.data:
        for reel in electro_house.data[:3]:  # Show first 3 samples
            print(f"  - ID: {reel['id']}, audio_title: {reel.get('audio_title')}, audio_artist: {reel.get('audio_artist')}, hashtags: {reel.get('hashtags')}")
    
    # Summary
    total_matches = (
        len(beretta_audio_title.data) + 
        len(beretta_audio_artist.data) + 
        len(beretta_caption.data) +
        len(el_de_las_r_audio_title.data) + 
        len(el_de_las_r_audio_artist.data) + 
        len(el_de_las_r_caption.data)
    )
    
    print(f"\n=== SUMMARY ===")
    print(f"Total unique matches across all searches: {total_matches}")
    
    if total_matches == 0:
        print("CONFIRMED: No reels found with Beretta/El De Las R's references - DISCOVERY GAP")
    else:
        print("FOUND: Reels exist with Beretta/El De Las R's references - investigate attribution/trend engine gap")
    
    return total_matches

if __name__ == '__main__':
    check_beretta_references()
