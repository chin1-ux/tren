"""
Niche Relevance Engine
======================
Transforms raw trend objects (audio trends + format/challenge trends) into
niche-specific opportunity feeds for different creator types.

For each trend it produces:
  - relevance_score (0.0–1.0) per creator niche
  - adaptation_brief (1-sentence content idea)
  - hook_idea (concrete first-line hook)
  - urgency_label ("Post NOW", "Post within 4h", "Still time", "Window closing")

Supported niches:
  fitness, food, travel, fashion, sports, comedy, beauty, tech,
  motivation, parenting, dance, music, general

This module is PURE LOGIC — no database calls. It can be used as a library
by routes, cron jobs, and the keyword monitor.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional


# ─── Niche Definitions ────────────────────────────────────────────────────────

@dataclass
class NicheProfile:
    """
    Defines how a creator niche maps to trends.
    - keywords: signals that directly match this niche
    - anti_keywords: signals that strongly suggest the trend is NOT for this niche
    - adapt_patterns: map of trend type/name patterns → content adaptation idea
    - base_relevance: floor relevance for any trend (some niches can adapt anything)
    """
    name: str
    display_name: str
    emoji: str
    keywords: list[str]
    anti_keywords: list[str] = field(default_factory=list)
    adapt_patterns: dict[str, str] = field(default_factory=dict)
    base_relevance: float = 0.1


NICHES: dict[str, NicheProfile] = {
    "fitness": NicheProfile(
        name="fitness",
        display_name="Fitness & Gym",
        emoji="🏋️",
        keywords=[
            "gym", "workout", "fitness", "exercise", "protein", "gains", "cardio",
            "abs", "muscle", "fat loss", "weight loss", "bulk", "cut", "reps", "sets",
            "squat", "deadlift", "bench", "athlete", "training", "bodybuilding",
            "transformation", "fit", "health", "wellness", "shred",
        ],
        anti_keywords=["cooking", "recipe", "makeup", "skincare"],
        adapt_patterns={
            "audio_trend":       "Sync your {trend_name} workout reel to this trending audio",
            "pov_format":        "POV: You finally got your form right on the {exercise} — use this format",
            "before_after":      "Use the 'before vs after' format for a physique transformation reveal",
            "day_of_challenge":  "Start a '30-day consistency' challenge series using this format",
            "transition":        "Show a weight-room 'glow up' transition using this trending visual format",
            "wait_for_it":       "Build suspense — 'wait for it' before your transformation reveal",
            "grwm_format":       "Do a 'Get Ready With Me: Pre-Workout Edition' reel with this format",
            "challenge":         "Participate with a gym-version of this challenge",
            "meme":              "Post the gym version of this meme with a fitness twist",
            "news":              "Give your hot take on this trending topic from an athlete's perspective",
            "honest_review":     "Do an 'honest review' of a supplement, workout gear, or gym",
            "types_of":          "Post 'Types of People at the Gym' using this trending format",
            "rate_this":         "Rate gym essentials or workout splits using this format",
        },
        base_relevance=0.12,
    ),
    "food": NicheProfile(
        name="food",
        display_name="Food & Cooking",
        emoji="🍕",
        keywords=[
            "food", "recipe", "cook", "cooking", "kitchen", "chef", "bake", "baking",
            "eat", "meal", "dish", "restaurant", "cafe", "taste", "flavor", "ingredient",
            "streetfood", "street food", "paneer", "biryani", "pasta", "pizza", "dessert",
            "protein", "healthy eating", "meal prep", "snack", "dinner", "lunch", "breakfast",
        ],
        anti_keywords=["gym", "workout"],
        adapt_patterns={
            "audio_trend":       "Film a satisfying cooking process reel with this trending audio in background",
            "pov_format":        "POV: You're eating the best [dish] of your life — first-person food review format",
            "before_after":      "Show the transformation from raw ingredients to the final plated dish",
            "wait_for_it":       "Film the suspense of an oven reveal or a sauce reduction with 'wait for it'",
            "asmr":              "Create a calming ASMR cooking video — this format is high-engagement for food",
            "timelapse":         "Time-lapse the full cooking process from prep to plate",
            "honest_review":     "Give an unfiltered honest review of a viral food item or restaurant",
            "rate_this":         "Rate every dish on a restaurant's menu or rate home-cook attempts",
            "challenge":         "Create a food version of this challenge (e.g., one-ingredient challenge)",
            "meme":              "Post the food-lover version of this trending meme",
            "news":              "React to food-related news (viral food items, restaurant closures, food trends)",
        },
        base_relevance=0.12,
    ),
    "travel": NicheProfile(
        name="travel",
        display_name="Travel & Adventure",
        emoji="✈️",
        keywords=[
            "travel", "trip", "destination", "explore", "adventure", "wanderlust",
            "mountains", "beach", "nature", "roadtrip", "trek", "hike", "backpack",
            "hotel", "resort", "flight", "budget travel", "solo travel", "itinerary",
            "hidden gem", "tourist", "wanderer", "nomad", "safari",
        ],
        anti_keywords=["gym", "cooking", "makeup"],
        adapt_patterns={
            "audio_trend":       "Use this trending audio over your most cinematic travel b-roll footage",
            "pov_format":        "POV: You're arriving at the most breathtaking destination — immersive travel POV",
            "before_after":      "Show a 'budget expectation vs luxury reality' travel comparison",
            "grwm_format":       "Do a 'Get Ready With Me: Packing for [destination]' reel",
            "timelapse":         "Time-lapse a sunrise/sunset at a scenic location",
            "aesthetic":         "Create a cinematic aesthetic travel reel with this trending format",
            "honest_review":     "Honest review of a 'viral' travel destination — was it worth it?",
            "rate_this":         "Rate budget hostels, local street food, or scenic viewpoints",
            "challenge":         "Do a travel version of this challenge (e.g., solo travel challenge)",
            "when_you":          "When you finally land in [dream destination] — relatable travel moment",
            "news":              "React to travel news (visa changes, flight deals, destination advisories)",
        },
        base_relevance=0.10,
    ),
    "fashion": NicheProfile(
        name="fashion",
        display_name="Fashion & Style",
        emoji="👗",
        keywords=[
            "fashion", "style", "outfit", "ootd", "look", "wear", "dress", "kurti",
            "saree", "styling", "grwm", "clothes", "wardrobe", "designer", "luxury",
            "streetwear", "aesthetic", "trend", "collection", "haul", "thrift",
            "sustainable fashion", "ootw", "lookbook",
        ],
        anti_keywords=["gym", "cooking"],
        adapt_patterns={
            "audio_trend":       "Film a slow-motion outfit reveal or walk-by reel with this trending audio",
            "grwm_format":       "Do a full 'Get Ready With Me' from concept outfit to final walk-out look",
            "transition":        "Execute a flawless outfit-change transition using this trending format",
            "before_after":      "Show a 'thrift flip' or wardrobe transformation — before vs after styling",
            "aesthetic":         "Create a mood-board reel of your aesthetic with this format",
            "pov_format":        "POV: Your outfit is so fire that everyone stops and stares",
            "types_of":          "Post 'Types of Outfit Vibes for [season]' using this format",
            "rate_this":         "Rate popular fashion trends or style challenges from your perspective",
            "honest_review":     "Honest review of a fast-fashion haul — is the quality worth it?",
            "challenge":         "Join this challenge with a fashion-forward interpretation",
            "meme":              "Post the fashion community's version of this meme",
        },
        base_relevance=0.12,
    ),
    "sports": NicheProfile(
        name="sports",
        display_name="Sports & Athletics",
        emoji="⚽",
        keywords=[
            "sports", "cricket", "football", "soccer", "basketball", "tennis", "badminton",
            "hockey", "athlete", "team", "match", "game", "tournament", "ipl", "fifa",
            "score", "goal", "win", "training", "play", "player", "coach",
        ],
        anti_keywords=["makeup", "cooking", "fashion"],
        adapt_patterns={
            "audio_trend":       "Use this trending audio for your best sports highlights or trick shot video",
            "pov_format":        "POV: You just scored the winning goal — immersive first-person sports POV",
            "wait_for_it":       "Build-up and deliver a jaw-dropping sports moment with 'wait for it' format",
            "before_after":      "Show pre-season vs match-day form transformation",
            "timelapse":         "Time-lapse a full training session from warmup to cooldown",
            "meme":              "Post the sports fan version of this viral meme with team/player context",
            "challenge":         "Create a sports skills challenge using this trending format",
            "news":              "React to major sports news, transfers, or match results with your take",
            "honest_review":     "Honest review of sports gear, supplements, or training programs",
            "rate_this":         "Rate top players, moments of the season, or sports equipment",
        },
        base_relevance=0.10,
    ),
    "comedy": NicheProfile(
        name="comedy",
        display_name="Comedy & Memes",
        emoji="😂",
        keywords=[
            "comedy", "funny", "meme", "joke", "lol", "relatable", "sarcasm", "humor",
            "parody", "satire", "sketch", "roast", "prank", "trolling", "fail", "reaction",
        ],
        anti_keywords=[],
        adapt_patterns={
            "audio_trend":       "Create a funny skit or relatable moment using this trending audio",
            "pov_format":        "POV: [insert painfully relatable scenario] — the funnier the better",
            "meme":              "Put your own spin on this trending meme template with original comedy",
            "challenge":         "Do the challenge but with a hilarious twist or fail compilation",
            "when_you":          "When you [relatable struggle] — extremely shareable 'when you' format",
            "types_of":          "Post 'Types of People Who [situation]' — universally relatable comedy",
            "honest_review":     "Brutally honest (comedic) review of anything — trending content format",
            "expectation_vs_reality": "Expectation vs Reality comedy format — always goes viral",
            "news":              "Comedic take or satirical reaction to trending news or events",
            "tell_me_without":   "Use the 'tell me without telling me' format for maximum engagement",
        },
        base_relevance=0.20,  # Comedy creators can adapt almost anything
    ),
    "beauty": NicheProfile(
        name="beauty",
        display_name="Beauty & Skincare",
        emoji="💄",
        keywords=[
            "beauty", "makeup", "skincare", "hair", "salon", "glow", "lipstick", "cosmetics",
            "foundation", "mascara", "eyeshadow", "contour", "highlighter", "serum", "moisturizer",
            "sunscreen", "routine", "hairstyle", "color hair", "blush", "glam", "natural look",
        ],
        anti_keywords=["gym", "sports"],
        adapt_patterns={
            "audio_trend":       "Film a satisfying makeup GRWM or skincare routine with this trending audio",
            "grwm_format":       "Do a full beauty 'Get Ready With Me' from bare face to final glam look",
            "before_after":      "Show a dramatic 'no makeup vs full glam' or skincare transformation",
            "asmr":              "Create a calming ASMR skincare routine — very high engagement for beauty",
            "honest_review":     "Honest review of a viral makeup product — does it live up to the hype?",
            "rate_this":         "Rate popular makeup techniques or skincare ingredients from a pro perspective",
            "timelapse":         "Time-lapse a full makeup look from blank slate to final glam",
            "pov_format":        "POV: Your skincare routine is finally working and your skin is glowing",
            "challenge":         "Beauty challenge version — recreate a celebrity look or color palette",
            "meme":              "Beauty community's version of this trending meme",
        },
        base_relevance=0.12,
    ),
    "tech": NicheProfile(
        name="tech",
        display_name="Tech & Gadgets",
        emoji="💻",
        keywords=[
            "tech", "technology", "ai", "coding", "programming", "developer", "software",
            "app", "phone", "gadget", "laptop", "unboxing", "review", "setup", "python",
            "javascript", "startup", "product launch", "innovation", "robot", "machine learning",
        ],
        anti_keywords=["makeup", "cooking", "fashion"],
        adapt_patterns={
            "audio_trend":       "Create an 'unboxing' or 'setup tour' reel with this trending audio",
            "honest_review":     "Honest, no-BS review of a viral tech product — your audience trusts your verdict",
            "before_after":      "Show a workstation or coding setup transformation",
            "pov_format":        "POV: You just discovered an AI tool that changes everything",
            "wait_for_it":       "Build anticipation for a product reveal or tech announcement",
            "types_of":          "Post 'Types of Developers/Programmers' — extremely relatable to your audience",
            "rate_this":         "Rate the latest AI tools, programming languages, or gadgets",
            "challenge":         "Coding challenge or tech challenge with a twist",
            "meme":              "Tech/developer meme — highly shareable within the community",
            "news":              "Hot take on major tech news (product launches, AI announcements)",
        },
        base_relevance=0.10,
    ),
    "motivation": NicheProfile(
        name="motivation",
        display_name="Motivation & Mindset",
        emoji="🔥",
        keywords=[
            "motivation", "mindset", "success", "hustle", "grind", "entrepreneur",
            "business", "growth", "inspire", "goal", "dream", "achieve", "quote",
            "self-improvement", "discipline", "consistency", "winner", "leadership",
        ],
        anti_keywords=[],
        adapt_patterns={
            "audio_trend":       "Deliver a powerful motivational message over this trending audio",
            "pov_format":        "POV: You finally decided to stop making excuses and start working",
            "before_after":      "Share a 'rock bottom to success' story using this format",
            "wait_for_it":       "Build up to a powerful mindset shift with the 'wait for it' format",
            "day_of_challenge":  "Start a 30-day discipline/consistency challenge in this format",
            "when_you":          "When you realize [mindset shift] — deeply relatable motivation format",
            "if_you":            "If you [struggle] then [advice] — direct motivational hook",
            "meme":              "Motivational twist on this trending meme — 'feel-good and share' content",
            "news":              "Motivational reaction to big news: 'Here's what we can learn from this'",
        },
        base_relevance=0.15,
    ),
    "dance": NicheProfile(
        name="dance",
        display_name="Dance & Choreography",
        emoji="💃",
        keywords=[
            "dance", "dancer", "dancing", "bhangra", "hookstep", "groove", "choreography",
            "routine", "moves", "step", "tiktok dance", "trending dance", "reel dance",
        ],
        anti_keywords=["cooking", "skincare"],
        adapt_patterns={
            "audio_trend":       "Choreograph an original dance to this trending audio — your core strength",
            "pov_format":        "POV: You just learned the trending dance in 30 minutes — reaction reel",
            "before_after":      "Show 'beginner vs pro' version of the same dance routine",
            "wait_for_it":       "Hold back your best move until the drop — 'wait for it' format",
            "types_of":          "Post 'Types of People Trying to Learn This Dance' — comedy + dance combo",
            "challenge":         "Start or participate in a dance challenge with your signature style",
            "timelapse":         "Time-lapse the process of learning a complex choreography",
        },
        base_relevance=0.15,
    ),
    "current_affairs": NicheProfile(
        name="current_affairs",
        display_name="Current Affairs & News",
        emoji="📰",
        keywords=[
            "news", "geopolitics", "india", "government", "economy", "politics",
            "breaking", "crisis", "flood", "earthquake", "war", "election",
            "budget", "parliament", "supreme court", "rbi", "inflation",
            "pakistan", "china", "usa", "ukraine", "nato", "un", "imf",
            "current affairs", "analysis", "explained", "what happened",
            "why it matters", "hot take", "opinion", "commentary"
        ],
        anti_keywords=["recipe", "workout", "makeup", "fashion haul"],
        adapt_patterns={
            "news_event":      "Create a greenscreen reaction/analysis reel on this breaking story",
            "audio_trend":     "Use this trending audio with your news commentary format",
            "meme":            "Add your analytical take on this viral moment",
            "geopolitical":    "Break down the India angle with a 60-second explainer",
            "controversy":     "Give your hot take — balanced but bold",
            "format/pov":      "POV: You finally understand why [news event] matters",
            "challenge":       "Participate: 'Tell me without telling me' about [event]",
        },
        base_relevance=0.05,
    ),
}


# ─── Relevance Scorer ─────────────────────────────────────────────────────────

def _keyword_overlap_score(text: str, keywords: list[str]) -> float:
    """
    Score the overlap between a text string and a keyword list.
    Returns 0.0–1.0.
    """
    if not text or not keywords:
        return 0.0
    text_lower = text.lower()
    hits = sum(1 for kw in keywords if kw in text_lower)
    return min(1.0, hits / max(1, len(keywords) * 0.15))


def _anti_keyword_penalty(text: str, anti_keywords: list[str]) -> float:
    """Returns a penalty factor (0.0–1.0) — lower means stronger penalty."""
    if not text or not anti_keywords:
        return 1.0
    text_lower = text.lower()
    hits = sum(1 for kw in anti_keywords if kw in text_lower)
    if hits == 0:
        return 1.0
    return max(0.3, 1.0 - hits * 0.2)


def compute_niche_relevance(
    trend: dict,
    *,
    trend_text: str | None = None,
) -> dict[str, float]:
    """
    Compute relevance scores (0.0–1.0) for each creator niche for a given trend.

    Parameters
    ----------
    trend : dict
        A trend object. Expected keys (any combination):
          audio_title, audio_artist, niche_tag, niche_category, trend_type,
          template_pattern, topic_keywords, sample_captions, caption
    trend_text : str | None
        Optional pre-built text blob to score against. If None, built from trend.

    Returns
    -------
    dict[str, float] mapping niche_name → relevance score (0.0–1.0)
    """
    # Build a unified text representation of the trend
    if trend_text is None:
        parts = [
            trend.get("audio_title") or "",
            trend.get("audio_artist") or "",
            trend.get("niche_tag") or "",
            trend.get("niche_category") or "",
            trend.get("trend_name") or "",
            trend.get("template_pattern") or "",
            " ".join(trend.get("topic_keywords") or []),
            " ".join(trend.get("sample_captions") or []),
            trend.get("caption") or "",
        ]
        trend_text = " ".join(parts)

    existing_niche = (trend.get("niche_tag") or trend.get("niche_category") or "").lower()
    trend_type = (trend.get("trend_type") or "audio").lower()
    template = (trend.get("template_pattern") or "").lower()

    scores: dict[str, float] = {}

    for niche_name, profile in NICHES.items():
        # 1. Base relevance for any trend
        score = profile.base_relevance

        # 2. Keyword overlap in trend text
        score += _keyword_overlap_score(trend_text, profile.keywords) * 0.5

        # 3. Direct niche match bonus
        if existing_niche and (existing_niche == niche_name or niche_name in existing_niche):
            score += 0.30

        # 4. Format template compatibility bonus
        if template and template in profile.adapt_patterns:
            score += 0.15

        # 5. Anti-keyword penalty
        score *= _anti_keyword_penalty(trend_text, profile.anti_keywords)

        # 6. Comedy gets a bonus for meme/challenge/format trends (more adaptable)
        if niche_name == "comedy" and trend_type in ("format", "challenge", "meme"):
            score += 0.10

        # 7. Dance gets bonus for audio trends
        if niche_name == "dance" and trend_type == "audio":
            score += 0.15

        scores[niche_name] = round(min(1.0, max(0.0, score)), 3)

    return scores


def generate_adaptation_brief(
    trend: dict,
    niche_name: str,
    relevance_score: float,
) -> dict:
    """
    Generate a niche-specific content adaptation brief for a given trend.

    Returns a dict with:
      - brief: one-sentence content idea
      - hook: a first-line hook the creator can use
      - urgency_label: urgency messaging
      - post_ideas: 2-3 bullet content ideas
    """
    profile = NICHES.get(niche_name)
    if not profile:
        return {}

    trend_type = (trend.get("trend_type") or "audio").lower()
    template = (trend.get("template_pattern") or "").lower()
    trend_name = trend.get("trend_name") or trend.get("audio_title") or "this trend"
    window_hours = trend.get("window_hours_remaining") or 24.0

    # Pick the best adapt pattern
    adapt_text = None
    if template and template in profile.adapt_patterns:
        adapt_text = profile.adapt_patterns[template]
    elif trend_type in profile.adapt_patterns:
        adapt_text = profile.adapt_patterns[trend_type]
    elif "general" in profile.adapt_patterns:
        adapt_text = profile.adapt_patterns["general"]

    # Format the adapt text
    brief = (adapt_text or f"Use '{trend_name}' for {profile.display_name} content").format(
        trend_name=trend_name,
        niche=profile.display_name,
        exercise="workout",  # fallback substitution for fitness
    )

    # Generate hook
    hooks_by_niche = {
        "fitness":    f"This {trend_name} trend is 🔥 for gym content right now",
        "food":       f"The most satisfying food reel you'll make this week 🍽️",
        "travel":     f"Pack your bags — this trend is perfect for travel content ✈️",
        "fashion":    f"Outfit inspo + trending audio = your best reel this week 👗",
        "sports":     f"Sports creators are sleeping on this trend — don't be one of them ⚽",
        "comedy":     f"This meme format is built for your humor 😂 — post NOW",
        "beauty":     f"Beauty creators: this format is converting like crazy right now 💄",
        "tech":       f"Tech takes on this trend are going viral — your audience wants your POV 💻",
        "motivation": f"This format is perfect for a powerful mindset reel 🔥",
        "dance":      f"This audio is blowing up — choreograph to it before it peaks 💃",
    }
    hook = hooks_by_niche.get(niche_name, f"Trending now — {profile.display_name} creators are missing this")

    # Urgency based on remaining window
    if window_hours <= 4:
        urgency_label = "🚨 Post NOW — window closing"
    elif window_hours <= 12:
        urgency_label = "⚡ Post within 4h for best results"
    elif window_hours <= 24:
        urgency_label = "⏰ Still time — post today"
    else:
        urgency_label = "📈 Early signal — start creating"

    # Concrete post ideas (3 ideas for top relevance, 2 for medium)
    post_ideas = _generate_post_ideas(trend, niche_name, relevance_score)

    return {
        "brief": brief,
        "hook": hook,
        "urgency_label": urgency_label,
        "post_ideas": post_ideas,
        "relevance_score": relevance_score,
    }


def _generate_post_ideas(trend: dict, niche_name: str, relevance_score: float) -> list[str]:
    """Generate 2-3 concrete post ideas for a niche + trend combination."""
    trend_name = trend.get("trend_name") or trend.get("audio_title") or "this trend"
    trend_type = (trend.get("trend_type") or "audio").lower()
    profile = NICHES.get(niche_name)
    if not profile:
        return []

    niche_specific_ideas = {
        "fitness": [
            f"Gym workout highlights synced to '{trend_name}'",
            "Transformation before/after with trending audio",
            "Morning routine reel — get ready to train",
        ],
        "food": [
            f"Recipe reveal reel using '{trend_name}' as background audio",
            "Behind-the-scenes cooking process with trending sounds",
            "Street food discovery or restaurant review reel",
        ],
        "travel": [
            f"Cinematic travel b-roll with '{trend_name}' as audio",
            "Hidden gem destination discovery with trending format",
            "Budget travel hack reveal with this trending format",
        ],
        "fashion": [
            f"Outfit of the day reveal with '{trend_name}' audio",
            "Transition outfit change using this trending visual format",
            "Thrift flip reveal — before vs after styling transformation",
        ],
        "sports": [
            f"Highlight reel of your best moves with '{trend_name}'",
            "Training drill or skills showcase with this format",
            "Hot take reaction to trending sports news",
        ],
        "comedy": [
            f"Relatable skit using '{trend_name}' trend",
            "Trending meme with your own comedic twist",
            "POV comedy format — painfully relatable scenario",
        ],
        "beauty": [
            f"GRWM makeup tutorial with '{trend_name}' playing",
            "Skincare routine transformation using trending format",
            "Honest product review in the trending 'rate this' format",
        ],
        "tech": [
            f"Unboxing or setup reel with '{trend_name}' playing",
            "Hot take on trending tech news in 30 seconds",
            "Tool or product review using 'honest review' format",
        ],
        "motivation": [
            f"Motivational monologue or quote reel with '{trend_name}'",
            "Personal story of overcoming failure using trending format",
            "Mindset shift POV — powerful and shareable",
        ],
        "dance": [
            f"Original choreography to '{trend_name}'",
            "Tutorial breakdown of trending dance steps",
            "Before vs after learning the trending dance in 1 day",
        ],
    }

    ideas = niche_specific_ideas.get(niche_name, [
        f"Create {profile.display_name} content using '{trend_name}'",
        "Adapt this trending format for your audience",
    ])

    # Return top 2 for medium relevance, top 3 for high relevance
    return ideas[:3] if relevance_score >= 0.5 else ideas[:2]


# ─── Batch Processing ─────────────────────────────────────────────────────────

def enrich_trends_with_niche_relevance(
    trends: list[dict],
    top_n_niches: int = 5,
) -> list[dict]:
    """
    Given a list of trend dicts, compute niche_relevance scores and adaptation_briefs
    for each and return the enriched list.

    Parameters
    ----------
    trends : list[dict]
        Raw trend dicts from audio trend engine or format trend detector.
    top_n_niches : int
        How many top-scoring niches to include in adaptation_briefs.

    Returns
    -------
    list[dict] — same trends with `niche_relevance` and `adaptation_briefs` added.
    """
    enriched = []
    for trend in trends:
        relevance_scores = compute_niche_relevance(trend)

        # Sort by relevance and keep top N
        top_niches = sorted(relevance_scores.items(), key=lambda x: -x[1])[:top_n_niches]

        adaptation_briefs: dict[str, dict] = {}
        for niche_name, score in top_niches:
            if score >= 0.15:  # Only generate briefs for niches with meaningful relevance
                adaptation_briefs[niche_name] = generate_adaptation_brief(trend, niche_name, score)

        enriched.append({
            **trend,
            "niche_relevance": relevance_scores,
            "adaptation_briefs": adaptation_briefs,
            "top_niches": [n for n, _ in top_niches if relevance_scores[n] >= 0.15],
        })

    return enriched


def filter_trends_for_niche(
    trends: list[dict],
    niche: str,
    min_relevance: float = 0.20,
) -> list[dict]:
    """
    Filter and sort a list of enriched trends for a specific creator niche.
    Trends without niche_relevance are scored on-the-fly.

    Returns trends sorted by relevance score descending.
    """
    result = []
    for trend in trends:
        relevance = trend.get("niche_relevance") or {}
        score = relevance.get(niche)
        if score is None:
            # Score on the fly if not pre-computed
            scores = compute_niche_relevance(trend)
            score = scores.get(niche, 0.0)
        if score >= min_relevance:
            result.append({**trend, "_niche_score": score})

    return sorted(result, key=lambda t: -t["_niche_score"])


# ─── Quick CLI test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    # Fix Windows console encoding
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    # Synthetic test trend
    test_trends = [
        {
            "audio_title": "Calm Down",
            "audio_artist": "Rema",
            "niche_tag": "music",
            "trend_type": "audio",
            "template_pattern": None,
            "window_hours_remaining": 8.0,
        },
        {
            "trend_name": "POV Format",
            "trend_type": "format",
            "template_pattern": "pov_format",
            "topic_keywords": ["pov"],
            "window_hours_remaining": 20.0,
        },
        {
            "trend_name": "Before vs After",
            "trend_type": "format",
            "template_pattern": "before_after",
            "topic_keywords": ["transformation"],
            "window_hours_remaining": 14.0,
        },
    ]

    enriched = enrich_trends_with_niche_relevance(test_trends, top_n_niches=5)

    print("\n─── Niche Relevance Engine Test ───")
    for t in enriched:
        name = t.get("trend_name") or t.get("audio_title")
        print(f"\n{'='*60}")
        print(f"Trend: {name} [{t.get('trend_type')}]")
        print("Top niche scores:")
        sorted_scores = sorted(t["niche_relevance"].items(), key=lambda x: -x[1])[:6]
        for niche, score in sorted_scores:
            bar = "█" * int(score * 20)
            briefs = t.get("adaptation_briefs", {})
            brief_txt = briefs.get(niche, {}).get("brief", "—")
            print(f"  {NICHES[niche].emoji} {niche:12} {score:.2f}  {bar}")
            if brief_txt != "—":
                print(f"               → {brief_txt[:80]}")

    # Filter for fitness specifically
    print("\n\n─── Fitness-Filtered Feed ───")
    fitness_feed = filter_trends_for_niche(enriched, "fitness", min_relevance=0.15)
    for t in fitness_feed:
        print(f"  [{t['_niche_score']:.2f}] {t.get('trend_name') or t.get('audio_title')}")
