"""
backend/song_key.py - Order 61/62 Song Identity Normalization

Normalizes audio title and artist into a stable, grouped song_key to join
remixes, slowed/reverb versions, and split audio IDs across Latin and Unicode scripts.
"""

import re
import unicodedata
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
    re.IGNORECASE | re.UNICODE
)

# Skip values
INVALID_TITLES = {"originalaudio", "0", "unknown"}


def fold_latin_diacritics(text: str) -> str:
    """
    Folds Latin diacritics (NFKD, drop combining marks only for Latin letters),
    preserving combining marks on non-Latin scripts.
    """
    text = unicodedata.normalize("NFKC", text)
    decomposed = unicodedata.normalize("NFKD", text)
    result = []
    prev_was_latin = False
    for ch in decomposed:
        cat = unicodedata.category(ch)
        if cat.startswith("M"):
            if prev_was_latin:
                # Drop combining mark attached to Latin base letter
                continue
            else:
                result.append(ch)
        else:
            if ("a" <= ch <= "z") or ("A" <= ch <= "Z"):
                prev_was_latin = True
            else:
                prev_was_latin = False
            result.append(ch)
    return unicodedata.normalize("NFC", "".join(result))


def get_script_min_length(text: str) -> int:
    """
    Determines minimum length threshold based on script:
    - 2 for CJK / Hangul / Kana
    - 3 for Arabic / Devanagari / Cyrillic
    - 5 for Latin / Default
    """
    for ch in text:
        cp = ord(ch)
        # CJK / Hangul / Kana
        if (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or 0xF900 <= cp <= 0xFAFF or
            0xAC00 <= cp <= 0xD7AF or 0x1100 <= cp <= 0x11FF or 0x3130 <= cp <= 0x318F or
            0x3040 <= cp <= 0x309F or 0x30A0 <= cp <= 0x30FF):
            return 2
    for ch in text:
        cp = ord(ch)
        # Arabic / Devanagari / Cyrillic
        if (0x0600 <= cp <= 0x06FF or 0x0750 <= cp <= 0x077F or 0x08A0 <= cp <= 0x08FF or
            0xFB50 <= cp <= 0xFDFF or 0xFE70 <= cp <= 0xFEFF or
            0x0900 <= cp <= 0x097F or 0xA8E0 <= cp <= 0xA8FF or
            0x0400 <= cp <= 0x04FF or 0x0500 <= cp <= 0x052F):
            return 3
    return 5


def normalize_title(title: Optional[str]) -> Optional[str]:
    """
    normalize(title):
    - NFKC normalization
    - lowercase
    - strip text after '|', '(', '[', ' - ', 'feat', 'ft.'
    - remove words slowed, reverb, sped, up, remix, version, lofi, edit, instrumental, extended
    - fold Latin diacritics
    - keep Unicode letters and digits (str.isalnum)
    - min length: 5 for Latin, 2 for CJK/Hangul/Kana, 3 for Arabic/Devanagari/Cyrillic
    - skip 'originalaudio', null, '0', 'unknown'
    """
    if not title:
        return None

    t = unicodedata.normalize("NFKC", str(title)).lower().strip()
    if not t:
        return None

    # Strip text after delimiters
    for delim in ["|", "(", "["]:
        if delim in t:
            t = t.split(delim, 1)[0]

    for delim in [" - ", " feat. ", " feat ", " ft. ", " ft "]:
        if delim in t:
            t = t.split(delim, 1)[0]

    # Remove stripped modifier words
    t = _MODIFIER_PATTERN.sub(" ", t)

    # Fold Latin diacritics
    t = fold_latin_diacritics(t)

    # Keep Unicode letters and digits (str.isalnum)
    t_clean = "".join(c for c in t if c.isalnum())

    # Check validity & script-specific min length
    if not t_clean or t_clean in INVALID_TITLES:
        return None

    min_len = get_script_min_length(t_clean)
    if len(t_clean) < min_len:
        return None

    return t_clean


def normalize_artist(artist: Optional[str]) -> Optional[str]:
    """
    artist: first artist token normalized (strip after comma, &, feat, etc., keep Unicode letters and digits).
    """
    if not artist:
        return None

    a = unicodedata.normalize("NFKC", str(artist)).lower().strip()
    if not a:
        return None

    # Delimiters for multiple artists
    for delim in [",", "&", "|", "/", "\\", "(", "[", " feat ", " ft "]:
        if delim in a:
            a = a.split(delim, 1)[0]

    a = fold_latin_diacritics(a)
    a_clean = "".join(c for c in a if c.isalnum())
    if not a_clean or a_clean in INVALID_TITLES:
        return None

    return a_clean


def compute_song_key(title: Optional[str], artist: Optional[str]) -> Optional[str]:
    """
    song_key = title_norm + '|' + artist_norm; if artist missing, title_norm only.
    Skip 'originalaudio', null, '0', 'unknown', and titles below script min length.
    """
    title_norm = normalize_title(title)
    if not title_norm:
        return None

    artist_norm = normalize_artist(artist)
    if artist_norm:
        return f"{title_norm}|{artist_norm}"
    return title_norm

