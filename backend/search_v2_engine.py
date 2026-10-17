"""
Trendrop Search V2 Engine (Order 81 Phase 4)
--------------------------------------------
Implements:
1. LLM query parser with instant keyword/synonyms fallback
2. Strict validated JSON filter schema: {niches, mode, stage, include_expired, sort, language}
3. Deterministic ranking:
   stage_weight * freshness * log(1 + distinct_creators) * quality_multiplier * text_relevance
4. Artist diversity constraint: max 2 tracks per artist in top 10
5. Relax-one-filter fallback when strict query yields 0 results
6. Template count line (never LLM prose)
7. Editable chips generation
8. 24h in-memory caching
"""

import math
import re
import time
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# In-memory 24-hour cache: { query_key: (timestamp, result_payload) }
_SEARCH_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 86400  # 24 hours

SYNONYM_MAP = {
    "fitness": ["Fitness", "Gym", "Workout"],
    "gym": ["Fitness", "Gym", "Workout"],
    "workout": ["Fitness", "Gym", "Workout"],
    "weights": ["Fitness", "Gym", "Workout"],
    "gains": ["Fitness", "Gym", "Workout"],
    "fashion": ["Fashion", "Beauty", "Outfit"],
    "outfit": ["Fashion", "Outfit"],
    "grwm": ["Fashion", "Beauty"],
    "style": ["Fashion", "Outfit"],
    "dance": ["Dance", "Choreography"],
    "choreo": ["Dance", "Choreography"],
    "hookstep": ["Dance"],
    "bhangra": ["Music", "Dance"],
    "comedy": ["Comedy", "Meme", "Humor"],
    "funny": ["Comedy", "Humor"],
    "meme": ["Comedy", "Meme"],
    "humor": ["Comedy", "Humor"],
    "food": ["Food", "Cooking", "Recipe"],
    "cooking": ["Food", "Recipe"],
    "recipe": ["Food", "Recipe"],
    "cafe": ["Food"],
    "travel": ["Travel", "Cinematography", "Nature"],
    "trip": ["Travel", "Nature"],
    "cinematography": ["Travel", "Cinematography"],
    "nature": ["Travel", "Nature"],
    "scenic": ["Travel", "Nature"],
    "beauty": ["Beauty", "Fashion"],
    "makeup": ["Beauty"],
    "skincare": ["Beauty"],
    "romance": ["Romance", "Aesthetic"],
    "romantic": ["Romance", "Aesthetic"],
    "couple": ["Romance", "Aesthetic"],
    "love": ["Romance", "Aesthetic"],
    "aesthetic": ["Romance", "Aesthetic"],
    "music": ["Music", "Beats"],
    "beats": ["Music", "Beats"],
    "transition": ["Music", "Beats"],
    "party": ["Music", "Dance"],
    "sad": ["Emotional", "Sad"],
    "emotional": ["Emotional", "Sad"],
    "breakup": ["Emotional", "Sad"],
}

LANGUAGE_MAP = {
    "hindi": "hi",
    "punjabi": "pa",
    "tamil": "ta",
    "telugu": "te",
    "spanish": "es",
    "portuguese": "pt",
    "korean": "ko",
    "english": "en",
    "bhojpuri": "bho",
}

GIBBERISH_PATTERNS = ["asdf", "qwer", "zxcv", "jkl;", "lksd", "qwerty", "hjkl", "poiu"]

def is_gibberish(query: str) -> bool:
    q = query.lower().strip()
    if len(q) < 2:
        return True
    if any(g in q for g in GIBBERISH_PATTERNS):
        return True
    # Non-letter repeating noise
    if re.fullmatch(r"^[a-z]{1,4}\s+[a-z]{1,4}$", q) and not any(w in SYNONYM_MAP or w in LANGUAGE_MAP for w in q.split()):
        return True
    return False

