import re
from collections import Counter

HASHTAG_POOL_MAP = {
    "INDIA_TRENDING": {
        "trendingindia", "reelsindia", "instagramindia", "indiansong",
        "reelkarofeelkaro", "desimemes", "exploreindia",
    },
    "INDIA_VERNACULAR": {
        "hindireels", "punjabisongs", "tamilreels", "telugureels",
        "kannadareels", "bhojpurisong", "marathireels",
    },
    "GLOBAL_NICHES": {
        "fitnessreels", "foodreels", "comedyreels", "fashionreels",
        "travelreels", "beautyreels", "artreels",
    },
    "GLOBAL_DISCOVERY": {
        "trending", "viral", "reels", "fyp", "explore", "instareels",
        "viralreels", "reelsviral", "tiktok", "aesthetic", "music",
        "travel", "fashion", "beauty", "art",
    },
}

HASHTAG_NICHE_MAP = {
    "fitnessreels": "fitness",
    "foodreels": "food",
    "comedyreels": "comedy",
    "fashionreels": "fashion",
    "travelreels": "travel",
    "beautyreels": "beauty",
    "artreels": "art",
    "trendingindia": "general",
    "reelsindia": "general",
    "instagramindia": "general",
    "indiansong": "music",
    "reelkarofeelkaro": "comedy",
    "desimemes": "comedy",
    "hindireels": "general",
    "punjabisongs": "music",
    "tamilreels": "general",
    "telugureels": "general",
    "kannadareels": "general",
    "bhojpurisong": "music",
    "marathireels": "general",
    "music": "music",
    "travel": "travel",
    "fashion": "fashion",
    "beauty": "beauty",
    "art": "art",
}

NICHE_KEYWORDS = {
    "fashion": ["fashion", "style", "outfit", "ootd", "look", "wear", "dress", "kurti", "saree", "styling", "grwm"],
    "food": ["food", "recipe", "cook", "cooking", "kitchen", "chef", "eat", "khana", "paneer", "chai", "tasty", "swad"],
    "comedy": ["comedy", "funny", "meme", "joke", "lol", "relatable", "sarcasm", "hasna", "chutkule", "hasi"],
    "dance": ["dance", "dancer", "dancing", "bhangra", "hookstep", "groove", "nach", "choreography"],
    "news/political": ["news", "politics", "election", "modi", "bjp", "congress", "government", "sarkar", "police", "protest", "scam"],
    "devotional": ["bhakti", "bhajan", "temple", "mandir", "god", "krishna", "shiva", "ram", "mahadev", "hanuman", "puja", "radhe"],
    "romance/relationship": ["love", "pyar", "mohabbat", "ishq", "dil", "couple", "relationship", "boyfriend", "girlfriend", "husband", "wife", "dosti", "yaari"],
    "fitness": ["gym", "fit", "workout", "fitness", "exercise", "protein", "cardio", "abs", "muscle", "fat loss", "weight loss"],
    "tech": ["tech", "technology", "ai", "coding", "programming", "developer", "software", "app", "phone", "gadget", "python", "javascript"],
    "narrative_edit": ["edit", "capcut", "alightmotion", "cinematic", "aesthetic", "pov", "vibe", "status", "shayari", "quotes", "lyrics"],
    "travel": ["travel", "trip", "vlog", "explore", "wanderlust", "mountains", "beach", "nature", "roadtrip", "trek", "safar", "safarnama"],
    "beauty": ["beauty", "makeup", "skincare", "hair", "salon", "glow", "lipstick", "cosmetics"],
    "general": ["aesthetic", "vlog", "lifestyle", "reels", "viral", "trending"],
}

