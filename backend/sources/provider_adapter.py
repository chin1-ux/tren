"""
Managed Provider Source Adapter (Order 95 Phase 4 - Default OFF)
Uses external managed Instagram scraper actor (e.g. Apify) when FALLBACK_PROVIDER_TOKEN is configured.
"""

import os
import logging
from typing import Any
from .base import BaseSourceAdapter

logger = logging.getLogger("sources.provider")

class ProviderSourceAdapter(BaseSourceAdapter):
    name = "provider"

    def __init__(self):
        self.token = os.getenv("FALLBACK_PROVIDER_TOKEN", "").strip()
        self.max_results = int(os.getenv("MAX_FALLBACK_RESULTS_PER_RUN", "50"))
        self.actor_id = os.getenv("FALLBACK_PROVIDER_ACTOR_ID", "apify/instagram-reel-scraper")

    def health(self) -> dict[str, Any]:
        """Provider is only active when token is set."""
        if not self.token:
            return {
                "status": "blocked",
                "reason": "FALLBACK_PROVIDER_TOKEN not configured (default OFF)"
            }
        return {
            "status": "ok",
            "reason": f"provider_ready (cap={self.max_results})"
        }

    def fetch(self, hashtags: list[str] = None, **kwargs) -> list[dict[str, Any]]:
        """Fetches reels via external provider API if enabled."""
        h = self.health()
        if h["status"] == "blocked":
            logger.debug(f"[SOURCE:provider] Skipped: {h['reason']}")
            return []

        logger.info(f"[SOURCE:provider] Invoking managed provider actor '{self.actor_id}' with cap {self.max_results}...")
        # External API invocation code goes here when token is provided
        return []
