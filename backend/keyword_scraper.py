"""
backend/keyword_scraper.py
Keyword Discovery Engine (Order 51).
Intercepts Instagram Search SERP responses without modifying Golden files.
Handles discovery_terms allocation: 70% yield, 30% exploration, 12h cooldown, 5 zero-yield deactivation.
"""

import asyncio
import collections
import json
import logging
import os
import random
import re
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import dotenv
from supabase import Client, create_client

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger("keyword_scraper")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def get_supabase_client() -> Client:
    dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY required.")
    return create_client(url, key)


def extract_items_from_serp(serp_dict: dict) -> List[dict]:
    """Extract media items from xdt_fbsearch__top_serp_graphql response."""
    items = []
    edges = serp_dict.get("edges", [])
    for edge in edges:
        node = edge.get("node", {})
        grid_items = node.get("items", [])
        for item in grid_items:
            if isinstance(item, dict):
                items.append(item)
    return items


def extract_audio_from_item(item: dict) -> dict:
    """Extract audio info if present in item."""
    clips_meta = item.get("clips_metadata") or {}
    music_info = clips_meta.get("music_info") or item.get("music_info") or {}
    minfo = music_info.get("music_info") if isinstance(music_info.get("music_info"), dict) else music_info
    asset = minfo.get("music_asset_info") or {}
    orig = clips_meta.get("original_sound_info") or item.get("original_sound_info") or {}

    audio_id = (
        asset.get("id") or
        asset.get("audio_cluster_id") or
        orig.get("audio_asset_id") or
        orig.get("id") or
        None
    )
    title = asset.get("title") or orig.get("original_audio_title") or None
    artist = asset.get("display_artist") or (orig.get("ig_artist") or {}).get("username") or None
    use_count = asset.get("use_count") or orig.get("use_count") or None

    return {
        "audio_id": str(audio_id) if audio_id else None,
        "audio_title": title,
        "audio_artist": artist,
        "audio_use_count": use_count,
    }


class KeywordScraper:
    def __init__(self, supabase_client: Optional[Client] = None):
        self.sb = supabase_client or get_supabase_client()

    def allocate_terms(self, limit: int = 10) -> List[dict]:
        """
        Allocate next terms according to Order 51 rules:
        - 70% yield (highest new_audios DESC, queries ASC)
        - 30% exploration (lowest queries ASC or new)
        - 12h cooldown: last_used is NULL or last_used < now - 12h
        - active == True
        """
        now = datetime.now(timezone.utc)
        cooldown_threshold = (now - timedelta(hours=12)).isoformat()

        try:
            # Query active terms that are not in cooldown
            res = self.sb.table("discovery_terms") \
                .select("*") \
                .eq("active", True) \
                .or_(f"last_used.is.null,last_used.lt.{cooldown_threshold}") \
                .execute()
            available = res.data or []
        except Exception as e:
            logger.warning(f"Error fetching discovery_terms (table may need migration 009): {e}")
            return []

        if not available:
            return []

        n_yield = max(1, int(limit * 0.7))
        n_explore = limit - n_yield

        # 70% yield pool
        sorted_by_yield = sorted(available, key=lambda x: (x.get("new_audios") or 0, -(x.get("queries") or 0)), reverse=True)
        yield_pool = sorted_by_yield[:n_yield]

        # Remaining for exploration
        remaining = [t for t in available if t["term"] not in {y["term"] for y in yield_pool}]
        if remaining:
            sorted_explore = sorted(remaining, key=lambda x: (x.get("queries") or 0))
            explore_pool = sorted_explore[:n_explore]
        else:
            explore_pool = []

        allocated = yield_pool + explore_pool
        return allocated[:limit]

    def record_term_result(self, term: str, new_audios_found: int):
        """
        Record term query telemetry and handle deactivation after 5 zero-yield runs.
        """
        now = datetime.now(timezone.utc).isoformat()
        try:
            res = self.sb.table("discovery_terms").select("*").eq("term", term).execute()
            if not res.data:
                return
            row = res.data[0]
            curr_queries = (row.get("queries") or 0) + 1
            curr_new = (row.get("new_audios") or 0) + new_audios_found

            # Deactivate if 5 runs with zero yield
            is_active = True
            if curr_queries >= 5 and curr_new == 0:
                is_active = False
                logger.info(f"Deactivating zero-yield term '{term}' (queries={curr_queries}, new_audios=0)")

            self.sb.table("discovery_terms").update({
                "queries": curr_queries,
                "new_audios": curr_new,
                "last_used": now,
                "active": is_active,
            }).eq("term", term).execute()
        except Exception as e:
            logger.error(f"Error recording term result for '{term}': {e}")

    def seed_terms(self) -> List[dict]:
        """
        Generate and persist seeds from:
        1. seed_audios (YouTube charts)
        2. recurring caption terms from top-decile velocity reels (last 7 days)
        Returns the list of seeds and prints the first 40.
        """
        all_seeds: Dict[str, dict] = {}

        # 1. seed_audios
        try:
            res_chart = self.sb.table("seed_audios").select("title, artist, region").execute()
            for r in (res_chart.data or []):
                t = (r.get("title") or "").strip()
                reg = r.get("region") or "GLOBAL"
                if t and len(t) >= 2 and t not in all_seeds:
                    all_seeds[t] = {
                        "term": t,
                        "kind": "chart_title",
                        "lang": None,
                        "region": reg,
                        "queries": 0,
                        "new_audios": 0,
                        "active": True,
                    }
        except Exception as e:
            logger.warning(f"Error reading seed_audios: {e}")

        # 2. Recurring caption terms / hashtags from reels
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            res_reels = self.sb.table("reels") \
                .select("caption, hashtags") \
                .gte("created_at", cutoff) \
                .order("view_count", desc=True) \
                .limit(500) \
                .execute()
            
            tag_counter = collections.Counter()
            for r in (res_reels.data or []):
                for tag in (r.get("hashtags") or []):
                    clean_tag = re.sub(r'[^a-zA-Z0-9_\u0600-\u06FF\uac00-\ud7a3\u0400-\u04FF]', '', tag).lower()
                    if len(clean_tag) >= 3:
                        tag_counter[clean_tag] += 1

            for tag, count in tag_counter.most_common(50):
                if tag not in all_seeds:
                    all_seeds[tag] = {
                        "term": tag,
                        "kind": "caption_tag",
                        "lang": None,
                        "region": "GLOBAL",
                        "queries": 0,
                        "new_audios": 0,
                        "active": True,
                    }
        except Exception as e:
            logger.warning(f"Error analyzing reel captions: {e}")

        seeds_list = list(all_seeds.values())

        # Persist into discovery_terms if table exists
        try:
            # Batch upsert in chunks of 100
            for i in range(0, len(seeds_list), 100):
                chunk = seeds_list[i:i+100]
                self.sb.table("discovery_terms").upsert(chunk, on_conflict="term").execute()
            logger.info(f"Persisted {len(seeds_list)} discovery terms into database.")
        except Exception as e:
            logger.warning(f"discovery_terms upsert note (table pending migration 009): {e}")

        return seeds_list


def main():
    scraper = KeywordScraper()
    seeds = scraper.seed_terms()
    print("======================================================================")
    print(f"DISCOVERY TERMS SEEDING SUMMARY (Total Generated: {len(seeds)})")
    print("======================================================================")
    print("FIRST 40 SEEDS:")
    for idx, s in enumerate(seeds[:40]):
        print(f"  {idx+1:02d}. [{s['kind']}] '{s['term']}' (region: {s['region']})")


if __name__ == "__main__":
    main()
