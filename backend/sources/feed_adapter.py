"""
Algorithmic Feed Source Adapter (Logged-Out)
Streams live reels from /reels/ unauthenticated to catch viral sounds.
"""

import logging
import asyncio
from typing import Any
from .base import BaseSourceAdapter

logger = logging.getLogger("sources.feed")

class FeedSourceAdapter(BaseSourceAdapter):
    name = "feed"

    def health(self) -> dict[str, Any]:
        """Feed adapter is unauthenticated; always ok unless blocked by network."""
        return {"status": "ok", "reason": "unauthenticated_stream"}

    def fetch(self, scroll_count: int = 6, **kwargs) -> list[dict[str, Any]]:
        """Harvests reels from /reels/ stream."""
        try:
            from feed_harvester import harvest_algorithmic_feed, save_harvested_reels
            from utils.db import get_supabase_client

            async def _run_guarded():
                return await asyncio.wait_for(harvest_algorithmic_feed(scroll_count=scroll_count), timeout=35.0)

            feed_reels = asyncio.run(_run_guarded())
            sb = get_supabase_client()
            stats = save_harvested_reels(sb, feed_reels, live=True)
            logger.info(f"[SOURCE:feed] Harvested {len(feed_reels)} reels, saved {stats.get('saved', 0)} new.")
            return feed_reels
        except Exception as e:
            logger.error(f"[SOURCE:feed] Harvesting failed: {e}")
            return []
