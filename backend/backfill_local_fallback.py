"""
P-LLM-1: Backfill existing pending/llm_unavailable trends to skipped_local_fallback.
One-time migration. Safe to re-run (idempotent).
"""
import os
import sys
import logging
from dotenv import load_dotenv
from supabase import create_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

TARGET_STATUSES = ["pending", "llm_unavailable"]
BATCH_SIZE = 100


def local_defaults(trend: dict) -> dict:
    title = trend.get("audio_title") or "this track"
    return {
        "why_this_works": f"The track {title} is currently driving high engagement on short-form feeds.",
        "audio_cue_second": 0,
        "format_transferable": True,
        "transfer_instructions": f"Adapt the visual style of {title} to your niche.",
    }


def main():
    total_updated = 0

    for status in TARGET_STATUSES:
        offset = 0
        while True:
            batch = (
                sb.table("trends")
                .select("id,audio_title,why_this_works,audio_cue_second,format_transferable,transfer_instructions")
                .eq("llm_classification_status", status)
                .range(offset, offset + BATCH_SIZE - 1)
                .execute()
                .data
                or []
            )

            if not batch:
                break

            updates = []
            for t in batch:
                defaults = local_defaults(t)
                update = {"llm_classification_status": "skipped_local_fallback"}
                # Only overwrite fields that are NULL/empty (don't clobber existing data)
                if not t.get("why_this_works"):
                    update["why_this_works"] = defaults["why_this_works"]
                if t.get("audio_cue_second") is None:
                    update["audio_cue_second"] = 0
                if t.get("format_transferable") is None:
                    update["format_transferable"] = True
                if not t.get("transfer_instructions"):
                    update["transfer_instructions"] = defaults["transfer_instructions"]
                updates.append((t["id"], update))

            for tid, upd in updates:
                try:
                    sb.table("trends").update(upd).eq("id", tid).execute()
                    total_updated += 1
                except Exception as e:
                    logger.error(f"Failed to update trend {tid}: {e}")

            logger.info(f"[{status}] Processed batch {offset}-{offset+len(batch)-1} ({len(batch)} trends)")
            offset += BATCH_SIZE

    logger.info(f"Done. Total updated: {total_updated}")


if __name__ == "__main__":
    main()