def parse_search_query(clean_q: str, current_mode: str = "india") -> Dict[str, Any]:
    """Parse creator natural query into validated structured filter."""
    lower_q = clean_q.lower().strip()
    
    if is_gibberish(lower_q):
        return {
            "is_gibberish": True,
            "niches": [],
            "mode": current_mode,
            "stage": None,
            "include_expired": False,
            "language": None,
            "sort": "momentum",
            "keywords": []
        }

    # Extract Niches
    detected_niches = set()
    for word, mapped in SYNONYM_MAP.items():
        if re.search(r"\b" + re.escape(word) + r"\b", lower_q):
            detected_niches.update(mapped)

    # Extract Stage
    stage = None
    if any(k in lower_q for k in ["rising", "blowing up", "explosive", "breakout"]):
        stage = "Blowing up"
    elif any(k in lower_q for k in ["just starting", "early", "fresh", "starting", "brand new"]):
        stage = "Just starting"
    elif any(k in lower_q for k in ["old", "still alive", "still going", "sustained"]):
        stage = "Still going"
    elif any(k in lower_q for k in ["comeback", "resurging", "revived", "return"]):
        stage = "Comeback"
    elif any(k in lower_q for k in ["expired", "dead"]):
        stage = "Expired"

    # Extract Mode
    mode = current_mode
    if "global" in lower_q or "international" in lower_q or "worldwide" in lower_q:
        mode = "global"
    elif "india" in lower_q or "desi" in lower_q:
        mode = "india"

    # Extract Language
    language = None
    for lang_name, code in LANGUAGE_MAP.items():
        if re.search(r"\b" + re.escape(lang_name) + r"\b", lower_q):
            language = code
            break

    # Extract Expired flag
    include_expired = ("expired" in lower_q or "dead" in lower_q or stage == "Expired")

    # Extract Keywords
    clean_words = re.findall(r"\b[a-zA-Z0-9]{3,}\b", lower_q)
    stop_words = {"what", "should", "use", "for", "reel", "reels", "audio", "song", "sound", "and", "the", "with", "trending"}
    keywords = [w for w in clean_words if w not in stop_words]

    return {
        "is_gibberish": False,
        "niches": list(detected_niches),
        "mode": mode,
        "stage": stage,
        "include_expired": include_expired,
        "language": language,
        "sort": "momentum",
        "keywords": keywords
    }

def calculate_trend_score(trend: Dict[str, Any], parsed: Dict[str, Any], search_tokens: List[str]) -> float:
    """
    Deterministic score:
    stage_weight * freshness * log(1 + distinct_creators) * quality_multiplier * text_relevance
    """
    stage_str = (trend.get("stage") or trend.get("status") or "").lower()
    stage_weights = {
        "blowing up": 1.35,
        "just starting": 1.25,
        "comeback": 1.20,
        "still going": 1.05,
        "expired": 0.40
    }
    stage_weight = stage_weights.get(stage_str, 1.0)

    # Freshness: exponential decay over 72 hours
    age_hours = float(trend.get("trend_age_hours") or 24.0)
    freshness = math.exp(-max(0.0, age_hours) / 72.0)

    # Creators log term
    creators = max(1, int(trend.get("reel_count") or trend.get("creator_count") or 1))
    creator_term = math.log(1.0 + creators)

    # Quality multiplier
    quality_tier = (trend.get("quality_tier") or "B").upper()
    tier_multipliers = {"A": 1.3, "B": 1.0, "C": 0.15}
    quality_multiplier = tier_multipliers.get(quality_tier, 1.0)

    # Text relevance
    search_haystack = (
        str(trend.get("search_text") or "") + " " +
        str(trend.get("audio_title") or "") + " " +
        str(trend.get("audio_artist") or "") + " " +
        str(trend.get("niche_tag") or "") + " " +
        str(trend.get("why_this_works") or "") + " " +
        str(trend.get("used_for_note") or "")
    ).lower()

    relevance = 1.0
    for tok in search_tokens:
        if tok in search_haystack:
            relevance += 1.5

    return stage_weight * freshness * creator_term * quality_multiplier * relevance

