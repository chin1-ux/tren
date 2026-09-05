"""
Shared language detection module.

Canonical implementation: 5-priority chain extracted from
instagram_scraper_browser.py. Every other call site should import
_detect_audio_language from here rather than maintaining its own copy.
"""
import re

# ── Maps language keywords (in audio title / caption / hashtags) → ISO 639-1 ──
LANG_KEYWORD_MAP: dict[str, str] = {
    # -- Bollywood / Hindi --
    "arijit": "hi", "alka": "hi", "pritam": "hi", "rahman": "hi", "sachin": "hi", "amit": "hi", "neha": "hi", "vishal": "hi",
    "shreya": "hi", "armaan": "hi", "badshah": "hi", "dhvani": "hi", "jubin": "hi", "anu malik": "hi", "hema sardesai": "hi",
    "shaarib toshi": "hi", "kumaar": "hi", "tanishk": "hi", "bagchi": "hi", "shreya ghoshal": "hi", "sonu nigam": "hi",
    "sunidhi": "hi", "shankar": "hi", "ehsaan": "hi", "loy": "hi", "udit narayan": "hi", "kumar sanu": "hi", "lata": "hi",
    "asha bhosle": "hi", "kishore": "hi", "rafi": "hi", "malik": "hi", "sardesai": "hi", "bollywood": "hi", "hindi song": "hi",
    "hindi music": "hi", "bhojpuri": "hi", "pawan singh": "hi", "khesari": "hi", "shilpi raj": "hi", "manoj tiger": "hi",
    "nadeem-shravan": "hi", "nadeem shravan": "hi", "javed ali": "hi", "mohit chauhan": "hi",
    "atif aslam": "hi", "rahat fateh": "hi", "nusrat": "hi",
    "hindi": "hi", "hindisong": "hi", "hindireels": "hi",
    "deva": "hi", "maula": "hi", "mere": "hi", "bhajan": "hi", "mata": "hi", "chalisa": "hi", "kirtan": "hi",
    "asees kaur": "hi", "anuv jain": "hi", "des rangila": "hi", "chak de india": "hi",
    "o sanam": "hi", "jhalak dikhla ja": "hi",
    "khatam nahi hoga": "hi", "ghar se bhaag": "hi",

    # -- Tamil --
    "anirudh": "ta", "sai abhyankkar": "ta", "gana muthu": "ta", "vishnu edavan": "ta", "edavan": "ta", "kollywood": "ta",
    "tamil song": "ta", "thalapathy": "ta", "thalaiva": "ta", "a.r. rahman": "ta", "yuvan": "ta", "g.v. prakash": "ta",
    "vijay": "ta", "suriya": "ta", "dhanush": "ta", "rajinikanth": "ta", "kamal haasan": "ta", "harris jayaraj": "ta",
    "imman": "ta", "vidyasagar": "ta", "ilayaraja": "ta", "santhosh narayanan": "ta", "karthik": "ta", "sid sriram": "ta",
    "tamilsong": "ta", "tamilreels": "ta", "tamil": "ta",

    # -- Telugu --
    "tollywood": "te", "telugu song": "te", "allu arjun": "te", "mahesh babu": "te", "ram charan": "te", "thaman": "te",
    "dsp": "te", "devi sri prasad": "te", "ntr": "te", "prabhas": "te", "pawan kalyan": "te", "chiranjeevi": "te",
    "mm keeravani": "te", "keeravani": "te", "mani sharma": "te", "anantha sreeram": "te", "chandrabose": "te",
    "s.p. balu": "te", "spb": "te", "ramajogayya": "te",
    "telugusong": "te", "telugureels": "te", "telugu": "te",

    # -- Punjabi --
    "diljit": "pa", "ap dhillon": "pa", "punjabi song": "pa", "punjabi music": "pa", "sidhu moose wala": "pa",
    "karan aujla": "pa", "harrdy sandhu": "pa", "ammy virk": "pa", "guru randhawa": "pa", "b praak": "pa", "jaani": "pa",
    "parmish verma": "pa", "jass manak": "pa", "honey singh": "pa", "mankirt": "pa", "shubh": "pa", "sukhe": "pa",
    "gurinder gill": "pa", "brown munde": "pa",
    "punjabisong": "pa", "punjabisongs": "pa", "punjabi": "pa",
    "satinder sartaaj": "pa", "daler mehndi": "pa", "harsh nussi": "pa", "babbu maan": "pa",

    # -- Bhojpuri --
    "bhojpuri": "bho", "pawan singh": "bho", "khesari": "bho", "shilpi raj": "bho", "manoj tiger": "bho",
    "tuntun yadav": "bho", "neelkamal singh": "bho", "khushi kakkar": "bho", "bhojpurisong": "bho", "bhojpurireel": "bho",

    # -- Haryanvi --
    "masoom sharma": "hne", "renuka panwar": "hne", "sapna choudhary": "hne", "pranjal dahiya": "hne",
    "haryanvisong": "hne", "haryanvireel": "hne", "desi chore": "hne",

    # -- Malayalam --
    "mollywood": "ml", "mohanlal": "ml", "mammootty": "ml", "dulquer": "ml", "fahadh": "ml", "sushin shyam": "ml",
    "gopi sundar": "ml", "shaan rahman": "ml", "k.s. chithra": "ml", "vineeth sreenivasan": "ml", "hesaham abdul": "ml",
    "malayalamsong": "ml", "malayalam": "ml",

    # -- Kannada --
    "sandalwood": "kn", "kannada song": "kn", "yash": "kn", "kiccha": "kn", "sudeep": "kn", "darshan": "kn",
    "puneeth": "kn", "ravi basrur": "kn", "v. harikrishna": "kn", "arjun janya": "kn", "sanjith hegde": "kn",
    "vijay prakash": "kn", "hemanth": "kn",
    "kannadareels": "kn", "kannada": "kn",

    # -- Marathi --
    "ajay atul": "mr", "marathi song": "mr", "avdhoot gupte": "mr", "swapnil bandodkar": "mr", "bela shende": "mr",
    " आदर्श shinde": "mr", "anand shinde": "mr",
    "marathisong": "mr", "marathireels": "mr", "marathi": "mr",

    # -- Bengali --
    "bengali song": "bn", "arijit singh": "bn", "anupam roy": "bn",
    "bengalisong": "bn", "bengalireels": "bn", "bengali": "bn",

    # -- Other --
    "english": "en"
}

