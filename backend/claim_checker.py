"""
backend/claim_checker.py
------------------------
Rule-based text claim validator for creator analysis.
Enforces Order 93 Section E:
- why_this_works describes ONLY how creators use the sound (from captions/hashtags/counts).
- NEVER describes the sound itself (BPM, tempo, beat drops, 808/bass, vocals, instruments, genre-quality words)
  UNLESS that exact fact exists in the input evidence.
- Flags ungrounded sentences and removes them or returns None/"unknown".
"""

import re
from typing import List, Tuple, Optional

# Sound-attribute and evaluative words that CANNOT be claimed unless in input
FORBIDDEN_SOUND_TERMS = [
    r"\b\d+\s*bpm\b",
    r"\bbpm\b",
    r"\btempo\b",
    r"\bbeat\s*drop[s]?\b",
    r"\b808[s]?\b",
    r"\bbassline[s]?\b",
    r"\bbass\b",
    r"\bvocal[s]?\b",
    r"\binstrument[s]?\b",
    r"\binstrumental\b",
    r"\bsynth[s]?\b",
    r"\bpercussion\b",
    r"\bdrums?\b",
    r"\bguitar\b",
    r"\bpiano\b",
    r"\bmelodic\b",
    r"\bmelody\b",
    r"\biconic\b",
    r"\bnostalgic\b",
    r"\binfectious\b",
    r"\bhypnotic\b",
    r"\belectrifying\b",
    r"\bmesmerizing\b",
    r"\bsoothing\b",
    r"\bemotive\b",
    r"\bdistorted\b",
]

SACRED_TERMS = [
    r"\bquran\b", r"\bqur'an\b", r"\bayah\b", r"\bsurah\b", r"\brecitation\b",
    r"\bgita\b", r"\bbhajan\b", r"\baarti\b", r"\bgurbani\b", r"\bshabad\b",
    r"\bhymn\b", r"\bnamaz\b", r"\bhanuman chalisa\b", r"\bshloka\b",
    r"عيني فيها تسمي سلسبيلا", r"قرآن", r"سلسبيلا"
]

MARATHI_QUOTE_TERMS = [
    r"\bआयुष्यात\b", r"\bविचार\b", r"\bसुविचार\b", r"\bmarathi\s*quotes?\b",
    r"\bmarathistatus\b", r"\blife\s*quotes?\b", r"\bmotivation\b"
]

def is_sacred_content(input_text: str, title: str = "") -> bool:
    blob = f"{input_text} {title}".lower()
    return any(re.search(pat, blob, re.IGNORECASE) for pat in SACRED_TERMS)

def is_marathi_quote_content(input_text: str, title: str = "") -> bool:
    blob = f"{input_text} {title}".lower()
    return any(re.search(pat, blob, re.IGNORECASE) for pat in MARATHI_QUOTE_TERMS)

def check_sound_claims(input_evidence: str, output_text: Optional[str]) -> Tuple[bool, List[str], Optional[str]]:
    """
    Validates output_text against input_evidence.
    Returns:
        (is_valid, list_of_unsupported_terms_found, sanitized_output)
    """
    if not output_text or output_text.strip().lower() in ("unknown", "null", "none"):
        return True, [], "unknown"

    input_lower = input_evidence.lower()
    sentences = re.split(r"(?<=[.!?])\s+", output_text.strip())
    clean_sentences = []
    unsupported_terms = []

    for sentence in sentences:
        s_lower = sentence.lower()
        sentence_has_unsupported = False
        
        for pat in FORBIDDEN_SOUND_TERMS:
            matches = re.findall(pat, s_lower)
            if matches:
                # Check if this term or pattern existed in input evidence
                for m in matches:
                    term_str = m if isinstance(m, str) else m[0]
                    if not re.search(r"\b" + re.escape(term_str) + r"\b", input_lower):
                        unsupported_terms.append(term_str)
                        sentence_has_unsupported = True
        
        if not sentence_has_unsupported:
            clean_sentences.append(sentence)

    if unsupported_terms:
        # Some claims were unsupported
        if clean_sentences:
            sanitized = " ".join(clean_sentences)
            return False, list(set(unsupported_terms)), sanitized
        else:
            return False, list(set(unsupported_terms)), None

    return True, [], output_text
