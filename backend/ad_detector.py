"""
Ad/Sponsored Detection for Instagram Reels.

Detects sponsored content using:
1. Instagram's is_paid_partnership flag
2. Caption disclosure hashtags (#ad, #sponsored, etc.)
3. Brand partnership patterns in caption text

Returns a dict with detection results for transparency.
"""
import re
from typing import Dict, Optional

# Ad disclosure hashtags (case-insensitive)
AD_HASHTAGS = {
    "#ad", "#sponsored", "#partner", "#paidpartnership",
    "#gifted", "#collab", "#brandambassador", "#ambassador",
    "#advertising", "#promoted", "#paidad", "#spon",
}

# Ad disclosure phrases (case-insensitive, regex patterns)
AD_PHRASES = [
    r"\bpaid\s+partnership\b",
    r"\bsponsored\s+by\b",
    r"\bpartner\s+with\b",
    r"\bcollab\s+with\b",
    r"\bgifted\s+by\b",
    r"\bprovided\s+by\b",
    r"\bad\b(?!\w)",  # standalone #ad without word chars after
    r"\bin\s+collaboration\s+with\b",
    r"\bbrought\s+to\s+you\s+by\b",
]

# High-confidence brand disclosure patterns
BRAND_DISCLOSURE_PATTERNS = [
    r"@\w+\s+(?:partner|sponsors?|ambassador)",
    r"(?:partner|sponsors?|ambassador)\s+@\w+",
]


def detect_sponsored(
    caption: str,
    media_dict: Optional[Dict] = None,
) -> Dict:
    """
    Detect if a reel is sponsored/ad content.

    Returns:
        {
            "is_sponsored": bool,
            "confidence": float (0.0-1.0),
            "signals": list[str],
        }
    """
    signals = []
    confidence = 0.0

    # 1. Check Instagram's paid partnership flag
    if media_dict:
        is_paid = media_dict.get("is_paid_partnership")
        if is_paid:
            signals.append("instagram_paid_partnership_flag")
            confidence = max(confidence, 0.95)

        # Check sponsor_tags if present
        sponsor_tags = media_dict.get("sponsor_tags") or []
        if sponsor_tags:
            signals.append(f"sponsor_tags: {len(sponsor_tags)}")
            confidence = max(confidence, 0.9)

    if not caption:
        return {"is_sponsored": confidence > 0.5, "confidence": confidence, "signals": signals}

    caption_lower = caption.lower()

    # 2. Check ad disclosure hashtags
    caption_words = set(re.findall(r"#\w+", caption_lower))
    found_hashtags = caption_words & AD_HASHTAGS
    if found_hashtags:
        signals.append(f"ad_hashtags: {', '.join(found_hashtags)}")
        confidence = max(confidence, 0.85)

    # 3. Check ad disclosure phrases
    for pattern in AD_PHRASES:
        if re.search(pattern, caption_lower):
            signals.append(f"ad_phrase: {pattern}")
            confidence = max(confidence, 0.7)
            break

    # 4. Check brand disclosure patterns
    for pattern in BRAND_DISCLOSURE_PATTERNS:
        if re.search(pattern, caption_lower):
            signals.append(f"brand_disclosure: {pattern}")
            confidence = max(confidence, 0.8)
            break

    is_sponsored = confidence > 0.5
    return {
        "is_sponsored": is_sponsored,
        "confidence": confidence,
        "signals": signals,
    }
