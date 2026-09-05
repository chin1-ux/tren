"""
A6 backfill: Reclassify 40 trend rows that have hashtag pool names as niche_tag/content_type.
Pool names (INDIA_VERNACULAR, GLOBAL_DISCOVERY, etc.) are internal routing labels, not real niches.
This script reclassifies them using classify_niche() and adds a defensive guard.
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

POOL_NAMES = {"INDIA_VERNACULAR", "GLOBAL_DISCOVERY", "INDIA_TRENDING", "GLOBAL_NICHES",
              "india_vernacular", "global_discovery", "india_trending", "global_niches"}

# Import classify_niche from the shared module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from classification_rules import classify_niche


def main():
    # Fetch all trends with pool-name niche_tag or content_type
    res = sb.table("trends").select("id, audio_title, niche_tag, content_type, sample_captions").execute()
    rows = res.data or []
    hits = [r for r in rows if r.get("niche_tag") in POOL_NAMES or r.get("content_type") in POOL_NAMES]

    logger.info(f"Found {len(hits)} trends with pool-name niche_tag/content_type out of {len(rows)} total")

    if not hits:
        logger.info("Nothing to fix")
        return

    fixed = 0
    for h in hits:
        tid = h["id"]
        title = h.get("audio_title", "")
        old_niche = h.get("niche_tag", "")
        old_content = h.get("content_type", "")
        sample = h.get("sample_captions", "")

        # Reclassify using sample_captions as caption input
        new_niche = classify_niche(sample, [], source_hashtag_pool=None, sample_size=5)
        if new_niche in POOL_NAMES or not new_niche:
            new_niche = "general"

        # Map backend niche to frontend canonical form
        from api_globals import CONTENT_TYPE_NORMALIZE
        new_content = CONTENT_TYPE_NORMALIZE.get(new_niche, new_niche)

        logger.info(f"  id={tid} '{title[:40]}' niche: {old_niche} -> {new_niche}, content_type: {old_content} -> {new_content}")

        try:
            sb.table("trends").update({
                "niche_tag": new_niche,
                "content_type": new_content,
            }).eq("id", tid).execute()
            fixed += 1
        except Exception as e:
            logger.error(f"  Failed to update trend {tid}: {e}")

    logger.info(f"Done. Fixed {fixed}/{len(hits)} trends.")


if __name__ == "__main__":
    main()
