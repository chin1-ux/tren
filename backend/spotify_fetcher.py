import os
import logging
import requests
from typing import List, Dict, Any
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("spotify_fetcher")

# Target viral queries for search-based ingestion
VIRAL_SEARCH_QUERIES = [
    "speed up remix",
    "tiktok viral",
    "trending dance audio",
    "viral reels sound",
    "remix 2026",
    "sped up dance",
    "global viral audio",
    "dance challenge sound"
]

VIRAL_50_PLAYLISTS = {
    "IN": "37i9dQZEVXbMz5rOwDMIpz",
    "US": "37i9dQZEVXbKuaTI1Z1Afx",
    "GB": "37i9dQZEVXbL3DLHfQeDmV",
    "BR": "37i9dQZEVXbMOkSwG072hV",
    "KR": "37i9dQZEVXbNxXF4SkHj9F",
    "JP": "37i9dQZEVXbINTEnbFeb8d",
    "GLOBAL": "37i9dQZEVXbLiRSasKsNU9"
}

class SpotifyFetcher:
    def __init__(self):
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
        """Fetch Spotify access token using Client Credentials Flow"""
        if not self.client_id or not self.client_secret:
            raise ValueError("Spotify credentials missing in .env")
            
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

    def fetch_search_tracks(self, query: str) -> List[Dict]:
        """Fetch viral tracks via Spotify Track Search API (unblocked for Client Credentials)"""
        if not self.access_token:
            self._get_token()
            
        url = f"https://api.spotify.com/v1/search?q={requests.utils.quote(query)}&type=track&limit=10"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200:
                logger.error(f"Failed search query '{query}': {res.status_code} {res.text}")
                return []
                
            data = res.json()
            items = data.get("tracks", {}).get("items", [])
            tracks = []
            for i, track in enumerate(items):
                if not track:
                    continue
                tracks.append({
                    "market": "SEARCH",
                    "rank": i + 1,
                    "title": track.get("name"),
                    "artist": ", ".join([a.get("name") for a in track.get("artists", [])]),
                    "spotify_id": track.get("id"),
                    "popularity": track.get("popularity", 0),
                    "query": query
                })
            return tracks
        except Exception as e:
            logger.error(f"Error fetching search tracks for '{query}': {e}")
            return []

    def fetch_viral_playlist(self, country_code: str) -> List[Dict]:
        """Fetch the top 50 viral tracks for a specific country (Playlist endpoint)"""
        playlist_id = VIRAL_50_PLAYLISTS.get(country_code)
        if not playlist_id:
            logger.warning(f"No Viral 50 playlist ID known for {country_code}")
            return []
            
        if not self.access_token:
            self._get_token()
            
        url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?limit=50"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200:
                logger.warning(f"Playlist {country_code} direct fetch restricted ({res.status_code}). Using search fallback.")
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
        except Exception as e:
            logger.error(f"Error fetching playlist {country_code}: {e}")
            return []

    def check_crossovers(self, market_tracks: List[Dict]) -> List[Dict]:
        """Cross-reference Spotify viral tracks with our content_trends"""
        if not self.supabase or not market_tracks:
            return []
            
        crossovers = []
        
        for track in market_tracks:
            title_clean = track['title'].split("(")[0].split("-")[0].strip()
            if not title_clean or len(title_clean) < 3:
                continue
                
            try:
                # Check if it's already present in content_trends
                res = self.supabase.table("content_trends") \
                    .select("id, status") \
                    .eq("trend_type", "audio") \
                    .ilike("trend_name", f"%{title_clean}%") \
                    .execute()
                    
                is_tracked = len(res.data) > 0
                
                if not is_tracked:
                    spotify_pattern = f"spotify_viral_{track['spotify_id']}"
                    crossover = {
                        "trend_type": "audio",
                        "trend_name": f"{track['title']} - {track['artist']}",
                        "template_pattern": spotify_pattern,
                        "topic_keywords": [track['artist'], "Spotify Viral", track.get('market', 'GLOBAL')],
                        "velocity_avg": float(100 - track.get('rank', 10)),
                        "confidence": 85.0,
                        "status": "candidate",
                        "niche_relevance": {"dance": 0.9, "lifestyle": 0.7, "remix": 0.95},
                        "adaptation_briefs": {
                            "dance": f"Rising Spotify sound '{track['title']}' by {track['artist']}. Early crossover opportunity for dance/reels creators.",
                            "lifestyle": f"Viral audio hit: Use '{track['title']}' before it saturates."
                        }
                    }
                    crossovers.append(crossover)
            except Exception as e:
                logger.error(f"Error checking crossover for {track['title']}: {e}")
                
        return crossovers

    def run_sync(self):
        """Fetch all viral markets & search queries to identify global crossover trends"""
        logger.info("Starting Spotify Viral & Search Ingestion...")
        all_tracks = []
        
        # 1. Try playlist endpoints (fallback to search if forbidden)
        for market in ["IN", "US", "GB", "BR", "KR", "JP", "GLOBAL"]:
            tracks = self.fetch_viral_playlist(market)
            if tracks:
                logger.info(f"Fetched {len(tracks)} playlist tracks for {market}")
                all_tracks.extend(tracks)
                
        # 2. Direct Spotify Track Search for global trending sounds
        for query in VIRAL_SEARCH_QUERIES:
            s_tracks = self.fetch_search_tracks(query)
            if s_tracks:
                logger.info(f"Fetched {len(s_tracks)} search tracks for query '{query}'")
                all_tracks.extend(s_tracks)

        logger.info(f"Total Spotify tracks collected: {len(all_tracks)}")
        
        # 3. Identify and register new crossover audio trends
        if all_tracks and self.supabase:
            crossovers = self.check_crossovers(all_tracks)
            logger.info(f"Found {len(crossovers)} new potential crossover trends.")
            
            if crossovers:
                # Deduplicate by template_pattern
                seen_patterns = set()
                deduped = []
                for c in crossovers:
                    if c["template_pattern"] not in seen_patterns:
                        seen_patterns.add(c["template_pattern"])
                        deduped.append(c)
                        
                logger.info(f"Saving {len(deduped)} unique crossover audio trends to Supabase...")
                try:
                    self.supabase.table("content_trends").upsert(
                        deduped, on_conflict="trend_type,template_pattern"
                    ).execute()
                    logger.info("Successfully upserted Spotify crossover trends to content_trends table!")
                except Exception as e:
                    logger.error(f"Failed to save crossovers: {e}")

if __name__ == "__main__":
    fetcher = SpotifyFetcher()
    fetcher.run_sync()
