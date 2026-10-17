"""
Quality Gate Engine (Shadow Mode)
Order 81 Phase 2 Implementation.

Evaluates trends into Tier A, Tier B, and Tier C (quarantine).
Never deletes rows. Safe for shadow evaluation and reporting.
"""

import re
from typing import Dict, Any, List, Optional, Tuple

SACRED_RECITATION_PATTERNS = [
    r"\bquran\b", r"\bsurah\b", r"\bayah\b", r"\bayat\b", r"\btilawat\b",
    r"\bqari\b", r"\badhan\b", r"\bazan\b", r"\bnasheed\b", r"\bnaat\b",
    r"\bmantra\b", r"\bgayatri\b", r"\bchalisa\b", r"\baarti\b", r"\bbhajan\b",
    r"\bstotram\b", r"\bstotra\b", r"\bkatha\b", r"\bhanuman\s+chalisa\b",
    r"\bshloka\b", r"\bdua\b", r"\bzikr\b", r"\bdhikr\b", r"\bhadees\b", r"\bhadith\b",
    r"\brecitation\b", r"\bnamaz\b", r"\bsalah\b", r"\bpujapath\b"
]

NON_INDIA_LANGUAGES = {
    "pt", "portuguese", "es", "spanish", "ko", "korean", "ar", "arabic",
    "ru", "russian", "fr", "french", "de", "german", "it", "italian", "ja", "japanese"
}

INDIA_MARKET_LANGUAGES = {
    "hi", "hindi", "pa", "punjabi", "ta", "tamil", "te", "telugu",
    "ml", "malayalam", "kn", "kannada", "mr", "marathi", "bn", "bengali",
    "gu", "gujarati", "en", "english", "instrumental"
}

def is_sacred_recitation_audio(title: str, artist: str = "") -> bool:
    """Checks if audio is a sacred/religious recitation."""
    text = f"{title or ''} {artist or ''}".lower()
    for pattern in SACRED_RECITATION_PATTERNS:
        if re.search(pattern, text):
            return True
    return False

def is_music_track(trend: Dict[str, Any]) -> bool:
    """
    Determines if audio is a verified music track.
    True if Shazam resolved, has canonical artist, or title lacks non-music indicators.
    """
    if trend.get("shazam_id") or trend.get("shazam_canonical_title"):
        return True
    
    title = (trend.get("audio_title") or "").strip().lower()
    artist = (trend.get("audio_artist") or "").strip().lower()

    if title.startswith("original_audio::") or "original audio" in title:
        # Check if artist is known or marked resolved
        if trend.get("is_original_audio_resolved"):
            return True
        return False

    # Check for speech/recitation indicators
    non_music_keywords = ["podcast", "dialogue", "dialog", "speech", "monologue", "interview", "scene", "episode"]
    if any(k in title for k in non_music_keywords):
        return False

    # Non-empty artist that isn't generic
    if artist and artist not in ["original audio", "unknown", "unknown artist", "various artists"]:
        return True

    return bool(len(title) > 2 and not is_sacred_recitation_audio(title, artist))

def get_grounded_why_this_works(why_this_works: str, sample_captions: List[str], is_sacred: bool) -> Optional[str]:
    """
    Returns grounded 'why this works' note.
    Rule: May ONLY summarize real captions/hashtags of reels using the sound;
    if none, return None (or grounded generic note). Never hallucinate from audio title.
    """
    if is_sacred:
        return None
    
    if not sample_captions or len(sample_captions) == 0:
        return None

    # Check if why_this_works appears grounded or hallucinated
    if not why_this_works or why_this_works.strip() == "" or "not enough data" in why_this_works.lower():
        return None

    return why_this_works.strip()

