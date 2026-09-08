import os
import sys
import logging
import asyncio
import io
from typing import Dict, Any, Optional

logger = logging.getLogger("shazam_recognizer")

try:
    from shazamio import Shazam
    _SHAZAM_AVAILABLE = True
except ImportError:
    _SHAZAM_AVAILABLE = False
    logger.warning("shazamio module not installed. Run: pip install shazamio")


class ShazamAudioRecognizer:
    """
    Shazam Audio Fingerprinting Engine (Single Call per Audio Cluster).
    Recognizes commercial tracks from raw audio bytes or URLs to resolve
    'Original audio' uploads to canonical track titles & artist metadata.
    """

    def __init__(self):
        self.shazam = Shazam() if _SHAZAM_AVAILABLE else None

    async def recognize_audio_bytes_async(self, audio_bytes: bytes) -> Optional[Dict[str, Any]]:
        """
        Recognize canonical track info from raw audio bytes in-memory.
        """
        if not _SHAZAM_AVAILABLE or not self.shazam:
            logger.warning("Shazam recognition skipped: shazamio library not available.")
            return None

        if not audio_bytes or len(audio_bytes) < 100:
            logger.warning("Shazam recognition skipped: audio payload empty or too small.")
            return None

        try:
            # ShazamIO recognize_song accepts bytes or file path
            out = await self.shazam.recognize(audio_bytes)
            return self._parse_shazam_output(out)
        except Exception as e:
            logger.error(f"ShazamIO recognition error: {e}", exc_info=True)
            return None

    def recognize_audio_bytes(self, audio_bytes: bytes) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for recognize_audio_bytes_async."""
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # If called from an active event loop, run in thread pool to prevent blocking/nesting conflict
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(lambda: asyncio.run(self.recognize_audio_bytes_async(audio_bytes)))
                    return future.result()
            else:
                return asyncio.run(self.recognize_audio_bytes_async(audio_bytes))
        except Exception as e:
            logger.error(f"Sync Shazam recognition error: {e}")
            return None

    async def recognize_audio_url_async(self, url: str, timeout_seconds: float = 10.0) -> Optional[Dict[str, Any]]:
        """
        Download up to 3 seconds (~150 KB) of audio from a public audio/video URL in-memory
        and recognize canonical track metadata via ShazamIO.
        """
        if not _SHAZAM_AVAILABLE or not self.shazam:
            logger.warning("Shazam recognition skipped: shazamio library not available.")
            return None

        if not url or not url.startswith("http"):
            return None

        try:
            import requests
            logger.info(f"Fetching audio snippet from URL for Shazam recognition: {url[:80]}...")
            
            # Request range bytes for lightweight 3-second sample (max 300 KB)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Range": "bytes=0-307200"  # First ~300 KB
            }
            resp = requests.get(url, headers=headers, timeout=timeout_seconds, stream=True)
            if not resp.ok and resp.status_code != 206:
                logger.warning(f"Failed to fetch audio stream for Shazam (HTTP {resp.status_code})")
                return None

            audio_data = resp.content
            if not audio_data:
                return None

            return await self.recognize_audio_bytes_async(audio_data)

        except Exception as e:
            logger.error(f"Error in recognize_audio_url_async: {e}")
            return None

    def _parse_shazam_output(self, out: dict) -> Optional[Dict[str, Any]]:
        """
        Parse ShazamIO output JSON dictionary into standardized metadata.
        """
        if not out or not isinstance(out, dict):
            return None

        track = out.get("track")
        if not track:
            return {
                "status": "no_match",
                "canonical_title": None,
                "canonical_artist": None,
                "canonical_album": None,
                "canonical_genre": None,
                "shazam_id": None,
                "is_original_audio_resolved": False,
                "confidence": 0.0
            }

        title = track.get("title")
        subtitle = track.get("subtitle")  # Artist name
        shazam_id = track.get("key")
        
        # Extract genre & album from sections metadata
        genre = None
        album = None
        sections = track.get("sections") or []
        for sec in sections:
            if sec.get("type") == "SONG":
                metadata = sec.get("metadata") or []
                for meta in metadata:
                    title_key = (meta.get("title") or "").lower()
                    if title_key == "album":
                        album = meta.get("text")
                    elif title_key == "genre":
                        genre = meta.get("text")

        genres_meta = track.get("genres", {})
        if not genre and genres_meta.get("primary"):
            genre = genres_meta.get("primary")

        logger.info(f"Shazam MATCH SUCCESS: '{title}' by '{subtitle}' (Genre: {genre}, Shazam ID: {shazam_id})")

        return {
            "status": "matched",
            "canonical_title": title,
            "canonical_artist": subtitle,
            "canonical_album": album,
            "canonical_genre": genre,
            "shazam_id": shazam_id,
            "is_original_audio_resolved": True,
            "confidence": 0.95,
            "raw_track": track
        }


# Quick CLI test wrapper
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("ShazamAudioRecognizer module initialized. Available:", _SHAZAM_AVAILABLE)
