"""
backend/reel_pattern_engine.py
------------------------------
Human-mimicking AI pattern analysis engine for 'why_this_works' and 'used_for'.
Analyzes up to 40-50 reels from the reels table:
1. Dense Reel Evidence Assembly (zero API cost)
2. Deterministic Heuristic Pre-Clustering (zero API cost)
3. Gemini 2.0 Flash Pattern Synthesizer with rate limits (15 RPM guardrail)
4. Rejection of discordant / junk / spam audios (no fake hallucinations)
"""

import os
import re
import json
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

from llm import call_gemini, _collect_env_keys

logger = logging.getLogger("reel_pattern_engine")

TARGET_GEMINI_MODEL = "gemini-3.5-flash-lite"
_GLOBAL_GEMINI_KEYS = None
_LAST_GEMINI_CALL_TIME = 0.0

# 3.0s sleep minimum between Gemini calls = ~12-14 RPM strictly within 15 RPM free limit
MIN_CALL_INTERVAL_SECONDS = 3.0

# High-confidence creator format keyword clusters
FORMAT_KEYWORDS = {
    "transition": [
        "transition", "transitions", "capcut", "template", "beat drop", "sync",
        "velocity", "edit", "edits", "glowup", "glow up", "before after", "cut",
        "drop", "speed ramp"
    ],
    "dance": [
        "dance", "dancing", "choreography", "dc", "challenge", "steps", "hookstep",
        "dancechallenge", "routine"
    ],
    "outfit-showcase": [
        "outfit", "ootd", "grwm", "haul", "meesho", "zara", "style", "fitcheck",
        "fashion", "aesthetic", "wardrobe", "styling", "lookbook", "ethnicwear"
    ],
    "meme": [
        "pov", "relatable", "when you", "me trying", "nobody talks", "skit",
        "funny", "humor", "comedy", "joke", "real", "us bro", "relatablereels"
    ],
    "fitness": [
        "gym", "pr", "workout", "fitness", "physique", "pump", "training",
        "bodybuilding", "lifting", "gymrat", "deadlift", "bench"
    ],
    "travel": [
        "travel", "wanderlust", "vlog", "explore", "mountains", "beach",
        "dump", "mini vlog", "trip", "vacation", "roadtrip"
    ],
    "voiceover": [
        "quote", "storytime", "motivation", "deep", "mindset", "life lessons",
        "poetry", "shayari", "thoughts", "feelings", "status"
    ],
    "tutorial": [
        "tutorial", "how to", "recipe", "cooking", "hack", "tips", "diy",
        "step by step", "guide", "learn"
    ]
}

GENERIC_SPAM_TAGS = {
    "viral", "reels", "trending", "explore", "fyp", "foryou", "explorepage",
    "instagram", "trend", "trendingreels", "trendingaudio", "virelvideo",
    "shortvideo", "followme", "likeforlike", "instalike", "video"
}


def _get_gemini_keys() -> List[str]:
    global _GLOBAL_GEMINI_KEYS
    if _GLOBAL_GEMINI_KEYS is None:
        _GLOBAL_GEMINI_KEYS = _collect_env_keys(("GEMINI_API_KEY",))
        _GLOBAL_GEMINI_KEYS.reverse()
    return _GLOBAL_GEMINI_KEYS or []


def _clean_caption(caption: Optional[str]) -> str:
    """Strip emojis, consecutive newlines, and truncate to 120 chars."""
    if not caption:
        return ""
    text = re.sub(r"[\r\n]+", " ", str(caption))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:120]


def _filter_hashtags(tags: Optional[List[str]]) -> List[str]:
    """Filter out pure spam hashtags to retain creator niche signals."""
    if not tags:
        return []
    filtered = []
    for t in tags:
        clean = str(t).replace("#", "").strip().lower()
        if clean and clean not in GENERIC_SPAM_TAGS and len(clean) > 2:
            filtered.append(clean)
    return filtered[:6]


