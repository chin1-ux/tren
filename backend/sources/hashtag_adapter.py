"""
Hashtag Source Adapter (Logged-In)
Wraps InstagramScraper hashtag search pipeline.
"""

import logging
from typing import Any
from .base import BaseSourceAdapter

logger = logging.getLogger("sources.hashtag")

class HashtagSourceAdapter(BaseSourceAdapter):
    name = "hashtag"

    def __init__(self, scraper_instance=None):
        self.scraper = scraper_instance

    def health(self) -> dict[str, Any]:
        """Checks if active session probe is verified."""
        if not self.scraper:
            try:
                from instagram_scraper_browser import InstagramScraper
                self.scraper = InstagramScraper()
            except Exception as e:
                return {"status": "blocked", "reason": f"scraper_init_failed: {e}"}

        # Check authenticated probe
        try:
            from cookie_sliding_manager import probe_instagram_session_authenticated
            is_valid, reason = probe_instagram_session_authenticated()
            if is_valid:
                return {"status": "ok", "reason": "session_verified"}
            else:
                return {"status": "blocked", "reason": f"session_blocked: {reason}"}
        except Exception as e:
            return {"status": "blocked", "reason": f"probe_exception: {e}"}

    def fetch(self, **kwargs) -> list[dict[str, Any]]:
        """Executes hashtag scrape if healthy."""
        h = self.health()
        if h["status"] == "blocked":
            logger.warning(f"[SOURCE:hashtag] Aborting fetch: status is blocked ({h['reason']})")
            return []

        if not self.scraper:
            from instagram_scraper_browser import InstagramScraper
            self.scraper = InstagramScraper()

        self.scraper._session_probe_verified = True
        new_count = self.scraper.scrape_trending_reels()
        logger.info(f"[SOURCE:hashtag] Scraped {new_count} new reels.")
        return getattr(self.scraper, "_last_scraped_items", []) or []