HINDI_TONE_LEXICON = {
    "wholesome": {"accha": 1.5, "shukriya": 1.5, "dhanyavaad": 2.0, "bless": 1.5, "bhakti": 1.5, "parivaar": 1.5, "sukoon": 1.0, "pyaara": 1.0, "cute": 1.0},
    "comedic": {"funny": 2.0, "meme": 1.5, "lol": 1.5, "hasi": 2.0, "hasna": 2.0, "chutkule": 2.0, "sarcasm": 1.0, "relatable": 1.0},
    "devotional": {"bhakti": 2.5, "bhajan": 2.0, "mandir": 1.5, "krishna": 2.0, "shiva": 2.0, "ram": 2.0, "mahadev": 2.0, "hanuman": 2.0, "radhe": 2.0},
    "aggressive/political": {"modi": 1.5, "bjp": 1.5, "congress": 1.5, "election": 1.5, "scam": 2.5, "protest": 2.0, "police": 1.0, "arrest": 2.0, "fight": 2.0, "anger": 2.0},
    "romantic": {"love": 2.0, "pyar": 2.5, "mohabbat": 2.5, "ishq": 2.5, "dil": 1.5, "couple": 1.5, "yaari": 1.0, "yaara": 1.0, "breakup": 2.0},
    "sad/emotional": {"sad": 2.0, "emotional": 2.0, "miss": 1.5, "cry": 2.0, "tears": 2.0, "pain": 2.0, "broken": 2.5, "heartbreak": 2.5, "lonely": 1.5, "shayari": 1.5, "feelings": 1.0},
}

def _norm(text: str | None) -> str:
    return (text or "").lower()

def build_source_hashtag_pool(hashtags: list[str] | None) -> str | None:
    if not hashtags:
        return "GLOBAL_DISCOVERY"
    seen = {tag.lower().lstrip("#") for tag in hashtags if tag}
    for pool_name, pool_tags in HASHTAG_POOL_MAP.items():
        if seen.intersection(pool_tags):
            return pool_name
    return "GLOBAL_DISCOVERY"

def classify_niche(caption: str, hashtags: list[str], source_hashtag_pool: str | None = None, sample_size: int = 0) -> str:
    # If sample size is too small, return "general" to avoid overfitting
    if sample_size > 0 and sample_size < 5:
        return "general"
    
    if source_hashtag_pool:
        pool_clean = source_hashtag_pool.upper().strip()
        pool_tags = HASHTAG_POOL_MAP.get(pool_clean, set())
        if pool_clean == "GLOBAL_NICHES":
            for tag in hashtags or []:
                tag_clean = tag.lower().lstrip("#")
                if tag_clean in HASHTAG_NICHE_MAP:
                    niche = HASHTAG_NICHE_MAP[tag_clean]
                    if niche != "general":
                        return niche
        elif pool_clean in {"INDIA_TRENDING", "INDIA_VERNACULAR"}:
            return "general"
        elif pool_clean in {"GLOBAL_DISCOVERY"}:
            return "general"
        for tag in hashtags or []:
            tag_clean = tag.lower().lstrip("#")
            if tag_clean in HASHTAG_NICHE_MAP and HASHTAG_NICHE_MAP[tag_clean] != "general":
                return HASHTAG_NICHE_MAP[tag_clean]

    text = f"{caption or ''} {' '.join(hashtags or [])}".lower()
    words = re.findall(r"[a-z\u0900-\u097f]+", text)
    scores = Counter()
    for niche, terms in NICHE_KEYWORDS.items():
        for term in terms:
            if term in text:
                scores[niche] += 1
        for word in words:
            if word in terms:
                scores[niche] += 1
    return scores.most_common(1)[0][0] if scores else "general"

def classify_content_tone(caption: str, hashtags: list[str] | None = None) -> str:
    text = f"{caption or ''} {' '.join(hashtags or [])}".lower()
    words = re.findall(r"[a-z\u0900-\u097f]+", text)
    scores = Counter()
    try:
        from nltk.sentiment import SentimentIntensityAnalyzer
        sia = SentimentIntensityAnalyzer()
        compound = sia.polarity_scores(text).get("compound", 0.0)
        if compound >= 0.35:
            scores["wholesome"] += 2.0
        elif compound <= -0.35:
            scores["sad/emotional"] += 1.0
    except Exception:
        pass
    for tone, lexicon in HINDI_TONE_LEXICON.items():
        for w in words:
            if w in lexicon:
                scores[tone] += lexicon[w]
        for term, weight in lexicon.items():
            if term in text:
                scores[tone] += weight * 0.5
    return scores.most_common(1)[0][0] if scores else "wholesome"
