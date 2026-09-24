"""
Backfill language_final for active trends (rising, emerging, resurging, peaked).
Checks audio_language_overrides first by audio_id, then calls classify_audio (Gemini only).
No Golden Checkpoint files touched.
"""
import os
import sys
import time
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
backend_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(backend_dir, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

os.environ["JWT_SECRET_KEY"] = "testsecret12345678901234567890123456789012"
sys.path.insert(0, backend_dir)

from api_globals import supabase
from language_classifier import classify_audio

logger = logging.getLogger("backfill_language")

def run_backfill():
    if not supabase:
        print("Error: Supabase client not initialized.", file=sys.stderr)
        return

    print("=== BACKFILL LANGUAGE CLASSIFICATION START ===", flush=True)

    # 1. Load audio language overrides into memory
    overrides_map = {}
    try:
        ov_res = supabase.table("audio_language_overrides").select("audio_id, language").execute()
        if ov_res.data:
            for item in ov_res.data:
                if item.get("audio_id") and item.get("language"):
                    overrides_map[item["audio_id"]] = item["language"]
        print(f"Loaded {len(overrides_map)} audio language override(s).", flush=True)
    except Exception as e:
        print(f"Note: Could not query audio_language_overrides: {e}", flush=True)

    # 2. Query active trends with language_final IS NULL
    query = (
        supabase.table("trends")
        .select("id, audio_id, audio_title, audio_artist, language, sample_captions, status")
        .in_("status", ["rising", "emerging", "resurging", "peaked"])
        .is_("language_final", "null")
    )
    res = query.execute()
    rows = res.data or []
    total = len(rows)
    print(f"Found {total} active trend(s) requiring language classification.", flush=True)

    processed_count = 0
    failure_count = 0
    language_counts = {}

    for idx, row in enumerate(rows, start=1):
        tid = row["id"]
        audio_id = row.get("audio_id")
        title = row.get("audio_title") or ""
        artist = row.get("audio_artist") or ""
        captions = row.get("sample_captions") or ""

        lang_final = None
        lang_conf = 0.0
        lang_source = None

        # Check overrides first
        if audio_id and audio_id in overrides_map:
            lang_final = overrides_map[audio_id]
            lang_conf = 1.0
            lang_source = "override"
        else:
            # Call classify_audio (Gemini 3.5 Flash only, with retry logic inside)
            try:
                cl = classify_audio(title, artist, captions)
                l_res = cl.get("language")
                c_res = cl.get("confidence", 0.0)
                pm_res = cl.get("provider_model") or "gemini/gemini-3.5-flash"

                if l_res and l_res != "unknown":
                    lang_final = l_res
                    lang_conf = c_res
                    lang_source = pm_res
                else:
                    # If classified as unknown or failed, retry once
                    time.sleep(2.0)
                    cl_retry = classify_audio(title, artist, captions)
                    l_retry = cl_retry.get("language")
                    if l_retry and l_retry != "unknown":
                        lang_final = l_retry
                        lang_conf = cl_retry.get("confidence", 0.0)
                        lang_source = cl_retry.get("provider_model") or "gemini/gemini-3.5-flash"
            except Exception as ex:
                logger.warning(f"Error classifying trend {tid}: {ex}")

        now_iso = datetime.now(timezone.utc).isoformat()

        if lang_final:
            try:
                update_payload = {
                    "language_final": lang_final,
                    "language_confidence": lang_conf,
                    "language_source": lang_source,
                    "language_classified_at": now_iso
                }
                supabase.table("trends").update(update_payload).eq("id", tid).execute()
                processed_count += 1
                language_counts[lang_final] = language_counts.get(lang_final, 0) + 1
            except Exception as ue:
                logger.error(f"Failed to update DB for trend {tid}: {ue}")
                failure_count += 1
        else:
            failure_count += 1
            print(f"[{idx}/{total}] Trend ID {tid} left NULL (unclassified)", flush=True)

        # Sleep between requests to respect rate limits
        time.sleep(3.0)

    print("\n=== BACKFILL COMPLETED ===", flush=True)
    print(f"Total Processed (Successfully Classified & Updated): {processed_count}", flush=True)
    print(f"Failures (Left NULL): {failure_count}", flush=True)
    print("Counts by language_final:", flush=True)
    for l_code, count in sorted(language_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {l_code}: {count}", flush=True)

if __name__ == "__main__":
    run_backfill()
