import os
import logging
import requests
from typing import List, Dict, Any
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client
from trend_constants import VINTAGE_CATALOG_AGE_DAYS, VINTAGE_CATALOG_AGE_YEARS_FALLBACK

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
                album_info = track.get("album", {}) or {}
                rel_date = album_info.get("release_date")
                rel_year = None
                if rel_date:
                    try:
                        rel_year = int(rel_date.split("-")[0])
                    except (ValueError, IndexError):
                        pass

                tracks.append({
                    "market": "SEARCH",
                    "rank": i + 1,
                    "title": track.get("name"),
                    "artist": ", ".join([a.get("name") for a in track.get("artists", [])]),
                    "spotify_id": track.get("id"),
                    "popularity": track.get("popularity", 0),
                    "query": query,
                    "release_date": rel_date,
                    "release_year": rel_year
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
                album_info = track.get("album", {}) or {}
                rel_date = album_info.get("release_date")
                rel_year = None
                if rel_date:
                    try:
                        rel_year = int(rel_date.split("-")[0])
                    except (ValueError, IndexError):
                        pass

                tracks.append({
                    "market": country_code,
                    "rank": i + 1,
                    "title": track.get("name"),
                    "artist": ", ".join([a.get("name") for a in track.get("artists", [])]),
                    "spotify_id": track.get("id"),
                    "popularity": track.get("popularity", 0),
                    "is_new": item.get("added_at", "") > (datetime.now(timezone.utc).isoformat()),
                    "release_date": rel_date,
                    "release_year": rel_year
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
            try:
                title_clean = track['title'].split("(")[0].split("-")[0].strip()
                if not title_clean or len(title_clean) < 3:
                    continue
                    
                # Tier 2 Normalized Match (Exact Title + Exact Primary Artist using explicit 'artist' column)
                from audio_utils import _normalize_audio_title_and_artist, _extract_remix_indicators

                norm_title, norm_artist = _normalize_audio_title_and_artist(track['title'], track['artist'])
                remix_kw = _extract_remix_indicators(track['title'])

                res = self.supabase.table("content_trends") \
                    .select("id, trend_name, artist, status, template_pattern") \
                    .eq("trend_type", "audio") \
                    .execute()

                is_tracked = False
                for existing in (res.data or []):
                    e_norm_t, e_norm_a = _normalize_audio_title_and_artist(existing.get("trend_name", ""), existing.get("artist", ""))
                    e_remix_kw = _extract_remix_indicators(existing.get("trend_name", ""))

                    if norm_title == e_norm_t and norm_artist == e_norm_a and remix_kw == e_remix_kw:
                        is_tracked = True
                        break

                if not is_tracked:
                    spotify_pattern = f"spotify_viral_{track['spotify_id']}"
                    rel_date = track.get("release_date")
                    rel_year = track.get("release_year")
                    
                    # Exact day-based age check against VINTAGE_CATALOG_AGE_DAYS
                    is_vintage = False
                    if rel_date:
                        try:
                            parts = rel_date.split("-")
                            if len(parts) == 3:
                                dt_rel = datetime.strptime(rel_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                                age_days = (datetime.now(timezone.utc) - dt_rel).days
                                if age_days >= VINTAGE_CATALOG_AGE_DAYS:
                                    is_vintage = True
                            elif len(parts) == 1 and rel_year:
                                # Fallback if only year was provided in API response (wider margin for fuzzy year precision)
                                if (datetime.now(timezone.utc).year - rel_year) >= VINTAGE_CATALOG_AGE_YEARS_FALLBACK:
                                    is_vintage = True
                        except Exception as parse_err:
                            logger.debug(f"Could not parse release_date '{rel_date}': {parse_err}")

                    niche_rel = {"dance": 0.9, "lifestyle": 0.7, "remix": 0.95}
                    if is_vintage:
                        niche_rel["vintage_catalog"] = True
                        logger.debug(f"Skipping vintage track '{track['title']}' ({rel_date}) from crossover candidate ingestion.")
                        continue

                    crossover = {
                        "trend_type": "audio",
                        "trend_name": f"{track['title']} - {track['artist']}",
                        "artist": track['artist'],
                        "template_pattern": spotify_pattern,
                        "topic_keywords": [track['artist'], "Spotify Viral", track.get('market', 'GLOBAL')],
                        "velocity_avg": float(100 - track.get('rank', 10)),
                        "confidence": 85.0,
                        "status": "candidate",
                        "release_date": rel_date,
                        "release_year": rel_year,
                        "niche_relevance": niche_rel,
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
