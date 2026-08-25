#!/usr/bin/env python3
"""
Test Spotify API connection with the provided credentials
"""

import os
import sys
import io
import requests
from dotenv import load_dotenv

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Load .env from project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

def test_spotify_connection():
    """Test Spotify API connection"""
    
    print("=== Spotify API Connection Test ===\n")
    
    # Get credentials
    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
    
    print(f"Client ID: {'✅ Found' if client_id else '❌ Missing'}")
    print(f"Client Secret: {'✅ Found' if client_secret else '❌ Missing'}")
    
    if not client_id or not client_secret:
        print("\n❌ Spotify credentials not found in environment variables")
        print("Please ensure they are in your .env file")
        return False
    
    # Test token endpoint
    print("\nTesting Spotify token endpoint...")
    
    try:
        token_url = 'https://accounts.spotify.com/api/token'
        data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        response = requests.post(token_url, data=data, timeout=10)
        
        if response.status_code == 200:
            print("✅ Successfully obtained Spotify access token")
            token_data = response.json()
            access_token = token_data.get('access_token')
            print(f"Token type: {token_data.get('token_type')}")
            print(f"Expires in: {token_data.get('expires_in')} seconds")
            
            # Test a simple API call
            print("\nTesting Spotify API call...")
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Try to get global viral chart
            test_url = 'https://api.spotify.com/v1/charts/global/viral/weekly'
            test_response = requests.get(test_url, headers=headers, timeout=10)
            
            if test_response.status_code == 200:
                print("✅ Successfully accessed Spotify Viral 50 chart")
                chart_data = test_response.json()
                entries = chart_data.get('entries', [])
                print(f"Chart entries received: {len(entries)}")
                if entries:
                    print(f"First entry: {entries[0].get('track', {}).get('name', 'Unknown')}")
            else:
                print(f"⚠️  Viral 50 endpoint returned status: {test_response.status_code}")
                print("Trying alternative Spotify endpoint...")
                
                # Try alternative endpoint - search for trending tracks
                search_url = 'https://api.spotify.com/v1/search?q=year:2024&type=track&limit=5'
                search_response = requests.get(search_url, headers=headers, timeout=10)
                
                if search_response.status_code == 200:
                    print("✅ Successfully accessed Spotify Search API")
                    search_data = search_response.json()
                    tracks = search_data.get('tracks', {}).get('items', [])
                    print(f"Search results: {len(tracks)} tracks")
                    if tracks:
                        print(f"First track: {tracks[0].get('name', 'Unknown')}")
                else:
                    print(f"⚠️  Search API also failed with status: {search_response.status_code}")
            
            return True
            
        else:
            print(f"❌ Token request failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

if __name__ == '__main__':
    success = test_spotify_connection()
    sys.exit(0 if success else 1)