def pre_cluster_reels(reels: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Deterministic local analysis across sampled reels (0 API cost).
    Computes keyword cluster consensus ratio.
    """
    if not reels:
        return {
            "dominant_format": "sporadic",
            "dominance_ratio": 0.0,
            "cluster_counts": {},
            "total_sampled": 0,
            "is_obvious_junk": True
        }

    cluster_counts = {k: 0 for k in FORMAT_KEYWORDS}
    total_valid = 0

    for r in reels:
        cap = (r.get("caption") or "").lower()
        tags = [str(t).lower() for t in (r.get("hashtags") or [])]
        combined = f"{cap} {' '.join(tags)}"

        matched_any = False
        for fmt, kws in FORMAT_KEYWORDS.items():
            if any(re.search(r"\b" + re.escape(kw) + r"\b", combined) for kw in kws):
                cluster_counts[fmt] += 1
                matched_any = True

        if matched_any:
            total_valid += 1

    sorted_clusters = sorted(cluster_counts.items(), key=lambda x: x[1], reverse=True)
    top_cluster, top_count = sorted_clusters[0]

    dominance_ratio = (top_count / len(reels)) if reels else 0.0

    # Obvious junk if under 20% pattern consensus across 5+ reels, or 0 matches
    is_obvious_junk = len(reels) >= 5 and dominance_ratio < 0.20 and top_count <= 1

    return {
        "dominant_format": top_cluster if top_count > 0 else "sporadic",
        "dominance_ratio": round(dominance_ratio, 2),
        "cluster_counts": {k: v for k, v in sorted_clusters if v > 0},
        "total_sampled": len(reels),
        "is_obvious_junk": is_obvious_junk
    }


def analyze_trend_reels(
    audio_id: Any,
    audio_title: str,
    audio_artist: str,
    supabase_client: Any,
    max_reels: int = 40
) -> Dict[str, Any]:
    """
    Forensic human-level pattern evaluation for an audio track:
    1. Fetches top reels from DB for audio_id.
    2. Runs deterministic pre-clustering.
    3. Calls Gemini 2.0 Flash to synthesize the exact creator use-case.
    4. Detects and flags discordant/junk audios without hallucination.
    """
    global _LAST_GEMINI_CALL_TIME

    if not audio_id:
        return {
            "used_for": "sporadic",
            "why_this_works": "Insufficient reel data to establish a verified viral creator pattern.",
            "used_for_note": "Sporadic usage across personal posts.",
            "is_coherent_pattern": False,
            "confidence": 0.1,
            "reels_analyzed": 0
        }

    # 1. Fetch top reels for this audio (sorted by view_count DESC, like_count DESC)
    try:
        res = (
            supabase_client.table("reels")
            .select("id,reel_id,caption,hashtags,view_count,like_count,hook_brief,format_patterns")
            .eq("audio_id", str(audio_id))
            .order("view_count", desc=True)
            .limit(max_reels)
            .execute()
        )
        reels = res.data or []
    except Exception as err:
        logger.warning(f"Error fetching reels for audio_id {audio_id}: {err}")
        reels = []

    if not reels:
        return {
            "used_for": "sporadic",
            "why_this_works": f"The track '{audio_title}' has no indexed reel evidence yet.",
            "used_for_note": "No reel evidence indexed.",
            "is_coherent_pattern": False,
            "confidence": 0.0,
            "reels_analyzed": 0
        }

    # Minimum Consensus Guardrail (N < 3 Anti-Hallucination Gate)
    # A recurring creator pattern requires multiple independent creator data points.
    # If fewer than 3 reels are indexed, an isolated spam post or hashtag
    # (e.g. #fashionreels on a spiritual recitation) must NOT hijack the entire audio's classification.
    if len(reels) < 3:
        logger.info(
            f"Audio {audio_id} ('{audio_title}') has insufficient sample evidence (N={len(reels)} < 3). "
            "Defaulting to sporadic to prevent single-post hashtag hijacking."
        )
        return {
            "used_for": "sporadic",
            "why_this_works": "Insufficient reel evidence (N<3) to establish a recurring creator format.",
            "used_for_note": "Early / sporadic usage across isolated posts.",
            "actionable_creator_brief": "Early audio without an established viral format yet.",
            "is_coherent_pattern": False,
            "confidence": 0.20,
            "reels_analyzed": len(reels)
        }

    # 2. Heuristic Pre-clustering
    pre_result = pre_cluster_reels(reels)
    if pre_result["is_obvious_junk"] and len(reels) >= 8:
        logger.info(f"Audio {audio_id} ('{audio_title}') flagged as obvious junk via pre-cluster.")
        return {
            "used_for": "sporadic",
            "why_this_works": "Sampled reels show completely discordant themes with zero common creator trend or viral editing format.",
            "used_for_note": "Sporadic usage with no viral trend pattern.",
            "is_coherent_pattern": False,
            "confidence": 0.25,
            "reels_analyzed": len(reels)
        }

    # 3. Compact reel evidence digest for Gemini
    reel_lines = []
    for idx, r in enumerate(reels[:25], start=1):
        clean_cap = _clean_caption(r.get("caption"))
        tags = _filter_hashtags(r.get("hashtags"))
        v_count = r.get("view_count") or 0
        l_count = r.get("like_count") or 0

        line = f"Reel #{idx} ({v_count:,} views, {l_count:,} likes): "
        if clean_cap:
            line += f'"{clean_cap}" '
        if tags:
            line += f"[tags: {', '.join(tags)}]"
        reel_lines.append(line.strip())

    evidence_digest = "\n".join(reel_lines)

    # 4. Strict Gemini 2.0 Flash Analytical Prompt
    system_prompt = (
        "You are a cynical, forensic social media trend auditor.\n"
        "Your task: Determine what creators are ACTUALLY using this Instagram audio for by inspecting real sampled reels.\n\n"
        "CRITICAL RULES:\n"
        "1. DO NOT invent psychological theories, vague cultural essays, or fake reasons.\n"
        "2. Ground your analysis strictly in the provided reel captions, editing patterns, and tags.\n"
        "3. Allowed categories for 'used_for':\n"
        "   - transition: Beat drops, CapCut templates, fast cuts, glow-up reveals\n"
        "   - dance: Dance routines, choreography challenges, sync steps\n"
        "   - outfit-showcase: Fashion lookbooks, OOTD reveals, GRWM styling, haul showcases\n"
        "   - meme: Relatable humor, POV scenarios, funny dialogue skits\n"
        "   - fitness: Gym PR lifts, physique checks, workout clips\n"
        "   - travel: Scenic travel montages, roadtrip vlogs, drone scenery\n"
        "   - voiceover: Background audio for deep quotes, reflective thoughts, aesthetic b-roll\n"
        "   - tutorial: Step-by-step cooking, beauty hacks, educational guides\n"
        "   - sporadic: NO coherent pattern. The sampled reels are random discordant clips (news, personal selfies, bot spam).\n"
        "4. JUNK DETECTION: If the reels are mixed random posts with no recurring format, you MUST return 'sporadic' with is_coherent_pattern=false.\n"
        "5. Output ONLY valid JSON with these EXACT keys:\n"
        "   {\n"
        '     "used_for": "category",\n'
        '     "why_this_works": "1 concise sentence explaining the exact visual edit or hook that makes this work.",\n'
        '     "used_for_note": "Crisp creator summary (max 12 words).",\n'
        '     "actionable_creator_brief": "Specific 1-line direction of what a creator should film.",\n'
        '     "is_coherent_pattern": true,\n'
        '     "confidence": 0.85\n'
        "   }"
    )

    user_prompt = f"""
Track: "{audio_title}" by {audio_artist}
Total Sampled Reels: {len(reels)}
Pre-Clustered Signal: Dominant theme '{pre_result['dominant_format']}' ({int(pre_result['dominance_ratio']*100)}% consensus)

SAMPLE REEL EVIDENCE (sorted by views):
{evidence_digest}

Analyze what this audio is actually being used for. If it's discordant random posts, return 'sporadic'.
"""

    gemini_keys = _get_gemini_keys()
    parsed_result = None

    if gemini_keys:
        for attempt in range(2):
            for gkey in list(gemini_keys):
                try:
                    # Enforce strict 3.0s delay between calls for 15 RPM guardrail
                    now = time.time()
                    elapsed = now - _LAST_GEMINI_CALL_TIME
                    if elapsed < MIN_CALL_INTERVAL_SECONDS:
                        time.sleep(MIN_CALL_INTERVAL_SECONDS - elapsed)

                    resp = call_gemini(
                        system_prompt,
                        user_prompt,
                        gemini_key=gkey,
                        response_mime_type="application/json",
                        timeout=12,
                        model=TARGET_GEMINI_MODEL
                    )
                    _LAST_GEMINI_CALL_TIME = time.time()

                    if isinstance(resp, str):
                        try:
                            parsed_result = json.loads(resp)
                        except Exception:
                            parsed_result = None
                    elif isinstance(resp, dict):
                        parsed_result = resp

                    if parsed_result:
                        break
                except Exception as err:
                    logger.warning(f"Gemini call error on audio {audio_id}: {err}")
                    if "429" in str(err) or "RESOURCE_EXHAUSTED" in str(err):
                        if gkey in gemini_keys:
                            gemini_keys.remove(gkey)
                            gemini_keys.append(gkey)
                        time.sleep(2.0)
            if parsed_result:
                break

    # If Gemini returns valid payload
    if parsed_result and isinstance(parsed_result, dict):
        parsed_result["reels_analyzed"] = len(reels)
        return parsed_result

    # Safe deterministic fallback if Gemini unavailable
    dom = pre_result["dominant_format"]
    if dom != "sporadic" and pre_result["dominance_ratio"] >= 0.35:
        return {
            "used_for": dom,
            "why_this_works": f"Creators consistently use this sound for {dom} formats based on sampled reel patterns.",
            "used_for_note": f"Trending for {dom} edits and reels.",
            "actionable_creator_brief": f"Film a high-retention {dom} clip matching the audio rhythm.",
            "is_coherent_pattern": True,
            "confidence": 0.65,
            "reels_analyzed": len(reels)
        }

    return {
        "used_for": "sporadic",
        "why_this_works": "Audio is used sporadically across unrelated personal clips with no clear viral creator pattern.",
        "used_for_note": "Sporadic usage across mixed personal posts.",
        "actionable_creator_brief": "No established viral format exists yet.",
        "is_coherent_pattern": False,
        "confidence": 0.3,
        "reels_analyzed": len(reels)
    }
