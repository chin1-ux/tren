import os
import json
import logging
from llm import call_llm

logger = logging.getLogger("news_impact_classifier")

# Low-impact noise filter keywords (vegetable prices, local traffic, minor accidents)
NOISE_KEYWORDS = [
    "price hike", "vegetable price", "onion price", "tomato price",
    "minor accident", "traffic delay", "water supply", "power outage",
    "municipal notice", "pothole", "bus fare", "autorickshaw"
]

def is_local_noise(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in NOISE_KEYWORDS)

def classify_news_impact(title: str, summary: str, user_niche: str = "all") -> dict:
    """
    Classifies a news story for high-feed Instagram Reels impact.
    Returns impact score, pass/fail status, category, urgency, and niche adaptation brief.
    """
    full_text = f"{title} {summary}"
    if is_local_noise(full_text):
        return {
            "should_surface": False,
            "impact_score": 10,
            "reason": "Local noise / non-viral news item",
            "category": "local",
            "urgency_window": "none",
            "niche_angle": None
        }

    system_prompt = (
        "You are an expert Instagram algorithm and pop culture strategist. "
        "Your task is to evaluate news stories for their feed-dominating viral potential on Instagram Reels."
    )

    user_prompt = f"""Evaluate this news story for Instagram Reels viral feed impact:
Title: {title}
Summary: {summary}
Target Creator Niche: {user_niche}

Rules:
1. Is this a major cultural, sports, entertainment, or global viral event that will dominate Instagram feeds (like FIFA, IPL, Michael Jackson release, blockbuster launch)?
2. Or is it minor local noise (price hikes, minor accident, routine notice) that should be discarded?
3. Generate a 1-sentence action angle for a {user_niche} creator.

Respond ONLY in valid JSON matching this schema:
{{
  "should_surface": true,
  "impact_score": 88,
  "category": "sports | entertainment | pop_culture | world_event",
  "urgency_window": "4h | 12h | 24h",
  "recommended_angle": "greenscreen reaction / commentary / breakdown",
  "niche_adaptation_brief": "Actionable reel script angle for this niche"
}}
"""

    try:
        res = call_llm(system_prompt=system_prompt, user_prompt=user_prompt, response_mime_type="application/json")
        return {
            "should_surface": res.get("should_surface", True),
            "impact_score": res.get("impact_score", 70),
            "category": res.get("category", "pop_culture"),
            "urgency_window": res.get("urgency_window", "12h"),
            "recommended_angle": res.get("recommended_angle", "greenscreen commentary"),
            "niche_adaptation_brief": res.get("niche_adaptation_brief", "Share your commentary or reaction on this breaking topic.")
        }
    except Exception as e:
        logger.error(f"Error in news impact classification: {e}")
        return {
            "should_surface": not is_local_noise(full_text),
            "impact_score": 65,
            "category": "entertainment",
            "urgency_window": "12h",
            "recommended_angle": "reaction video",
            "niche_adaptation_brief": f"Create a timely commentary reel about {title}."
        }
