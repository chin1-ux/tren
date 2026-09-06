import os
import sys
import logging

logger = logging.getLogger(__name__)

_TRANSITION_HASHTAGS = {
    "transitionreels", "transition", "transitions", "outfits", "outfitinspo",
    "grwm", "fashiontransition", "glowup", "reveal", "outfitswap", "mvmus"
}

def verify_transition_trend(reels: list[dict], audio_title: str = "") -> dict:
    """
    Verifies if an audio is driving a visual transition trend.
    Returns dict with is_transition_trend, transition_type, and confidence.
    """
    all_hashtags = set()
    all_captions = []

    for r in reels:
        tags = r.get("hashtags") or []
        all_hashtags.update(t.lower() for t in tags)
        cap = (r.get("caption") or "").lower()
        if cap:
            all_captions.append(cap)

    # Check hashtag overlap
    matched_tags = all_hashtags.intersection(_TRANSITION_HASHTAGS)
    caption_text = " ".join(all_captions)
    matched_caption_words = [w for w in _TRANSITION_HASHTAGS if w in caption_text]

    has_transition_signal = bool(matched_tags or matched_caption_words or "transition" in audio_title.lower())

    # Determine transition type
    transition_type = None
    if "outfit" in caption_text or "outfit" in " ".join(matched_tags) or "grwm" in caption_text:
        transition_type = "Outfit Swap / Reveal"
    elif "glowup" in caption_text or "before" in caption_text:
        transition_type = "Before & After Transformation"
    elif has_transition_signal:
        transition_type = "Visual Sync Transition"

    confidence = 0.85 if (len(matched_tags) >= 2 or len(reels) >= 3) else (0.65 if has_transition_signal else 0.0)

    return {
        "is_transition_trend": has_transition_signal and confidence >= 0.6,
        "transition_type": transition_type,
        "transition_confidence": confidence,
        "matched_signals": list(matched_tags.union(matched_caption_words))
    }
