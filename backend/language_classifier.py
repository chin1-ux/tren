"""
ORDER 18 Language Classifier:
- Direct Gemini ONLY using model 'gemini-3.5-flash'.
- Key rotation across available GEMINI_API_KEYs with 429 backoff.
- No fallback to Groq/allam or OpenRouter. If Gemini fails, returns 'unknown'.
- Pre-rules (deterministic script match) apply ONLY to audio TITLE and ARTIST (NOT captions).
- Strict vocal language evaluation.
No Golden Checkpoint files touched.
"""
import os
import re
import json
import time
import logging
from dotenv import load_dotenv

load_dotenv()
backend_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(backend_dir, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

from llm import call_gemini, _collect_env_keys

logger = logging.getLogger("language_classifier")

ALLOWED_LANGUAGES = {
    "hi", "pa", "ta", "te", "kn", "ml", "mr", "bn", "gu", "ne",
    "en", "es", "pt", "ko", "instrumental", "other", "unknown"
}

TARGET_GEMINI_MODEL = "gemini-3.5-flash"

def classify_audio(title: str, artist: str, captions: str = "") -> dict:
    """
    Classify the SUNG vocal language of an audio track using Gemini 3.5 Flash.
    Returns: {
        "language": str,
        "confidence": float,
        "vocal_evidence": str,
        "context_evidence": str,
        "provider_model": str,
        "_raw": dict
    }
    """
    title_str = str(title or "")
    artist_str = str(artist or "")
    captions_str = str(captions or "")
    title_artist_text = f"{title_str} {artist_str}"

    # --- Step 3b: Deterministic Pre-rules (TITLE and ARTIST ONLY) ---
    # 1. Title contains "instrumental"
    if "instrumental" in title_str.lower():
        return {
            "language": "instrumental",
            "confidence": 1.0,
            "vocal_evidence": "Title explicitly specifies 'instrumental'",
            "context_evidence": "Title deterministic match",
            "provider_model": "rule/title-instrumental",
            "_raw": {}
        }

    # 2. Script detection in audio TITLE and ARTIST ONLY (NOT captions)
    script_rules = [
        (r'[\u0A00-\u0A7F]', "pa", "Gurmukhi script in title/artist"),
        (r'[\u0B80-\u0BFF]', "ta", "Tamil script in title/artist"),
        (r'[\u0D00-\u0D7F]', "ml", "Malayalam script in title/artist"),
        (r'[\u0C00-\u0C7F]', "te", "Telugu script in title/artist"),
        (r'[\u0C80-\u0CFF]', "kn", "Kannada script in title/artist"),
        (r'[\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F]', "ko", "Hangul script in title/artist")
    ]

    for pattern, lang_code, ev_msg in script_rules:
        if re.search(pattern, title_artist_text):
            return {
                "language": lang_code,
                "confidence": 0.95,
                "vocal_evidence": ev_msg,
                "context_evidence": "Deterministic title/artist script match",
                "provider_model": f"rule/script-{lang_code}",
                "_raw": {}
            }

    # --- Step 3a & 3c: Gemini-Only LLM Prompt & Call ---
    system_prompt = (
        "You are an expert music and vocal language classifier.\n"
        "Your sole task: Classify the language SUNG in the audio track.\n\n"
        "CRITICAL RULES:\n"
        "1. Classify the language of the vocals/singing, NOT the topic of the reels, NOT dance trends, and NOT hashtags.\n"
        "2. Hashtags (#kpop, #viral, #reels) and reel descriptions describe the reels, NOT the vocals, and CANNOT ALONE justify a vocal language.\n"
        "3. Allowed language codes:\n"
        "   - hi: Hindi\n"
        "   - pa: Punjabi (e.g. Kulwant Khang, Charcha, Mausam, Punjabi songs)\n"
        "   - ta: Tamil (e.g. D. Imman, Tamil films)\n"
        "   - te: Telugu (e.g. Anirudh Ravichander Telugu releases, Amma Amma)\n"
        "   - kn: Kannada\n"
        "   - ml: Malayalam (e.g. Neeyam Thanalinu, Minunundae Mullapolae)\n"
        "   - mr: Marathi\n"
        "   - bn: Bengali\n"
        "   - gu: Gujarati (e.g. Geeta Rabari, Gujarati folk)\n"
        "   - ne: Nepali (e.g. Kobid Bazra, Bikesh Bazra, Deepson Putuwar)\n"
        "   - en: English (e.g. She Loves Me by Serani)\n"
        "   - es: Spanish (e.g. Arcángel, Yandel, Spanish reggaeton/latin)\n"
        "   - pt: Portuguese (e.g. Me Chama, Furacão 2000, Brazilian Funk, Segredos e Defeitos)\n"
        "   - ko: Korean (e.g. TWS, BESTie, Girls' Generation)\n"
        "   - instrumental: Audio with NO vocal lyrics (beats/instruments only)\n"
        "   - other: Vocal lyrics present in a language not listed above\n"
        "   - unknown: Unsure or insufficient data — return 'unknown' rather than guessing.\n"
        "4. Never claim to know an artist or lyrics if you are unsure.\n"
        "5. Output ONLY a JSON object with EXACT keys:\n"
        '   {"language": "code", "confidence": float, "vocal_evidence": "reasons from title/lyrics", "context_evidence": "reasons from hashtags/reels"}\n'
        "6. STRICT CONFIDENCE RULE: If vocal_evidence is empty or missing, confidence MUST BE <= 0.5."
    )

    user_prompt = f"""
Audio Title: "{title_str}"
Artist: "{artist_str}"
Sample Captions: "{captions_str}"

Pick EXACTLY ONE language code from: [hi, pa, ta, te, kn, ml, mr, bn, gu, ne, en, es, pt, ko, instrumental, other, unknown].
Return JSON format: {{"language": "code", "confidence": 0.85, "vocal_evidence": "exact lyric/title evidence", "context_evidence": "hashtag/reel context"}}
"""

    gemini_keys = _collect_env_keys(("GEMINI_API_KEY",))
    res = None

    # Step 3a: Strict Gemini ONLY call using gemini-3.5-flash with rate limit retry
    if gemini_keys:
        for attempt in range(3):
            for gkey in gemini_keys:
                try:
                    res = call_gemini(system_prompt, user_prompt, gemini_key=gkey, response_mime_type="application/json", timeout=30, model=TARGET_GEMINI_MODEL)
                    if res:
                        break
                except Exception as ge:
                    logger.warning("Gemini key attempt error: %s", ge)
                    if ("429" in str(ge) or "RESOURCE_EXHAUSTED" in str(ge) or "503" in str(ge)):
                        time.sleep(62.0)
            if res is not None:
                break

    # Step 3a: If Gemini fails, return "unknown" (NO fallback to Groq/allam or OpenRouter)
    if res is None:
        return {
            "language": "unknown",
            "confidence": 0.0,
            "vocal_evidence": "",
            "context_evidence": "Gemini API call failed or unavailable",
            "provider_model": f"gemini/{TARGET_GEMINI_MODEL}-failed",
            "_raw": {}
        }

    lang = (res.get("language") or "unknown").lower().strip()
    if lang not in ALLOWED_LANGUAGES:
        lang = "unknown"

    vocal_ev = str(res.get("vocal_evidence") or "").strip()
    context_ev = str(res.get("context_evidence") or "").strip()
    
    try:
        conf = float(res.get("confidence") or 0.0)
    except (ValueError, TypeError):
        conf = 0.0

    # Rule: If vocal_evidence is empty, cap confidence at 0.5
    if not vocal_ev and conf > 0.5:
        conf = 0.5

    # Threshold: Any result with confidence < 0.75 is stored as "other"
    if conf < 0.75 and lang not in ("unknown", "instrumental"):
        lang = "other"

    return {
        "language": lang,
        "confidence": round(conf, 2),
        "vocal_evidence": vocal_ev,
        "context_evidence": context_ev,
        "provider_model": f"gemini/{TARGET_GEMINI_MODEL}",
        "_raw": res
    }
