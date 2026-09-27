"""
cron_auto_classifier.py
------------------------
Auto-classification hook and safety-net for language_final and used_for tags.
Used by cron_job.py inline after trend creation, and as a background safety net pass.

Allowed Languages: hi, pa, ta, te, kn, ml, mr, bn, gu, ne, en, es, pt, ko, instrumental, other
Allowed Used-For: quote / text overlay, motivational vlog, dance transition, comedy skit,
                 travel / scenic, fashion / beauty, food / recipe, devotional / festival,
                 lip sync, fitness / gym, general / unknown
"""

import os
import sys
import json
import logging
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, ".env"))

from supabase import create_client
from artist_language_map import get_artist_language
from llm import call_llm

logger = logging.getLogger("cron_auto_classifier")

ALLOWED_LANGUAGES = {
    "hi", "pa", "ta", "te", "kn", "ml", "mr", "bn", "gu", "ne",
    "en", "es", "pt", "ko", "instrumental", "other"
}

ALLOWED_USED_FOR = {
    "quote / text overlay",
    "motivational vlog",
    "dance transition",
    "comedy skit",
    "travel / scenic",
    "fashion / beauty",
    "food / recipe",
    "devotional / festival",
    "lip sync",
    "fitness / gym",
    "general / unknown"
}

def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    return create_client(url, key)


def classify_languages_batch(trends: List[Dict[str, Any]]) -> Dict[int, str]:
    """
    Classify language for a batch of trends.
    First uses artist_language_map (0 API cost), then batches remaining through Gemini.
    Returns map of trend_id -> language_code.
    """
    results: Dict[int, str] = {}
    unresolved: List[Dict[str, Any]] = []

    # 1. Artist Map Pass
    for t in trends:
        tid = t["id"]
        artist = t.get("audio_artist") or ""
        mapped = get_artist_language(artist)
        if mapped and mapped in ALLOWED_LANGUAGES:
            results[tid] = mapped
        else:
            unresolved.append(t)

    if not unresolved:
        return results

    # 2. Gemini Batched Classifier Pass (batch size 10)
    for i in range(0, len(unresolved), 10):
        batch = unresolved[i:i + 10]
        items_payload = []
        for item in batch:
            items_payload.append({
                "id": item["id"],
                "title": item.get("audio_title") or "",
                "artist": item.get("audio_artist") or "",
                "sample_captions": item.get("sample_captions") or "(none)"
            })

        system_prompt = "You are a multilingual audio language classifier for Indian social media trends. Return ONLY valid JSON. No markdown wrappers."
        user_prompt = f"""
Classify the dominant spoken/singing language for each audio track in this list.

Allowed Language Codes: {sorted(list(ALLOWED_LANGUAGES))}

Input Items:
{json.dumps(items_payload, ensure_ascii=False, indent=2)}

Return ONLY a JSON object with this EXACT structure:
{{
  "classifications": [
    {{ "id": 123, "language": "hi" }},
    ...
  ]
}}
Rules:
- MUST include an entry for every input item ID.
- Choose ONLY from allowed language codes.
- Use "instrumental" for tracks without lyrics/vocals.
- Use "other" for languages not in the list.
"""
        try:
            resp = call_llm(system_prompt, user_prompt, timeout=15)
            if isinstance(resp, str):
                try:
                    resp = json.loads(resp)
                except Exception:
                    resp = {}
            if isinstance(resp, list) and len(resp) > 0:
                resp = resp[0]
            
            classifications = resp.get("classifications", []) if isinstance(resp, dict) else []
            for c in classifications:
                if isinstance(c, dict):
                    cid = c.get("id")
                    lang = str(c.get("language") or "").lower().strip()
                    if cid and lang in ALLOWED_LANGUAGES:
                        results[cid] = lang

            # Retry missing IDs in batch
            missing = [item for item in batch if item["id"] not in results]
            if missing:
                for m_item in missing:
                    results[m_item["id"]] = "en" # Default fallback for unclassified
        except Exception as err:
            logger.warning(f"Language batch Gemini call failed: {err}")
            for item in batch:
                if item["id"] not in results:
                    results[item["id"]] = "en"

    return results