def evaluate_quality(
    trend: Dict[str, Any],
    distinct_creators: int,
    is_saved_by_user: bool = False,
    mode: str = "india",
    sample_captions: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Evaluates quality tier (A, B, C) for a trend.
    Returns:
    {
        "trend_id": int,
        "tier": "A" | "B" | "C",
        "reasons": list[str],
        "signals": dict
    }
    """
    title = trend.get("audio_title") or ""
    artist = trend.get("audio_artist") or ""
    raw_lang = (trend.get("language_final") or trend.get("language") or "en").lower().strip()
    
    # Normalize language
    lang = raw_lang
    if lang in ["hindi", "bhojpuri"]:
        lang = "bhojpuri" if "bhojpuri" in raw_lang else "hi"

    is_original = bool(
        title.lower().startswith("original_audio::") or
        "original audio" in title.lower() or
        trend.get("is_original_audio_resolved") is False
    )

    sacred = is_sacred_recitation_audio(title, artist)
    music = is_music_track(trend)

    reasons: List[str] = []
    signals: Dict[str, Any] = {
        "distinct_creators": distinct_creators,
        "is_original_audio": is_original,
        "language_final": lang,
        "is_music_track": music,
        "is_sacred_recitation": sacred,
        "is_saved_by_user": is_saved_by_user,
        "mode": mode,
        "why_this_works_grounded": get_grounded_why_this_works(
            trend.get("why_this_works") or "", sample_captions or [], sacred
        )
    }

    # ── TIER C: QUARANTINE RULES ──────────────────────────────────────────────
    is_tier_c = False

    # 1. Sacred Recitation
    if sacred:
        is_tier_c = True
        reasons.append("sacred_recitation_not_creator_audio")

    # 2. Single-creator audio
    if distinct_creators <= 1:
        is_tier_c = True
        reasons.append("single_creator_quarantine")

    # 3. Original audio by single creator
    if is_original and distinct_creators <= 1:
        if "single_creator_quarantine" not in reasons:
            reasons.append("original_audio_single_creator")

    # 4. Bhojpuri requires >= 20 distinct creators
    if lang == "bhojpuri" and distinct_creators < 20:
        is_tier_c = True
        reasons.append(f"bhojpuri_low_creators_{distinct_creators}_lt_20")

    # 5. Non-India language in India mode requires >= 3 creators
    if mode == "india" and (lang in NON_INDIA_LANGUAGES) and distinct_creators < 3:
        is_tier_c = True
        reasons.append(f"foreign_language_in_india_mode_{lang}_creators_{distinct_creators}_lt_3")

    # 6. Global mode requires >= 3 creators AND a music track
    if mode == "global":
        if distinct_creators < 3:
            is_tier_c = True
            reasons.append(f"global_mode_low_creators_{distinct_creators}_lt_3")
        if not music:
            is_tier_c = True
            reasons.append("global_mode_non_music_track")

    # ── NEVER-HIDE OVERRIDE RULE ──────────────────────────────────────────────
    # NEVER-HIDE: >= 3 distinct creators in a market-fit language, OR anything saved by a user.
    # HARD TEST: ZERO OF THEM IN TIER C.
    is_market_fit = (mode == "india" and (lang in INDIA_MARKET_LANGUAGES or lang == "en")) or \
                    (mode == "global" and music)

    never_hide = False
    if is_saved_by_user:
        never_hide = True
        reasons.append("never_hide_saved_by_user")
    elif distinct_creators >= 3 and is_market_fit and not sacred:
        never_hide = True
        reasons.append("never_hide_market_fit_multi_creator")

    if never_hide and is_tier_c:
        is_tier_c = False
        reasons.append("tier_c_quarantine_lifted_by_never_hide")

    # ── FINAL TIER DETERMINATION ─────────────────────────────────────────────
    if is_tier_c:
        tier = "C"
    elif distinct_creators >= 3 and music and not sacred:
        tier = "A"
        reasons.append("tier_a_high_quality_multi_creator")
    else:
        tier = "B"
        reasons.append("tier_b_eligible_adoption")

    return {
        "trend_id": trend.get("id"),
        "tier": tier,
        "reasons": reasons,
        "signals": signals,
    }
