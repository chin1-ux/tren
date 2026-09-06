import os
import sys
import re
import logging
import asyncio

logger = logging.getLogger(__name__)

# Fallback pattern dictionary for known viral transition audios
_KNOWN_TRANSITION_ALIASES = {
    "nikkiseey": "Rompe - Daddy Yankee",
    "rompe": "Rompe - Daddy Yankee",
    "daddy yankee": "Rompe - Daddy Yankee",
    "transitionreels": "Transition Beat Drop",
}

def resolve_song_alias_from_reels(audio_title: str, reels: list[dict]) -> str | None:
    """
    Extracts commercial song alias from captions, hashtags, or title.
    Returns e.g. "Rompe - Daddy Yankee" or None.
    """
    title_lower = (audio_title or "").lower()
    
    # 1. Check title keywords
    for key, alias in _KNOWN_TRANSITION_ALIASES.items():
        if key in title_lower:
            return alias

    # 2. Check captions and hashtags across reels
    all_text = []
    for r in reels:
        cap = r.get("caption") or ""
        tags = " ".join(r.get("hashtags") or [])
        all_text.append(f"{cap} {tags}".lower())
    
    combined_text = " ".join(all_text)

    if "rompe" in combined_text or "daddy yankee" in combined_text:
        return "Rompe - Daddy Yankee"
    if "mi gente" in combined_text or "j balvin" in combined_text:
        return "Mi Gente - J Balvin"
    if "gasolina" in combined_text:
        return "Gasolina - Daddy Yankee"

    # Pattern search: check for 'song: <name>' or 'track: <name>' in captions
    match = re.search(r'(?:song|music|track|audio|by)\s*[:\-]\s*([a-zA-Z0-9\s]{3,30})', combined_text)
    if match:
        extracted = match.group(1).strip().title()
        if len(extracted) >= 3 and extracted.lower() not in {"original audio", "reels", "trending"}:
            return extracted

    return None


async def shazam_recognize_audio_url(audio_url: str) -> dict | None:
    """
    Recognizes underlying commercial song for free ($0 cost) using shazamio.
    """
    if not audio_url:
        return None
    try:
        from shazamio import Shazam
        shazam = Shazam()
        out = await shazam.recognize(audio_url)
        track = out.get("track")
        if track:
            title = track.get("title")
            subtitle = track.get("subtitle")
            return {
                "title": title,
                "artist": subtitle,
                "alias": f"{title} - {subtitle}" if (title and subtitle) else title
            }
    except Exception as e:
        logger.warning(f"shazamio recognition skipped/failed: {e}")
    return None
