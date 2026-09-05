import os
import logging
import requests
from typing import List, Dict, Any
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("spotify_fetcher")

# Spotify Viral 50 Playlist IDs for target markets
VIRAL_50_PLAYLISTS = {
    "IN": "37i9dQZEVXbMz5rOwDMIpz", # India
    "US": "37i9dQZEVXbKuaTI1Z1Afx", # USA
    "GB": "37i9dQZEVXbL3DLHfQeDmV", # UK
    "BR": "37i9dQZEVXbMOkSwG072hV", # Brazil
    "KR": "37i9dQZEVXbNxXF4SkHj9F", # South Korea
    "JP": "37i9dQZEVXbINTEnbFeb8d", # Japan
    "GLOBAL": "37i9dQZEVXbLiRSasKsNU9"
}

class SpotifyFetcher:
    def __init__(self):
        # Try both backend and root env files
        load_dotenv("backend/.env")
        load_dotenv(".env")
        
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            logger.warning("Supabase credentials missing.")
            self.supabase = None
        else:
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
            
        self.access_token = None

    def _get_token(self) -> str:
        """Fetch Spotify access token"""
        if not self.client_id or not self.client_secret:
            raise ValueError("Spotify credentials missing")
            
        auth_url = 'https://accounts.spotify.com/api/token'
        res = requests.post(auth_url, data={
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }, timeout=10)
        
        if res.status_code == 200:
            self.access_token = res.json().get('access_token')
            return self.access_token
        else:
            raise Exception(f"Failed to get Spotify token: {res.text}")

    def fetch_viral_playlist(self, country_code: str) -> List[Dict]:
        """Fetch the top 50 viral tracks for a specific country"""
        playlist_id = VIRAL_50_PLAYLISTS.get(country_code)
        if not playlist_id:
            logger.warning(f"No Viral 50 playlist ID known for {country_code}")
            return []
            
        if not self.access_token:
            self._get_token()
            
        url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?limit=50"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            logger.error(f"Failed to fetch playlist {country_code}: {res.text}")
            return []
            
        data = res.json()
        tracks = []
        for i, item in enumerate(data.get("items", [])):
            track = item.get("track")
            if not track:
                continue
            tracks.append({
                "market": country_code,
                "rank": i + 1,
                "title": track.get("name"),
                "artist": ", ".join([a.get("name") for a in track.get("artists", [])]),
                "spotify_id": track.get("id"),
                "popularity": track.get("popularity", 0),
                "is_new": item.get("added_at", "") > (datetime.now(timezone.utc).isoformat())
            })
        return tracks
        
    def check_crossovers(self, market_tracks: List[Dict]) -> List[Dict]:
        """Cross-reference Spotify viral tracks with our content_trends/tracked_audio"""
        if not self.supabase or not market_tracks:
            return []
            
        # We look for tracks that are viral in KR/JP/US but not yet huge in India
        crossovers = []
        
        for track in market_tracks:
            # Check if we already track this audio
            # Simple text search since Instagram audio titles often loosely match Spotify
            title_query = track['title'].split("(")[0].strip() # Remove (feat. X)
            
            try:
                # 1. Check if it's already a trend in our DB
                res = self.supabase.table("content_trends") \
                    .select("id, status") \
                    .eq("trend_type", "audio") \
                    .ilike("trend_name", f"%{title_query}%") \
                    .execute()
                    
                is_tracked = len(res.data) > 0
                
                # If it's highly ranked internationally but we don't have it, it's a crossover opportunity
                if not is_tracked and track["rank"] <= 10 and track["market"] in ["KR", "JP", "US", "GB"]:
                    crossover = {
                        "trend_type": "audio",
                        "trend_name": f"{track['title']} - {track['artist']}",
                        "template_pattern": f"spotify_viral_{track['spotify_id']}",
                        "topic_keywords": [track['artist'], "Spotify Viral", track['market']],
                        "velocity_avg": float(100 - track['rank']),
                        "confidence": 75.0,
                        "status": "emerging",
                        "niche_relevance": {"dance": 0.8, "lifestyle": 0.6},
                        "adaptation_briefs": {
                            "dance": f"This track is # {track['rank']} on Spotify Viral {track['market']}. Choreograph a routine before it hits India.",
                            "lifestyle": f"Early adopter audio: Use this rising hit from {track['market']} for your next vlog."
                        }
                    }
                    crossovers.append(crossover)
            except Exception as e:
                logger.error(f"Error checking crossover for {track['title']}: {e}")
                
        return crossovers
        
    def run_sync(self):
        """Fetch all viral markets and identify crossovers"""
        logger.info("Starting Spotify Viral 50 sync...")
        all_crossovers = []
        
        for market in ["IN", "US", "GB", "BR", "KR", "JP"]:
            tracks = self.fetch_viral_playlist(market)
            logger.info(f"Fetched {len(tracks)} tracks for {market}")
            
            if market != "IN": # We use international markets to predict Indian trends
                cross = self.check_crossovers(tracks)
                if cross:
                    all_crossovers.extend(cross)
                    
        if all_crossovers and self.supabase:
            logger.info(f"Found {len(all_crossovers)} potential crossover trends. Saving to DB...")
            # We can upsert these to content_trends
            to_upsert = []
            for c in all_crossovers:
                to_upsert.append(c)
                
            try:
                self.supabase.table("content_trends").upsert(
                    to_upsert, on_conflict="trend_type,template_pattern"
                ).execute()
            except Exception as e:
                logger.error(f"Failed to save crossovers: {e}")

if __name__ == "__main__":
    fetcher = SpotifyFetcher()
    fetcher.run_sync()
