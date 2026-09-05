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
    "MICRO_DANCE": {
        "microdance", "trendingdance", "viralchallenge", "dancehacks",
        "indiandance", "southdance", "bangaloredance", "punjabidance"
    },
    "MICRO_FOOD": {
        "foodcreators", "microfood", "tastyfood", "indianfood",
        "streetfood", "foodrecipe", "kitchenhacks", "homecooking"
    },
    "MICRO_FASHION": {
        "fashionhacks", "styletips", "outfitideas", "microfashion",
        "indianfashion", "sareestyle", "fashiondiy", "budgetfashion"
    },
    "MICRO_COMEDY": {
        "funnyreels", "comedyhacks", "relatable", "microcomedy",
        "indiancomedy", "viralcomedy", "humor", "troll"
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
    "motivation": ["motivation", "inspire", "success", "mindset", "goals", "hustle", "grind", "positive", "growth", "motivational", "daily routine", "self improvement"],
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

    # Try to get a specific niche from hashtags first (works for all pools)
    for tag in hashtags or []:
        tag_clean = tag.lower().lstrip("#")
        if tag_clean in HASHTAG_NICHE_MAP and HASHTAG_NICHE_MAP[tag_clean] != "general":
            return HASHTAG_NICHE_MAP[tag_clean]

    # Fix #4: Previously INDIA_TRENDING / INDIA_VERNACULAR / GLOBAL_DISCOVERY all returned "general"
    # immediately, skipping keyword analysis. Now we fall through to keyword matching so that
    # a Hindi food reel tagged #trendingindia doesn't get niche_tag='general' forever.
    # GLOBAL_NICHES still gets direct hashtag resolution (already handled above).
    if source_pool := source_hashtag_pool:
        pool_clean = source_pool.upper().strip()
        # MICRO pools: resolve specific niche from hashtag map (already done above)
        # For all other pools: fall through to keyword analysis below
        _ = pool_clean  # acknowledged, no early return

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
    # Fix #11: Removed NLTK/VADER dependency — unavailable in Vercel production.
    # The Hindi tone lexicon covers the majority of Indian content correctly;
    # VADER was only marginally useful for English captions and frequently failed.
    for tone, lexicon in HINDI_TONE_LEXICON.items():
        for w in words:
            if w in lexicon:
                scores[tone] += lexicon[w]
        for term, weight in lexicon.items():
            if term in text:
                scores[tone] += weight * 0.5
    # Basic English sentiment fallback without NLTK:
    # Positive English words boost 'wholesome'; negative boost 'sad/emotional'
    _POS_WORDS = {"amazing", "great", "love", "happy", "beautiful", "awesome", "wonderful", "blessed", "grateful", "joy"}
    _NEG_WORDS = {"sad", "miss", "cry", "broken", "hate", "alone", "lost", "pain", "hurt", "tears"}
    for w in words:
        if w in _POS_WORDS:
            scores["wholesome"] += 1.0
        if w in _NEG_WORDS:
            scores["sad/emotional"] += 1.0
    return scores.most_common(1)[0][0] if scores else "wholesome"

def detect_voiceover(audio_title: str | None, caption: str | None) -> bool:
    """Detects if the audio is likely a voiceover/dialogue rather than music."""
    title_clean = (audio_title or "").lower()
    caption_clean = (caption or "").lower()
    
    # Common speech/voiceover keywords
    voiceover_keywords = {
        "original audio", "original voice", "dialogue", "speaking", 
        "talking", "podcast", "speech", "interview", "monologue",
        "voice of", "voiceover", "rant", "clips", "lip sync"
    }
    
    # If the title explicitly mentions voice or dialogue
    if any(kw in title_clean for kw in voiceover_keywords):
        # But if it also has a song-like structure or specific artist, let's keep it
        # unless it is clearly just "Original Audio"
        if "original audio" in title_clean or "original voice" in title_clean:
            return True
            
    # POV captions without commercial song titles are often voiceovers
    if "pov:" in caption_clean and len(caption_clean) > 80 and not any(m in title_clean for m in ["feat", "prod", "remix", "song", "music"]):
        if "original" in title_clean:
            return True
            
    return False

def classify_vibe_tag(niche: str, caption: str | None, hashtags: list[str] | None) -> str:
    """Classifies the vibe of the trend (e.g. aesthetic, transition, high-energy, regional)."""
    text = f"{caption or ''} {' '.join(hashtags or [])}".lower()
    
    # Priority 1: Check for transition keywords
    transition_keywords = {"transition", "beat", "edit", "cut", "loop", "transformation", "glowup", "beforeafter", "capcut", "alight"}
    if any(kw in text for kw in transition_keywords):
        return "transition"
        
    # Priority 2: Aesthetic / Lifestyle
    aesthetic_keywords = {"aesthetic", "vlog", "lifestyle", "morning", "chill", "lo-fi", "lofi", "vibe", "minimal", "grwm", "neutral"}
    if any(kw in text for kw in aesthetic_keywords) or niche in {"travel", "fashion", "beauty"}:
        return "aesthetic"
        
    # Priority 3: Comedy / Meme
    comedy_keywords = {"comedy", "funny", "meme", "joke", "lol", "relatable", "parody", "roast", "fun"}
    if any(kw in text for kw in comedy_keywords) or niche == "comedy":
        return "comedy"
        
    # Priority 4: Regional / Local
    regional_keywords = {"devotional", "bhakti", "bhajan", "mandir", "desi", "local", "regional", "state", "folksong", "folk"}
    if any(kw in text for kw in regional_keywords) or niche == "devotional":
        return "regional"
        
    return "general"