def classify_used_for_batch(trends: List[Dict[str, Any]]) -> Dict[int, Dict[str, str]]:
    """
    Classify used_for category and note for a batch of trends using Gemini.
    Returns map of trend_id -> {"used_for": tag, "used_for_note": note}.
    """
    results: Dict[int, Dict[str, str]] = {}

    for i in range(0, len(trends), 10):
        batch = trends[i:i + 10]
        items_payload = []
        for item in batch:
            items_payload.append({
                "id": item["id"],
                "title": item.get("audio_title") or "",
                "artist": item.get("audio_artist") or "",
                "sample_captions": item.get("sample_captions") or "(none)"
            })

        system_prompt = "You are a Instagram Reel format analyst. Return ONLY valid JSON. No markdown wrappers."
        user_prompt = f"""
Classify how creators are using each audio track in Instagram Reels based on title, artist, and sample captions.

Allowed Categories (choose EXACT string):
- "quote / text overlay"
- "motivational vlog"
- "dance transition"
- "comedy skit"
- "travel / scenic"
- "fashion / beauty"
- "food / recipe"
- "devotional / festival"
- "lip sync"
- "fitness / gym"
- "general / unknown"

Input Items:
{json.dumps(items_payload, ensure_ascii=False, indent=2)}

Return ONLY a JSON object with this EXACT structure:
{{
  "classifications": [
    {{
      "id": 123,
      "used_for": "quote / text overlay",
      "used_for_note": "Used primarily behind motivational quote text overlays."
    }},
    ...
  ]
}}
"""
        try:
            resp = call_llm(system_prompt, user_prompt, timeout=15)
            if isinstance(resp, str):
                try:
                    resp = json.loads(resp)
                except Exception:
                    resp = {}
            if isinstance(resp, list) and len(resp) > 0:
                resp = resp[0]

            classifications = resp.get("classifications", []) if isinstance(resp, dict) else []
            for c in classifications:
                if isinstance(c, dict):
                    cid = c.get("id")
                    tag = str(c.get("used_for") or "").strip()
                    note = str(c.get("used_for_note") or "").strip()
                    if cid:
                        if tag not in ALLOWED_USED_FOR:
                            tag = "general / unknown"
                        results[cid] = {"used_for": tag, "used_for_note": note}

            # Retry missing IDs in batch
            missing = [item for item in batch if item["id"] not in results]
            for m_item in missing:
                results[m_item["id"]] = {"used_for": "general / unknown", "used_for_note": "Automated default classification."}
        except Exception as err:
            logger.warning(f"used_for batch Gemini call failed: {err}")
            for item in batch:
                results[item["id"]] = {"used_for": "general / unknown", "used_for_note": "Automated fallback classification."}

    return results


def auto_classify_trends(trend_ids: List[int]) -> Dict[str, Any]:
    """
    Non-fatal helper to auto-classify new or unclassified trends.
    Updates Supabase in single batched calls per language group / used_for payload.
    """
    if not trend_ids:
        return {"processed": 0, "language_updated": 0, "used_for_updated": 0}

    sb = get_supabase()
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Fetch trend records
    res = sb.table("trends") \
        .select("id, audio_title, audio_artist, sample_captions, language_final, used_for") \
        .in_("id", trend_ids) \
        .execute()

    trends = res.data or []
    if not trends:
        return {"processed": 0, "language_updated": 0, "used_for_updated": 0}

    logger.info(f"Auto-classifying {len(trends)} trends: {trend_ids}")

    # 2. Language Classification
    lang_map = classify_languages_batch(trends)
    lang_updated_cnt = 0
    if lang_map:
        # Group IDs by language for batched updates
        by_lang = {}
        for tid, lcode in lang_map.items():
            by_lang.setdefault(lcode, []).append(tid)

        for lcode, tids in by_lang.items():
            try:
                sb.table("trends").update({
                    "language_final": lcode,
                    "language": lcode,
                    "llm_classification_status": "verified"
                }).in_("id", tids).execute()
                lang_updated_cnt += len(tids)
            except Exception as e:
                logger.warning(f"Failed to bulk update language={lcode} for IDs {tids}: {e}")

    # 3. Used-For Classification
    used_for_map = classify_used_for_batch(trends)
    used_for_updated_cnt = 0
    if used_for_map:
        for tid, data in used_for_map.items():
            try:
                sb.table("trends").update({
                    "used_for": data["used_for"],
                    "used_for_note": data["used_for_note"],
                    "used_for_classified_at": now_iso
                }).eq("id", tid).execute()
                used_for_updated_cnt += 1
            except Exception as e:
                logger.warning(f"Failed to update used_for for trend ID {tid}: {e}")

    logger.info(f"Auto-classification complete for {len(trends)} trends: language={lang_updated_cnt}, used_for={used_for_updated_cnt}")
    return {
        "processed": len(trends),
        "language_updated": lang_updated_cnt,
        "used_for_updated": used_for_updated_cnt
    }


def run_unclassified_safety_net_pass(limit: int = 50) -> Dict[str, Any]:
    """
    Safety net step: finds active trends with NULL language_final or NULL used_for
    and runs the auto-classifier against them.
    """
    sb = get_supabase()
    res = sb.table("trends") \
        .select("id") \
        .neq("status", "unqualified") \
        .or_("language_final.is.null,used_for.is.null") \
        .limit(limit) \
        .execute()

    rows = res.data or []
    if not rows:
        logger.info("Safety-net pass: 0 active unclassified trends found.")
        return {"processed": 0}

    unclassified_ids = [r["id"] for r in rows]
    logger.info(f"Safety-net pass: found {len(unclassified_ids)} unclassified active trends. Classifying...")
    return auto_classify_trends(unclassified_ids)