# Maps specific hashtags used as pool seeds → guaranteed language code (highest priority)
VERNACULAR_HASHTAG_LANG: dict[str, str] = {
    "hindireels": "hi",
    "punjabisongs": "pa",
    "tamilreels": "ta",
    "telugureels": "te",
    "kannadareels": "kn",
    "marathireels": "mr",
    "bengalireels": "bn",
    "bhojpurireel": "bho",
    "haryanvireel": "hne",
    "tirangayatra": "hi",
}

_INDIAN_LANG_CODES = {"hi", "pa", "ta", "te", "kn", "mr", "ml", "bn", "bho", "hne"}


def _normalize_text(t: str) -> str:
    if not t:
        return ""
    t = t.lower()
    t = re.sub(r'[^a-z0-9]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

_SCRIPT_RANGES = {
    "hi": ("\u0900", "\u097F"), # Devanagari
    "bn": ("\u0980", "\u09FF"), # Bengali
    "pa": ("\u0A00", "\u0A7F"), # Gurmukhi
    "te": ("\u0C00", "\u0C7F"), # Telugu
    "kn": ("\u0C80", "\u0CFF"), # Kannada
    "ml": ("\u0D00", "\u0D7F"), # Malayalam
    "ta": ("\u0B80", "\u0BFF"), # Tamil
}

def _detect_audio_language(
    audio_text: str,
    caption_text: str,
    hashtags: list[str] | None = None,
    source_hashtag_pool: str | None = None,
) -> str:
    """
    Detect audio language with a reliable priority chain:
    1. Vernacular hashtag (e.g. #tamilreels → ta) — most reliable
    2. Individual hashtag keyword match
    3. Keyword match in title/artist/caption using normalized text and word boundaries
    4. Native script detection in caption/title → corresponding language
    5. Default → en
    """
    # Priority 1: vernacular pool hashtag (100% reliable)
    for tag in (hashtags or []):
        clean = tag.lower().lstrip("#").replace(" ", "")
        if clean in VERNACULAR_HASHTAG_LANG:
            return VERNACULAR_HASHTAG_LANG[clean]

    # Priority 2: hashtag keyword → language map
    for tag in (hashtags or []):
        clean = tag.lower().lstrip("#")
        if clean in LANG_KEYWORD_MAP:
            return LANG_KEYWORD_MAP[clean]

    # Priority 3: keyword match in normalized audio + caption text
    full_text_raw = f"{audio_text or ''} {caption_text or ''}"
    full_text_norm = _normalize_text(full_text_raw)
    # Pre-pad with spaces to simulate word boundaries
    padded_text = f" {full_text_norm} "

    # Check for keyword matches
    for keyword, lang_code in LANG_KEYWORD_MAP.items():
        norm_keyword = _normalize_text(keyword)
        if norm_keyword and f" {norm_keyword} " in padded_text:
            return lang_code

    # Priority 4: Native script detection
    for lang_code, (start, end) in _SCRIPT_RANGES.items():
        if any(start <= ch <= end for ch in full_text_raw):
            return lang_code

    # Default
    return "en"


def _looks_indian_audio(title: str | None, artist: str | None, caption: str | None = None) -> bool:
    full_text_raw = f"{title or ''} {artist or ''} {caption or ''}"
    full_text_norm = _normalize_text(full_text_raw)
    padded_text = f" {full_text_norm} "

    # Check against LANG_KEYWORD_MAP keys that map to Indian languages
    for keyword, lang_code in LANG_KEYWORD_MAP.items():
        if lang_code in _INDIAN_LANG_CODES:
            norm_keyword = _normalize_text(keyword)
            if norm_keyword and f" {norm_keyword} " in padded_text:
                return True

    # Also check scripts
    for lang_code, (start, end) in _SCRIPT_RANGES.items():
        if lang_code in _INDIAN_LANG_CODES and any(start <= ch <= end for ch in full_text_raw):
            return True

    return False
