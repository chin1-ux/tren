import os, sys, logging
from datetime import datetime, timezone, timedelta
from supabase import create_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sweep")

ACTIVE = ("emerging", "rising", "peaked", "resurging")
FALLBACK_NOTE = "Automated fallback classification."

def main():
    limit = int(os.getenv("LIMIT", "30"))
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    now = datetime.now(timezone.utc)
    week = (now - timedelta(days=7)).isoformat()
    six_h = (now - timedelta(hours=6)).isoformat()

    # 1. Preflight: if Gemini (production path) is down, touch nothing and fail loudly
    try:
        from llm import call_gemini_only
        r = call_gemini_only("Return only JSON.", 'Return {"ok": true}', timeout=20)
        if not r:
            raise RuntimeError("empty")
    except Exception as e:
        log.error("Gemini preflight failed: %s", type(e).__name__)
        sys.exit(1)

    # 2. Select: active, last 7 days, never successfully classified, newest first
    rows = (sb.table("trends").select("id").in_("status", ACTIVE)
            .is_("used_for_classified_at", "null").gt("created_at", week)
            .order("created_at", desc=True).limit(limit).execute().data or [])
    ids = [r["id"] for r in rows]
    log.info("selected=%d ids=%s", len(ids), ids)

    # 3. Classify with the private repo's existing code
    if ids:
        from cron_auto_classifier import auto_classify_trends
        res = auto_classify_trends(ids) or {}
        log.info("result=%s", {k: v for k, v in res.items() if isinstance(v, (int, float))})

        # 4. Don't leave the placeholder text on cards for rows that fell back this run
        fb = (sb.table("trends").select("id").in_("id", ids)
              .eq("used_for_note", FALLBACK_NOTE).is_("used_for_classified_at", "null")
              .execute().data or [])
        fb_ids = [r["id"] for r in fb]
        if fb_ids:
            sb.table("trends").update({"used_for": None, "used_for_note": None}).in_("id", fb_ids).execute()
        log.warning("fallback_reverted=%d ids=%s", len(fb_ids), fb_ids)

    # 5. Health check: anything active, recent and still unclassified after 6h fails the run
    stale = (sb.table("trends").select("id", count="exact").in_("status", ACTIVE)
             .is_("used_for_classified_at", "null").gt("created_at", week)
             .lt("created_at", six_h).execute())
    n = stale.count or 0
    log.info("stale_gt_6h=%d", n)
    if n > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
