"""
Deterministic, rule-based classifier for Reels/Trends niche tagging and content tone.
Designed to eliminate LLM dependencies for basic tagging and tone analysis.
"""
import re

# Hashtag to niche mapping dictionary
HASHTAG_NICHE_MAP = {
    "fitnessreels": "fitness",
    "foodreels": "food",
    "comedyreels": "comedy",
    "fashionreels": "fashion",
    "travelreels": "travel",
    "beautyreels": "beauty",
    "artreels": "art",
    "travel": "travel",
    "fashion": "fashion",
    "beauty": "beauty",
    "art": "art",
    "music": "music",
    "punjabisongs": "music",
    "bhojpurisong": "music",
    "indiansong": "music",
    "desimemes": "comedy",
}

# Keyword dictionaries for deterministic niche tagging
NICHE_KEYWORDS = {
    "food": [
        "food", "recipe", "kitchen", "cook", "chef", "eat", "diet", "dinner", "lunch", "breakfast",
        "healthyfood", "high protein", "swad", "khana", "cooking", "delicious", "yummy", "tasty",
        "recipe", "paneer", "chai", "restaurant", "streetfood", "snack"
    ],
    "fitness": [
        "gym", "fit", "workout", "fitness", "motivation", "cardio", "healthy", "abs", "legs",
        "exercise", "weight loss", "fat loss", "protein", "bodybuilding", "muscle", "squat", "benchpress"
    ],
    "travel": [
        "travel", "trip", "vlog", "wanderlust", "mountains", "beach", "nature", "explore", "roadtrip",
        "safarnama", "wander", "hill", "waterfall", "trek", "tourism", "vacation"
    ],
    "fashion": [
        "fashion", "look", "style", "wear", "dress", "ootd", "outfit", "aesthetic", "wardrobe",
        "fabric", "suit", "kurti", "saree", "styling", "haul", "grwm", "drape", "designer"
    ],
    "comedy": [
        "comedy", "funny", "joke", "laugh", "meme", "roast", "fun", "relatable", "funnymemes", "lol",
        "chutkule", "hasna", "hasi", "sarcasm", "comedian", "memeindia", "memes"
    ],
    "dance": [
        "dance", "step", "groove", "bhangra", "hookstep", "taal", "nach", "nachte", "kathak",
        "choreography", "dancer", "dancing"
    ],
    "news/political": [
        "news", "politics", "police", "delhi", "bjp", "congress", "modi", "yogi", "election",
        "neta", "sarkar", "government", "parliament", "protest", "arrest", "scam", "newsupdate"
    ],
    "devotional": [
        "devotional", "god", "krishna", "shiva", "ram", "bhakti", "mandir", "bhajan", "puja",
        "mahabharat", "hanuman", "mahadev", "prabhu", "temple", "blessing", "spiritual", "hare", "radhe"
    ],
    "romance/relationship": [
        "love", "heart", "miss", "story", "romance", "romantic", "couple", "dost", "friend",
        "pyar", "mohabbat", "ishq", "dil", "yaari", "yaara", "relationship", "couplegoals", "dosti",
        "boyfriend", "girlfriend", "husband", "wife"
    ],
    "tech": [
        "tech", "technology", "phone", "gadget", "software", "ai", "coding", "mobile", "app",
        "developer", "programming", "python", "javascript", "features"
    ],
    "narrative_edit": [
        "edit", "capcut", "alightmotion", "aesthetic", "vibe", "cinematic", "vlog", "pov", "status",
        "feelings", "poetry", "shayari", "quotes", "lyrics", "editor"
    ],
    "business": [
        "business", "money", "startup", "finance", "marketing", "sales", "passiveincome", "crypto",
        "invest", "trading", "stockmarket", "career", "jobs"
    ],
    "beauty": [
        "makeup", "beauty", "skincare", "hair", "salon", "glow", "cosmetics", "lipstick"
    ]
}

