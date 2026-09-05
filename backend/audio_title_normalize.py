"""
Audio title normalization for trend grouping.

Strips known variant suffixes (sped up, slowed, remix, etc.) from audio
titles so that "Espresso (Sped Up)" and "Espresso" group as the same trend.
"""
import re

# Ordered by specificity — more specific patterns first to avoid partial matches
VARIANT_SUFFIXES = [
    r"\(slowed\s*\+\s*reverb\)",
    r"\(sped\s*up\s*\+\s*reverb\)",
    r"\(sped\s*up\)",
    r"\(slowed\)",
    r"\(reverb\)",
    r"\(nightcore\)",
    r"\(remix\)",
    r"\(cover\)",
    r"\(live\)",
    r"\(acoustic\)",
    r"\(instrumental\)",
    r"\(extended\)",
    r"\(edit\)",
    r"\(version\)",
    r"\(rmx\)",
]

# Compiled pattern: strips all variant suffixes, collapses whitespace
_VARIANT_RE = re.compile(
    r"\s*(?:"
    + "|".join(VARIANT_SUFFIXES)
    + r")\s*",
    re.IGNORECASE,
)


def normalize_audio_title(title: str) -> str:
    """Strip known variant suffixes from an audio title for grouping purposes.

    Returns a canonical form suitable for trend grouping. Does NOT modify
    the stored audio_title — only used as a grouping key.

    Examples:
        "Espresso (Sped Up)" → "Espresso"
        "Song (Slowed + Reverb)" → "Song"
        "Track (Nightcore) (Remix)" → "Track"
    """
    if not title:
        return ""
    normalized = _VARIANT_RE.sub(" ", title)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized
