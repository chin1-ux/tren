"""
Format Detector — Metadata-level trend format analysis.

Distinguishes between:
  - "audio is trending" (many people use the same song)
  - "format trend ON that audio" (many people replicate the same STRUCTURE)

Uses cheap signals first (captions, hashtags, creator diversity) before any
video analysis. No GPU, no paid APIs, instant execution.
"""

import re
import logging
from collections import Counter, defaultdict
from typing import Optional

logger = logging.getLogger(__name__)

# ── Concept keyword patterns (what creators are DOING with the audio) ────────

FORMAT_CONCEPTS = {
    "outfit_transition": [
        r"outfit\s*(change|transition|reveal|swap|edit)",
        r"before\s*(and|&)?\s*after",
        r"glow\s*up",
        r"transition\s*challenge",
        r"fit\s*check",
        r"ootd",
        r"look\s*(reveal|change|book)",
    ],
    "dance_challenge": [
        r"dance\s*(challenge|trend|routine|move)",
        r"choreography",
        r"step\s*(by\s*step|tutorial)",
        r"learn\s*(this|the)\s*dance",
        r"dance\s*with\s*me",
    ],
    "beat_sync": [
        r"beat\s*(drop|sync|hit)",
        r"on\s*the\s*beat",
        r"beat\s*morph",
        r"sound\s*on",
        r"listen",
    ],
    "storytelling": [
        r"story\s*t(ime|elling)",
        r"wait\s*for\s*(it|the\s*end)",
        r"part\s*\d+",
        r"pov[:\s]",
        r"when\s*you",
        r"nobody:\s*",
        r"me\s*when",
    ],
    "tutorial_howto": [
        r"how\s*to",
        r"tutorial",
        r"tip\s*\d*",
        r"hack",
        r"trick",
        r"step\s*\d+",
        r"learn",
    ],
    "before_after_reveal": [
        r"before\s*(and|&)?\s*after",
        r"reveal",
        r"transformation",
        r"glow\s*up",
        r"makeover",
        r"results?\s*(check|look|see)",
    ],
    "relatable_meme": [
        r"relatable",
        r"when\s*you",
        r"me\s*when",
        r"nobody:\s*",
        r"every\s*.*\s*be\s*like",
        r"tag\s*(someone|a\s*friend)",
        r"send\s*this\s*to",
    ],
    "emotional": [
        r"cry",
        r"emotional",
        r"heart\s*touch",
        r"missing\s*you",
        r"love",
    ],
    "comedy_skit": [
        r"comedy",
        r"funny",
        r"skit",
        r"joke",
        r"laugh",
        r"humor",
        r"parody",
    ],
    "product_reveal": [
        r"new\s*(arrival|drop|collection|launch)",
        r"unboxing",
        r"review",
        r"must\s*have",
        r"obsessed",
        r"game\s*changer",
    ],
}


def extract_concept_keywords(caption: str) -> list[str]:
    """Extract concept keywords from a reel's caption.
    
    Returns a list of matched format concepts (e.g. ['outfit_transition', 'beat_sync']).
    """
    if not caption:
        return []
    
    caption_lower = caption.lower()
    matched = []
    
    for concept, patterns in FORMAT_CONCEPTS.items():
        for pattern in patterns:
            if re.search(pattern, caption_lower):
                matched.append(concept)
                break  # one match per concept is enough
    
    return matched


def extract_hashtag_concepts(hashtags: list[str]) -> list[str]:
    """Extract format concepts from hashtags.
    
    E.g. #outfittransition -> outfit_transition, #dancechallenge -> dance_challenge
    """
    if not hashtags:
        return []
    
    concepts = []
    for tag in hashtags:
        tag_lower = tag.lower().replace("#", "")
        for concept, patterns in FORMAT_CONCEPTS.items():
            for pattern in patterns:
                clean_pattern = pattern.replace(r"\s*", "").replace(r"\s+", "")
                if re.search(clean_pattern.replace("(", "").replace(")", "").replace("|", "|"), tag_lower):
                    concepts.append(concept)
                    break
    
    return concepts


def detect_dominant_format(reels: list[dict]) -> dict:
    """Analyze a group of reels (same audio) to detect the dominant format.
    
    Args:
        reels: List of reel dicts with keys: caption, hashtags, owner_username,
               view_count, like_count, velocity_score
    
    Returns:
        dict with:
            - dominant_format: str (e.g. "outfit_transition")
            - format_concepts: list[str] (all detected concepts)
            - format_replication_rate: float (0.0-1.0)
            - concept_counts: dict (concept -> count of reels using it)
            - unique_creators: int
            - total_reels: int
            - creator_diversity: float (unique/total, 0.0-1.0)
            - top_creators: list[str] (top 5 by velocity)
    """
    if not reels:
        return {
            "dominant_format": "unknown",
            "format_concepts": [],
            "format_replication_rate": 0.0,
            "concept_counts": {},
            "unique_creators": 0,
            "total_reels": 0,
            "creator_diversity": 0.0,
            "top_creators": [],
        }
    
    # Extract concepts from each reel
    reel_concepts = []
    all_concepts = []
    creator_velocity = defaultdict(float)
    
    for reel in reels:
        caption = reel.get("caption") or ""
        hashtags = reel.get("hashtags") or []
        if isinstance(hashtags, str):
            try:
                import json
                hashtags = json.loads(hashtags)
            except:
                hashtags = []
        
        owner = reel.get("owner_username") or "unknown"
        velocity = reel.get("velocity_score") or 0
        
        concepts = extract_concept_keywords(caption)
        hashtag_concepts = extract_hashtag_concepts(hashtags)
        all_reel_concepts = list(set(concepts + hashtag_concepts))
        
        reel_concepts.append(all_reel_concepts)
        all_concepts.extend(all_reel_concepts)
        creator_velocity[owner] = max(creator_velocity[owner], velocity)
    
    # Count concepts
    concept_counts = Counter(all_concepts)
    
    # Find dominant format
    unique_creators = len(set(r.get("owner_username") for r in reels if r.get("owner_username")))
    total_reels = len(reels)
    
    if concept_counts:
        dominant_format, dominant_count = concept_counts.most_common(1)[0]
        # Format replication rate: what % of reels share the dominant concept
        format_replication_rate = dominant_count / total_reels if total_reels > 0 else 0.0
    else:
        dominant_format = "unknown"
        format_replication_rate = 0.0
    
    # Creator diversity
    creator_diversity = unique_creators / total_reels if total_reels > 0 else 0.0
    
    # Top creators by velocity
    sorted_creators = sorted(creator_velocity.items(), key=lambda x: x[1], reverse=True)
    top_creators = [c[0] for c in sorted_creators[:5]]
    
    # All detected concepts (deduplicated)
    all_detected = list(concept_counts.keys())
    
    return {
        "dominant_format": dominant_format,
        "format_concepts": all_detected,
        "format_replication_rate": round(format_replication_rate, 3),
        "concept_counts": dict(concept_counts),
        "unique_creators": unique_creators,
        "total_reels": total_reels,
        "creator_diversity": round(creator_diversity, 3),
        "top_creators": top_creators,
    }


def is_format_trend(analysis: dict, min_replication_rate: float = 0.3,
                    min_unique_creators: int = 3) -> bool:
    """Determine if an audio group has a FORMAT TREND (not just audio popularity).
    
    A format trend exists when:
    1. Multiple independent creators use the same format (not just same audio)
    2. The format replication rate is above threshold
    3. There are enough unique creators (not just one person posting variants)
    """
    if analysis["dominant_format"] == "unknown":
        return False
    
    return (
        analysis["format_replication_rate"] >= min_replication_rate
        and analysis["unique_creators"] >= min_unique_creators
    )


def get_format_trend_score(analysis: dict) -> float:
    """Calculate a 0-100 score for how strong the format trend is.
    
    Factors:
    - Format replication rate (40% weight)
    - Creator diversity (30% weight)
    - Unique concept count (30% weight — more concepts = richer format)
    """
    replication = analysis["format_replication_rate"]
    diversity = analysis["creator_diversity"]
    concept_richness = min(1.0, len(analysis["format_concepts"]) / 5.0)
    
    score = (replication * 40) + (diversity * 30) + (concept_richness * 30)
    return round(score, 1)