# Keyword weights for rule-based content tone scoring
TONE_LEXICON = {
    "wholesome": {
        "wholesome": 2.0, "uplifting": 2.0, "educational": 1.5, "heartwarming": 2.0, "motivational": 1.5,
        "positive": 1.5, "cute": 1.5, "baby": 1.5, "family": 1.5, "sweet": 1.0, "smile": 1.0, "happy": 1.0,
        "morning": 1.0, "life": 0.5, "beautiful": 1.0, "success": 1.0, "positivevibes": 1.5, "inspire": 1.5,
        "grow": 1.0, "thank": 1.0, "bless": 1.5, "help": 1.0, "learn": 1.0, "tip": 1.0, "guide": 1.0,
        "tutorial": 1.5, "howto": 1.5, "hack": 1.0, "spirit": 1.0, "caring": 1.5, "god": 1.0, "bhakti": 1.5
    },
    "wholesome_comedy": {
        # Comedy counts towards wholesome in our tone taxonomy
        "funny": 1.5, "comedy": 1.5, "laugh": 1.5, "meme": 1.0, "joke": 1.5, "roast": 1.0, "fun": 1.0,
        "lol": 1.5, "chutkule": 2.0, "hasna": 2.0, "hasi": 2.0, "desimemes": 1.5, "funnyreels": 1.5,
        "humor": 1.5, "hilarious": 1.5, "sarcasm": 1.0, "relatable": 1.0
    },
    "controversial": {
        "debate": 2.0, "opinion": 1.5, "policy": 1.5, "government": 1.0, "bjp": 1.5, "congress": 1.5,
        "modi": 1.5, "yogi": 1.5, "election": 1.5, "news": 1.0, "talk": 0.5, "scam": 2.0, "alert": 1.0,
        "warning": 1.0, "fake": 1.5, "exposing": 2.0, "truth": 1.0, "realtalk": 1.5, "facts": 1.0,
        "argument": 2.0, "protest": 2.0, "arrest": 2.0, "case": 1.0, "media": 1.0, "exposed": 2.0
    },
    "outrage": {
        "anger": 2.0, "moral": 1.0, "cheat": 2.0, "steal": 2.0, "crime": 2.0, "fight": 2.0, "abuse": 2.5,
        "bad": 1.0, "terrible": 1.5, "danger": 1.5, "expose": 1.5, "cancel": 2.0, "boycott": 2.0,
        "ban": 1.5, "corrupt": 2.0, "police": 0.5, "stayalert": 2.0, "shocking": 1.5
    },
    "emotional": {
        "sad": 2.0, "miss": 1.5, "emotional": 2.0, "cry": 2.0, "tears": 2.0, "pain": 2.0, "broken": 2.0,
        "heart": 1.0, "love": 1.0, "romantic": 1.5, "couple": 1.0, "romance": 1.5, "pyar": 1.5,
        "mohabbat": 2.0, "ishq": 2.0, "dil": 1.0, "yaari": 1.5, "yaara": 2.0, "dosti": 1.5, "breakup": 2.5,
        "heartbreak": 2.5, "alone": 1.5, "lonely": 1.5, "poetry": 1.5, "shayari": 2.0, "feelings": 1.0
    }
}

def classify_niche(caption: str, hashtags: list[str], source_hashtag_pool: str = None) -> str:
    """
    Classifies a reel into a niche deterministically without LLM calls.
    Order of precedence:
    1. Direct mapping via source_hashtag_pool or active hashtag in mapping dict.
    2. Caption / hashtag keyword matching.
    3. Default to "general".
    """
    # 1. source_hashtag_pool matching
    if source_hashtag_pool:
        pool_clean = source_hashtag_pool.lower().strip().lstrip("#")
        if pool_clean in HASHTAG_NICHE_MAP:
            return HASHTAG_NICHE_MAP[pool_clean]

    # Check individual hashtags in the mapping
    if hashtags:
        for tag in hashtags:
            tag_clean = tag.lower().strip().lstrip("#")
            if tag_clean in HASHTAG_NICHE_MAP:
                return HASHTAG_NICHE_MAP[tag_clean]

    # 2. Keyword matching on caption and hashtags
    caption_text = (caption or "").lower()
    tags_text = " ".join(hashtags or []).lower()
    full_text = f"{caption_text} {tags_text}"

    # Clean punctuation to avoid partial matches
    words = re.findall(r"[a-z\u0900-\u097f]+", full_text)
    
    niche_scores = {niche: 0 for niche in NICHE_KEYWORDS}
    for word in words:
        for niche, kw_list in NICHE_KEYWORDS.items():
            if word in kw_list:
                niche_scores[niche] += 1
                
    best_niche = max(niche_scores, key=niche_scores.get)
    if niche_scores[best_niche] > 0:
        return best_niche
        
    return "general"

def classify_tone(caption: str, hashtags: list[str]) -> str:
    """
    Classifies a reel's content tone deterministically.
    Order of precedence:
    1. Keyword score based on Hinglish and English lexicon.
    2. Default to "neutral" if scores are tied or zero.
    """
    caption_text = (caption or "").lower()
    tags_text = " ".join(hashtags or []).lower()
    full_text = f"{caption_text} {tags_text}"

    words = re.findall(r"[a-z\u0900-\u097f]+", full_text)

    # Initialize scores
    scores = {
        "wholesome": 0.0,
        "controversial": 0.0,
        "outrage": 0.0,
        "emotional": 0.0
    }

    for word in words:
        # Check wholesome
        if word in TONE_LEXICON["wholesome"]:
            scores["wholesome"] += TONE_LEXICON["wholesome"][word]
        # wholesome comedy also adds to wholesome
        if word in TONE_LEXICON["wholesome_comedy"]:
            scores["wholesome"] += TONE_LEXICON["wholesome_comedy"][word]
            
        # Check other categories
        for cat in ["controversial", "outrage", "emotional"]:
            if word in TONE_LEXICON[cat]:
                scores[cat] += TONE_LEXICON[cat][word]

    best_cat = max(scores, key=scores.get)
    if scores[best_cat] > 0.0:
        return best_cat
        
    return "neutral"
