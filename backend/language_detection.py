"""
Shared language detection module.

Canonical implementation: 5-priority chain extracted from
instagram_scraper_browser.py. Every other call site should import
_detect_audio_language from here rather than maintaining its own copy.
"""
import re
import urllib.request
import urllib.parse
import json


# ── Maps language keywords (in audio title / caption / hashtags) → ISO 639-1 ──
LANG_KEYWORD_MAP: dict[str, str] = {
    # -- Bollywood / Hindi / Regional --
    "arijit": "hi", "alka": "hi", "pritam": "hi", "rahman": "hi", "sachin": "hi", "amit": "hi", "neha": "hi", "vishal": "hi",
    "shreya": "hi", "armaan": "hi", "badshah": "hi", "dhvani": "hi", "jubin": "hi", "anu malik": "hi", "hema sardesai": "hi",
    "jasleen royal": "hi", "jasleen": "hi", "ansh chahal": "hi", "sadhu tiwari": "hi", "aishwarya majmudar": "hi", "aghori muzik": "hi",
    "shaarib toshi": "hi", "kumaar": "hi", "tanishk": "hi", "bagchi": "hi", "shreya ghoshal": "hi", "sonu nigam": "hi",
    "sunidhi": "hi", "shankar": "hi", "ehsaan": "hi", "loy": "hi", "udit narayan": "hi", "kumar sanu": "hi", "lata": "hi",
    "asha bhosle": "hi", "kishore": "hi", "rafi": "hi", "malik": "hi", "sardesai": "hi", "bollywood": "hi", "hindi song": "hi",
    "hindi music": "hi", "bhojpuri": "hi", "pawan singh": "hi", "khesari": "hi", "shilpi raj": "hi", "manoj tiger": "hi",
    "pramod premi yadav": "hi", "pramod premi": "hi", "abhishek gupta": "hi", "ps polist": "hi",
    "nadeem-shravan": "hi", "nadeem shravan": "hi", "javed ali": "hi", "mohit chauhan": "hi", "anand bhaskar": "hi",
    "romy": "hi", "ginny diwan": "hi", "roop kumar rathod": "hi", "sadhana sargam": "hi", "tapas relia": "hi",
    "antara nandy": "hi", "yuvnsoni": "hi", "hiten": "hi", "sharvi yadav": "hi",
    "atif aslam": "hi", "rahat fateh": "hi", "nusrat": "hi",
    "hindi": "hi", "hindisong": "hi", "hindireels": "hi",
    "deva": "hi", "maula": "hi", "mere": "hi", "bhajan": "hi", "mata": "hi", "chalisa": "hi", "kirtan": "hi",
    "asees kaur": "hi", "anuv jain": "hi", "des rangila": "hi", "chak de india": "hi",
    "o sanam": "hi", "jhalak dikhla ja": "hi",
    "khatam nahi hoga": "hi", "ghar se bhaag": "hi",

    # -- Tamil --
    "anirudh": "ta", "sai abhyankkar": "ta", "gana muthu": "ta", "vishnu edavan": "ta", "edavan": "ta", "kollywood": "ta",
    "tamil song": "ta", "thalapathy": "ta", "thalaiva": "ta", "a.r. rahman": "ta", "yuvan": "ta", "g.v. prakash": "ta",
    "g v prakash": "ta", "vijay": "ta", "suriya": "ta", "dhanush": "ta", "rajinikanth": "ta", "kamal haasan": "ta", "harris jayaraj": "ta",
    "imman": "ta", "vidyasagar": "ta", "ilayaraja": "ta", "ilaiyaraaja": "ta", "kj yesudas": "ta", "k.j. yesudas": "ta",
    "santhosh narayanan": "ta", "karthik": "ta", "sid sriram": "ta", "tippu": "ta", "pradeep kumar": "ta",
    "tamilsong": "ta", "tamilreels": "ta", "tamil": "ta", "dhibu ninan thomas": "ta",

    # -- Telugu --
    "tollywood": "te", "telugu song": "te", "allu arjun": "te", "mahesh babu": "te", "ram charan": "te", "thaman": "te",
    "dsp": "te", "devi sri prasad": "te", "ntr": "te", "prabhas": "te", "pawan kalyan": "te", "chiranjeevi": "te",
    "mm keeravani": "te", "keeravani": "te", "mani sharma": "te", "anantha sreeram": "te", "chandrabose": "te",
    "s.p. balu": "te", "spb": "te", "ramajogayya": "te", "s p charan": "te", "s. p. charan": "te", "smitha": "te",
    "telugusong": "te", "telugureels": "te", "telugu": "te",

    # -- Punjabi --
    "diljit": "pa", "ap dhillon": "pa", "punjabi song": "pa", "punjabi music": "pa", "sidhu moose wala": "pa",
    "karan aujla": "pa", "harrdy sandhu": "pa", "harvy sandhu": "pa", "jordan sandhu": "pa", "ammy virk": "pa", "guru randhawa": "pa", "b praak": "pa", "jaani": "pa",
    "parmish verma": "pa", "jass manak": "pa", "honey singh": "pa", "mankirt": "pa", "shubh": "pa", "sukhe": "pa",
    "gurinder gill": "pa", "brown munde": "pa", "surjit bindrakhia": "pa", "bindrakhia": "pa", "arjan dhillon": "pa",
    "amar sajaalpuria": "pa", "gur sekhon": "pa", "gur sidhu": "pa", "cheema y": "pa", "dhanda nyoliwala": "pa",
    "punjabisong": "pa", "punjabisongs": "pa", "punjabi": "pa", "tarsem jassar": "pa", "tarseem jassar": "pa",
    "satinder sartaaj": "pa", "daler mehndi": "pa", "harsh nussi": "pa", "babbu maan": "pa",
    "sukha": "pa", "manni sandhu": "pa", "hustinder": "pa", "madan madi": "pa", "sharn": "pa",
    "prem dhillon": "pa", "elly mangat": "pa", "gurnam bhullar": "pa", "navaan sandhu": "pa",
    "khan bhaini": "pa", "veet baljit": "pa", "amrit maan": "pa", "kulwinder billa": "pa",
    "korala maan": "pa", "singga": "pa", "mankirt aulakh": "pa", "balkar sidhu": "pa",
    "nirvair pannu": "pa", "geeta zaildar": "pa", "rajvir jawanda": "pa", "bhalwaan": "pa",
    "gagan kokri": "pa", "harjit harman": "pa", "kamal khaira": "pa", "kulwinder dhillon": "pa",
    "maninder buttar": "pa", "ninja": "pa", "sippy gill": "pa", "sharry mann": "pa",
    "sunanda sharma": "pa", "jatt": "pa", "gabru": "pa", "pind": "pa", "billo": "pa",
    "mitran": "pa", "sohneya": "pa", "wang": "pa", "rullde": "pa", "firde": "pa",
    "anand raaj anand": "hi", "shweta pandit": "hi", "saroj": "hi", "zubeen garg": "hi",
    "samay raina": "hi", "ashneer grover": "hi", "dilliwaliwomaniya": "hi", "rahul gurjar": "hi",
    "roopkumar rathod": "hi", "sunil shetty": "hi", "alisha chinai": "hi", "babul supriyo": "hi",
    "lucky ali": "hi", "shaan": "hi", "palash sen": "hi", "jagjit singh": "hi", "pankaj udhas": "hi",
    "samayraina": "hi", "indiasgotlatent": "hi", "bajrangbali": "hi", "sanatandharma": "hi",

    # -- Bhojpuri --
    "bhojpuri": "bho", "pawan singh": "bho", "khesari": "bho", "shilpi raj": "bho", "manoj tiger": "bho",
    "tuntun yadav": "bho", "neelkamal singh": "bho", "khushi kakkar": "bho", "gulshan yadav": "bho",
    "awadhesh premi": "bho", "raushan rohi": "bho", "bhojpurisong": "bho", "bhojpurireel": "bho",
    "samar singh": "bho", "pramod premi": "bho", "arvind akela": "bho", "kallu": "bho", "bhojpuriya": "bho",
    "babaan": "bho", "babuaan": "bho", "chehra nurani": "bho", "highlojan": "bho", "balam mor": "bho",
    "aego baat": "bho", "rajawa re": "bho", "majanuaa": "bho", "choli me holi": "bho", "kamar me dagi": "bho",
    "bihar mein": "bho", "bihari song": "bho", "bhojpuri music": "bho", "yadav 5731": "bho",
    "khushbu tiwari": "bho", "nirhua": "bho", "dinesh lal": "bho", "amarpali": "bho",

    # -- Haryanvi --
    "masoom sharma": "hne", "renuka panwar": "hne", "sapna choudhary": "hne", "pranjal dahiya": "hne",
    "ashu twinkle": "hne", "haryanvisong": "hne", "haryanvireel": "hne", "desi chore": "hne",

    # -- Gujarati --
    "osman mir": "gu", "kirtidan": "gu", "kirtidan gadhavi": "gu", "jayesh nayak": "gu", "jaymin dabhoda": "gu",
    "kaushik bharwad": "gu", "aditya gadhvi": "gu", "gujarati": "gu", "gujaratisong": "gu",
    "bandish projekt": "gu", "pooja kalyani": "gu", "dakla": "gu", "garba": "gu",
    "aishwariya majmudar": "gu", "aishwarya majmudar": "gu", "nirav barot": "gu", "umbare ubhi": "gu",
    "sambhalu re": "gu", "kanudo vhalo": "gu", "gujarati song": "gu", "gujarati reels": "gu",

    # -- Malayalam --
    "mollywood": "ml", "mohanlal": "ml", "mammootty": "ml", "dulquer": "ml", "fahadh": "ml", "sushin shyam": "ml",
    "gopi sundar": "ml", "shaan rahman": "ml", "k.s. chithra": "ml", "vineeth sreenivasan": "ml", "hesaham abdul": "ml",
    "rajeesh": "ml", "rajeesh k chandu": "ml", "kalabhavan mani": "ml", "kadakanninmunakondu": "ml",
    "malayalamsong": "ml", "malayalam": "ml",

    # -- Kannada --
    "sandalwood": "kn", "kannada song": "kn", "yash": "kn", "kiccha": "kn", "sudeep": "kn", "darshan": "kn",
    "puneeth": "kn", "ravi basrur": "kn", "v. harikrishna": "kn", "arjun janya": "kn", "sanjith hegde": "kn",
    "vijay prakash": "kn", "hemanth": "kn", "anoop seelin": "kn",
    "kannadareels": "kn", "kannada": "kn",

    # -- Marathi --
    "ajay atul": "mr", "marathi song": "mr", "avdhoot gupte": "mr", "swapnil bandodkar": "mr", "bela shende": "mr",
    " आदर्श shinde": "mr", "anand shinde": "mr",
    "marathisong": "mr", "marathireels": "mr", "marathi": "mr",

    # -- Bengali --
    "bengali song": "bn", "anupam roy": "bn",
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

_INDIAN_LANG_CODES = {"hi", "pa", "ta", "te", "kn", "mr", "ml"}
DISALLOWED_REGIONAL_LANGS = {"gu", "hne", "bho", "bn"}


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

_GENRE_LANG_MAP = {
    "punjabi": "pa",
    "bollywood": "hi",
    "indian pop": "hi",
    "devotional": "hi",
    "hindustani": "hi",
    "tamil": "ta",
    "telugu": "te",
    "marathi": "mr",
    "malayalam": "ml",
    "kannada": "kn",
    "bhojpuri": "bho",
    "haryanvi": "hne",
    "gujarati": "gu",
}

def resolve_via_music_catalog(audio_text: str, artist_text: str = "") -> str | None:
    """
    Lookup track genre via iTunes / Apple Music (Shazam catalog) API to accurately
    classify Romanized regional songs (e.g., Punjabi, Hindi, Tamil) when script/keyword checks fail.
    """
    query = f"{audio_text or ''} {artist_text or ''}".strip()
    if not query or len(query) < 3:
        return None
    try:
        url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&media=music&limit=3"
        req = urllib.request.Request(url, headers={"User-Agent": "Trendrop/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            results = data.get("results", [])
            for res in results:
                genre = (res.get("primaryGenreName") or "").lower()
                for key, code in _GENRE_LANG_MAP.items():
                    if key in genre:
                        return code
    except Exception:
        pass
    return None

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
    5. iTunes / Shazam Catalog API lookup (primaryGenreName: Punjabi, Bollywood, etc.)
    6. Default → en
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
    padded_text = f" {full_text_norm} "

    # Also extract comma/dash/slash separated segments (e.g. "Harvy Sandhu, Mirroronly")
    raw_segments = re.split(r'[,/\-\|]', audio_text or '')
    norm_segments = [f" {_normalize_text(seg)} " for seg in raw_segments if _normalize_text(seg)]

    # Check for keyword matches
    for keyword, lang_code in LANG_KEYWORD_MAP.items():
        norm_keyword = _normalize_text(keyword)
        if not norm_keyword:
            continue
        padded_kw = f" {norm_keyword} "
        if padded_kw in padded_text:
            return lang_code
        for seg in norm_segments:
            if padded_kw in seg:
                return lang_code

    # Priority 4: Native script detection
    for lang_code, (start, end) in _SCRIPT_RANGES.items():
        if any(start <= ch <= end for ch in full_text_raw):
            return lang_code

    # Priority 5: Catalog lookup (iTunes / Shazam Music API for Romanized tracks)
    catalog_lang = resolve_via_music_catalog(audio_text)
    if catalog_lang:
        return catalog_lang

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


def is_disallowed_regional_content(title: str | None, artist: str | None, caption: str | None = None, hashtags: list[str] | None = None) -> bool:
    """Check if content belongs to disallowed regional languages (Gujarati gu, Haryanvi hne, Bhojpuri bho, Bengali bn)."""
    full_text = f"{title or ''} {artist or ''} {caption or ''} {' '.join(hashtags or [])}".lower()
    for kw, lang in LANG_KEYWORD_MAP.items():
        if lang in DISALLOWED_REGIONAL_LANGS and kw in full_text:
            return True
    detected = _detect_audio_language(full_text, caption or '', hashtags or [])
    if detected in DISALLOWED_REGIONAL_LANGS:
        return True
    return False

def is_bhojpuri_content(title: str | None, artist: str | None, caption: str | None = None, hashtags: list[str] | None = None) -> bool:
    """Check if title, artist, caption or hashtags belong to Bhojpuri language/music."""
    return is_disallowed_regional_content(title, artist, caption, hashtags)

