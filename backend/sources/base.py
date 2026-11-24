"""
Source Adapter Base Interface
Defines the contract for all Trendrop ingestion sources.
"""

from abc import ABC, abstractmethod
from typing import Any

class BaseSourceAdapter(ABC):
    name: str

    @abstractmethod
    def health(self) -> dict[str, Any]:
        """
        Returns health status dictionary:
        {
            "status": "ok" | "degraded" | "blocked",
            "reason": str
        }
        """
        pass

    @abstractmethod
    def fetch(self, **kwargs) -> list[dict[str, Any]]:
        """
        Fetches reels from this source.
        Returns a list of standardized reel dictionaries:
        {
            "reel_id": str,
            "shortcode": str,
            "video_url": str,
            "source": str,  # "hashtag" | "feed" | "watchlist" | "provider"
            "source_tag": str,
            "audio_title": str,
            "audio_artist": str,
            ...
        }
        """
        pass
