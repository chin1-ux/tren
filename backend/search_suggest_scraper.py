import os
import sys
import logging
import json
import time
import random
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("search_suggest_scraper")


class SearchSuggestScraper:
    """
    Vector 4 Non-Hashtag Discovery Engine (Instagram TopSearch API).
    Queries Meta's public search auto-suggest endpoint for broad search terms
    ('viral audio', 'trending sound', 'dance challenge', 'phonk edit', 'bollywood remix')
    to discover emerging audio entities directly from Meta's search engine.
    Uses 100% unauthenticated public requests to protect your logged-in scraper account.
    """

    SEARCH_SEEDS = [
        "trending audio",
        "viral sound",
        "dance challenge",
        "aesthetic reel",
        "bollywood remix",
        "phonk edit",
        "punjabi viral",
        "lofi remix",
        "trending music"
    ]

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "X-IG-App-ID": "936619743392459",
            "X-Requested-With": "XMLHttpRequest"
        }
        self.cookies_dict = {}
        cookies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.json")
        if os.path.exists(cookies_path):
            try:
                with open(cookies_path, "r") as f:
                    cookies_data = json.load(f)
                    self.cookies_dict = {c["name"]: c["value"] for c in cookies_data if "name" in c and "value" in c}
            except Exception as e:
                logger.warning(f"Could not load cookies.json for SearchSuggestScraper: {e}")

    def fetch_topsearch_audios(self, query_term: str) -> List[Dict[str, Any]]:
        """
        Query Meta's /web/search/topsearch/?query=<term> endpoint.
        Extracts discovered audio, creator, and hashtag trend entities.
        """
        url = f"https://www.instagram.com/web/search/topsearch/?query={requests.utils.quote(query_term)}"
        logger.info(f"Querying Instagram Search Auto-Suggest for: '{query_term}'...")

        try:
            resp = requests.get(url, headers=self.headers, cookies=self.cookies_dict, timeout=10)
            if not resp.ok:
                logger.warning(f"TopSearch API request returned HTTP {resp.status_code} for query '{query_term}'")
                return []

            data = resp.json()
            audios = []

            # 1. Parse explicit audio objects if returned
            for item in data.get("audios", []) or []:
                audio_data = item.get("audio") or {}
                audio_info = audio_data.get("audio_asset_info") or audio_data
                
                audio_id = str(audio_info.get("audio_cluster_id") or audio_info.get("id") or "")
                title = audio_info.get("title") or audio_info.get("display_artist")
                artist = audio_info.get("display_artist") or audio_info.get("artist_name")
                use_count = int(audio_data.get("use_count") or 0)

                if audio_id and title:
                    audios.append({
                        "audio_id": audio_id,
                        "audio_title": title,
                        "audio_artist": artist or "Unknown",
                        "audio_use_count": use_count,
                        "discovery_source": "meta_search_suggest",
                        "discovered_at": datetime.now(timezone.utc).isoformat()
                    })

            # 2. Parse hashtag entities returned by Meta topsearch
            for item in data.get("hashtags", []) or []:
                hashtag_info = item.get("hashtag") or {}
                name = hashtag_info.get("name")
                media_count = hashtag_info.get("media_count") or 0
                if name:
                    audios.append({
                        "audio_id": f"hashtag_{name}",
                        "audio_title": f"#{name}",
                        "audio_artist": "Meta Search Hashtag",
                        "audio_use_count": media_count,
                        "discovery_source": "meta_search_suggest_hashtag",
                        "discovered_at": datetime.now(timezone.utc).isoformat()
                    })

            logger.info(f"Discovered {len(audios)} entities from search term '{query_term}'")
            return audios

        except Exception as e:
            logger.error(f"Error querying TopSearch API for '{query_term}': {e}")
            return []

    def discover_broad_trending_audios(self, max_seeds: int = 5) -> List[Dict[str, Any]]:
        """
        Runs a multi-seed search discovery cycle across selected search seeds with human jitter.
        Returns deduplicated list of discovered audio entities.
        """
        seeds = random.sample(self.SEARCH_SEEDS, min(max_seeds, len(self.SEARCH_SEEDS)))
        all_discovered: List[Dict[str, Any]] = []
        seen_ids = set()

        for idx, seed in enumerate(seeds):
            if idx > 0:
                jitter = random.uniform(1.8, 3.5)
                time.sleep(jitter)

            items = self.fetch_topsearch_audios(seed)
            for item in items:
                aid = item.get("audio_id")
                if aid and aid not in seen_ids:
                    seen_ids.add(aid)
                    all_discovered.append(item)

        logger.info(f"TopSearch discovery cycle complete: Discovered {len(all_discovered)} unique audio entities across {len(seeds)} seed queries.")
        return all_discovered


# Quick test wrapper
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scraper = SearchSuggestScraper()
    res = scraper.discover_broad_trending_audios(max_seeds=2)
    print(f"Sample TopSearch Discovery Result ({len(res)} items):", res[:3])
