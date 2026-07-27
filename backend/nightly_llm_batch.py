import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from llm import call_llm

load_dotenv()
if not os.getenv("SUPABASE_URL"):
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("nightly_llm_batch")

MAX_CALLS_PER_RUN = int(os.getenv("NIGHTLY_LLM_MAX_CALLS_PER_RUN", "5"))
BASE_DELAY_SECONDS = float(os.getenv("NIGHTLY_LLM_BASE_DELAY_SECONDS", "2.0"))
MAX_DELAY_SECONDS = float(os.getenv("NIGHTLY_LLM_MAX_DELAY_SECONDS", "20.0"))
MAX_RETRIES_PER_TREND = 3


def _sleep_backoff(attempt: int) -> None:
    delay = min(MAX_DELAY_SECONDS, BASE_DELAY_SECONDS * (2 ** (attempt - 1)))
    logger.info("Backoff sleeping %.1fs before retry %d", delay, attempt + 1)
    time.sleep(delay)


def _build_prompt(trend: dict) -> tuple[str, str]:
    system_prompt = "You are a social media trend analyst. Return ONLY valid JSON. No markdown."
    user_prompt = f"""
Classify this REAL social media trend for format transfer and posting strategy.

Audio: "{trend.get('audio_title')}" by {trend.get('audio_artist')}
Trend tone: {trend.get('content_tone')}
Trend niche: {trend.get('niche_tag')}
Sample captions: {trend.get('sample_captions') or ''}

Return ONLY a valid JSON object with EXACTLY these fields:
{{
  "optimal_post_hour_ist": 0,
  "format_transferable": true,
  "transfer_instructions": "one short sentence explaining how a creator in another niche can adapt this format"
}}
"""
    return system_prompt, user_prompt


def run_nightly_batch(limit: int | None = None) -> dict:
    load_dotenv()
    sb = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY"),
    )
    max_calls = min(limit or MAX_CALLS_PER_RUN, MAX_CALLS_PER_RUN)
    start = time.monotonic()
    processed = 0
    succeeded = 0
    unavailable = 0

    rows = (
        sb.table("trends")
        .select("id,audio_title,audio_artist,niche_tag,content_tone,llm_classification_status,optimal_post_hour_ist,format_transferable,transfer_instructions")
        .in_("llm_classification_status", ["pending", "llm_unavailable"])
        .order("first_detected_at", desc=False)
        .limit(max_calls)
        .execute()
        .data
        or []
    )
    logger.info("Nightly LLM batch starting: cap=%d rows_selected=%d", max_calls, len(rows))

    for trend in rows:
        processed += 1
        tid = trend["id"]
        title = trend.get("audio_title")
        system_prompt, user_prompt = _build_prompt(trend)
        result = None
        for attempt in range(1, MAX_RETRIES_PER_TREND + 1):
            try:
                logger.info("Trend %s (%s) attempt %d/%d", tid, title, attempt, MAX_RETRIES_PER_TREND)
                result = call_llm(system_prompt, user_prompt, timeout=12)
                break
            except Exception as err:
                logger.warning("Trend %s failed on attempt %d: %s", tid, attempt, err)
                if attempt < MAX_RETRIES_PER_TREND:
                    _sleep_backoff(attempt)
        if not result:
            unavailable += 1
            sb.table("trends").update({
                "llm_classification_status": "llm_unavailable",
                "llm_retry_count": (trend.get("llm_retry_count") or 0) + MAX_RETRIES_PER_TREND,
                "llm_classified_at": None,
                "raw_llm_response": None,
            }).eq("id", tid).execute()
            logger.info("Trend %s marked llm_unavailable", tid)
            continue

        update = {
            "optimal_post_hour_ist": int(result.get("optimal_post_hour_ist") or 18),
            "format_transferable": bool(result.get("format_transferable", False)),
            "transfer_instructions": result.get("transfer_instructions") or "",
            "llm_classification_status": "completed",
            "llm_classified_at": datetime.now(timezone.utc).isoformat(),
            "raw_llm_response": json.dumps(result, ensure_ascii=False),
        }
        sb.table("trends").update(update).eq("id", tid).execute()
        succeeded += 1
        logger.info("Trend %s completed", tid)

    elapsed = time.monotonic() - start
    summary = {
        "processed": processed,
        "succeeded": succeeded,
        "llm_unavailable": unavailable,
        "elapsed_seconds": round(elapsed, 2),
        "cap": max_calls,
    }
    logger.info("Nightly LLM batch complete: %s", summary)
    return summary


if __name__ == "__main__":
    run_nightly_batch()