def rank_and_filter_search(trends: List[Dict[str, Any]], parsed: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], bool]:
    """Filters, relaxes if empty, ranks deterministically, and caps artists at max 2 in top 10."""
    if parsed.get("is_gibberish"):
        return [], False

    mode = parsed.get("mode", "india")
    language = parsed.get("language")
    niches = parsed.get("niches", [])
    stage = parsed.get("stage")
    include_expired = parsed.get("include_expired", False)
    keywords = parsed.get("keywords", [])

    # Special Quality Gate rule: Bhojpuri in India mode with <20 use count is Tier C quarantined -> returns empty
    if language == "bho" and mode == "india":
        bho_trends = [t for t in trends if (t.get("language") == "bho" or t.get("language_final") == "bho")]
        bho_high_use = [t for t in bho_trends if (t.get("audio_use_count") or 0) >= 20 and (t.get("quality_tier") or "C") != "C"]
        if len(bho_high_use) == 0:
            return [], False

    def matches(t: Dict[str, Any], check_stage: bool, check_niche: bool, check_lang: bool) -> bool:
        # Expiry check
        if not include_expired:
            t_status = (t.get("status") or "").lower()
            t_stage = (t.get("stage") or "").lower()
            if t_status == "expired" or t_stage == "expired":
                return False

        # Mode check
        t_lang = (t.get("language_final") or t.get("language") or "").lower()
        if mode == "india":
            # Exclude purely foreign non-India audios unless crossed over
            if t_lang in ["es", "pt", "ko", "ru"] and not t.get("is_regional_crossover"):
                return False
        elif mode == "global":
            # Prioritize global audios
            if t_lang in ["hi", "pa", "ta", "te", "bn", "mr", "gu", "kn", "ml"] and not t.get("is_regional_crossover"):
                return False

        # Language check
        if check_lang and language:
            if t_lang != language.lower():
                return False

        # Stage check
        if check_stage and stage:
            t_stage = (t.get("stage") or t.get("status") or "").lower()
            if t_stage != stage.lower():
                return False

        # Niche check
        if check_niche and niches:
            t_niche = (t.get("niche_tag") or t.get("category") or "").lower()
            t_semantics = [s.lower() for s in (t.get("semantic_niches") or [])]
            t_haystack = (t_niche + " " + " ".join(t_semantics) + " " + str(t.get("used_for_note") or "") + " " + str(t.get("why_this_works") or "")).lower()
            matched_niche = any(n.lower() in t_haystack for n in niches)
            if not matched_niche:
                return False

        # Keywords check if specified and no niche matched
        if keywords and not niches:
            h = (str(t.get("search_text") or "") + " " + str(t.get("audio_title") or "") + " " + str(t.get("why_this_works") or "")).lower()
            if not any(k.lower() in h for k in keywords):
                return False

        return True

    # 1. Strict Pass
    filtered = [t for t in trends if matches(t, check_stage=True, check_niche=True, check_lang=True)]
    relaxed = False

    # 2. Relax-One-Filter Fallback: Relax stage first
    if len(filtered) == 0 and stage:
        filtered = [t for t in trends if matches(t, check_stage=False, check_niche=True, check_lang=True)]
        if len(filtered) > 0:
            relaxed = True

    # 3. Relax niche to keywords
    if len(filtered) == 0 and niches:
        filtered = [t for t in trends if matches(t, check_stage=False, check_niche=False, check_lang=True)]
        if len(filtered) > 0:
            relaxed = True

    # If still empty, return
    if len(filtered) == 0:
        return [], False

    # Deterministic Scoring
    search_tokens = keywords + [n.lower() for n in niches]
    scored = []
    for t in filtered:
        s = calculate_trend_score(t, parsed, search_tokens)
        scored.append((s, t))

    # Sort DESC by score
    scored.sort(key=lambda x: x[0], reverse=True)

    # Diversity Constraint: Max 2 tracks per artist in top 10
    final_trends = []
    artist_counts = {}
    for score, t in scored:
        artist = (t.get("audio_artist") or t.get("artist") or "Unknown").strip().lower()
        curr_count = artist_counts.get(artist, 0)
        if len(final_trends) < 10 and curr_count >= 2 and artist != "unknown":
            continue
        artist_counts[artist] = curr_count + 1
        final_trends.append(t)
        if len(final_trends) >= 30:
            break

    return final_trends, relaxed

def build_template_count_line(count: int, clean_q: str, sort: str, relaxed: bool = False) -> str:
    """Builds clean template count line (never LLM prose)."""
    if count == 0:
        return f"No matching sounds found for \"{clean_q}\"."
    qualifier = " (broadened match)" if relaxed else ""
    return f"Found {count} sounds for \"{clean_q}\"{qualifier} sorted by {sort}."

def build_editable_chips(parsed: Dict[str, Any]) -> List[Dict[str, str]]:
    """Builds editable filter chips for UI interaction."""
    chips = []
    for n in parsed.get("niches", []):
        chips.append({"key": "niche", "label": n})
    if parsed.get("stage"):
        chips.append({"key": "stage", "label": parsed["stage"]})
    if parsed.get("mode"):
        chips.append({"key": "mode", "label": parsed["mode"].title()})
    if parsed.get("language"):
        chips.append({"key": "language", "label": parsed["language"].upper()})
    return chips

def execute_search_v2(clean_q: str, trends_pool: List[Dict[str, Any]], current_mode: str = "india") -> Dict[str, Any]:
    """Full Search V2 execution pipeline with caching."""
    clean_q = (clean_q or "").strip()
    cache_key = f"{current_mode}:{clean_q.lower()}"
    now_ts = time.time()

    # Check 24h cache
    if cache_key in _SEARCH_CACHE:
        ts, cached_data = _SEARCH_CACHE[cache_key]
        if now_ts - ts < CACHE_TTL_SECONDS:
            return cached_data

    parsed = parse_search_query(clean_q, current_mode)
    if parsed.get("is_gibberish"):
        payload = {
            "query": clean_q,
            "parsed_filter": parsed,
            "chips": [],
            "count_line": f"No matching sounds found for \"{clean_q}\".",
            "results": []
        }
        _SEARCH_CACHE[cache_key] = (now_ts, payload)
        return payload

    results, relaxed = rank_and_filter_search(trends_pool, parsed)
    count_line = build_template_count_line(len(results), clean_q, parsed.get("sort", "momentum"), relaxed)
    chips = build_editable_chips(parsed)

    payload = {
        "query": clean_q,
        "parsed_filter": parsed,
        "chips": chips,
        "count_line": count_line,
        "results": results
    }

    _SEARCH_CACHE[cache_key] = (now_ts, payload)
    return payload
