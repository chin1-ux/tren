"""
backend/song_key.py - Order 61 Song Identity Normalization

Normalizes audio title and artist into a stable, grouped song_key to join
remixes, slowed/reverb versions, and split audio IDs.
"""

import re
from typing import Optional, Tuple

# Word boundaries for modifiers to remove
STRIP_MODIFIERS = [
    "slowed",
    "reverb",
    "sped",
    "up",
    "remix",
    "version",
    "lofi",
    "edit",
    "instrumental",
    "extended",
]

_MODIFIER_PATTERN = re.compile(
    r"\b(" + "|".join(STRIP_MODIFIERS) + r")\b",
    re.IGNORECASE
)

# Skip values
INVALID_TITLES = {"originalaudio", "0", "unknown"}


def normalize_title(title: Optional[str]) -> Optional[str]:
    """
    normalize(title):
    - lowercase
    - strip text after '|', '(', '[', ' - ', 'feat', 'ft.'
    - remove words slowed, reverb, sped, up, remix, version, lofi, edit, instrumental, extended
    - strip non-letters/digits
    - skip 'originalaudio', null, '0', 'unknown', and titles <5 chars
    """
    if not title:
        return None

    t = title.lower().strip()
    if not t:
        return None

    # Strip text after delimiters
    # Order matters: check ' - ', 'feat.', 'feat', 'ft.', 'ft', '|', '(', '['
    # First handle text delimiters
    for delim in ["|", "(", "["]:
        if delim in t:
            t = t.split(delim, 1)[0]

    for delim in [" - ", " feat. ", " feat ", " ft. ", " ft "]:
        if delim in t:
            t = t.split(delim, 1)[0]

    # Remove stripped modifier words
    t = _MODIFIER_PATTERN.sub(" ", t)

    # Strip non-letters/digits (retain only a-z and 0-9)
    t_clean = re.sub(r"[^a-z0-9]", "", t)

    # Check validity
    if not t_clean or len(t_clean) < 5 or t_clean in INVALID_TITLES:
        return None

    return t_clean


def normalize_artist(artist: Optional[str]) -> Optional[str]:
    """
    artist: first artist token normalized (strip after comma, &, feat, etc., keep a-z0-9).
    """
    if not artist:
        return None

    a = artist.lower().strip()
    if not a:
        return None

    # Delimiters for multiple artists
    for delim in [",", "&", "|", "/", "\\", "(", "[", " feat ", " ft "]:
        if delim in a:
            a = a.split(delim, 1)[0]

    a_clean = re.sub(r"[^a-z0-9]", "", a)
    if not a_clean or a_clean in INVALID_TITLES:
        return None

    return a_clean


def compute_song_key(title: Optional[str], artist: Optional[str]) -> Optional[str]:
    """
    song_key = title_norm + '|' + artist_norm; if artist missing, title_norm only.
    Skip 'originalaudio', null, '0', 'unknown', and titles <5 chars.
    """
    title_norm = normalize_title(title)
    if not title_norm:
        return None

    artist_norm = normalize_artist(artist)
    if artist_norm:
        return f"{title_norm}|{artist_norm}"
    return title_norm
