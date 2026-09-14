import re

REMIX_KEYWORDS = {
    "sped up", "speed up", "remix", "slowed", "mashup",
    "live", "cover", "edit", "nightcore"
}

MIN_NORMALIZED_TITLE_LEN = 3

def _normalize_audio_title_and_artist(title: str, artist: str) -> tuple[str, str]:
    """
    Returns (clean_title, clean_primary_artist) normalized for exact string comparison.
    Enforces MIN_NORMALIZED_TITLE_LEN guard to prevent single/double char stripped Unicode collisions.
    """
    t_clean = (title or "").lower()
    t_clean = re.sub(r'[^a-z0-9\s]', '', t_clean)
    t_norm = " ".join(t_clean.split())
    if len(t_norm) < MIN_NORMALIZED_TITLE_LEN:
        t_norm = ""

    a_clean = (artist or "").lower()
    a_clean = re.sub(r'[^a-z0-9\s]', '', a_clean)
    primary_artist = a_clean.split("feat")[0].split("and")[0].strip()
    a_norm = " ".join(primary_artist.split())

    return t_norm, a_norm

def _extract_remix_indicators(title: str) -> set[str]:
    """
    Extracts remix/variant keywords present in title.
    """
    t_lower = (title or "").lower()
    return {kw for kw in REMIX_KEYWORDS if kw in t_lower}
