"""
Backfill language_final for active trends (rising, emerging, resurging, peaked).
Checks audio_language_overrides first by audio_id, then calls classify_audio (Gemini only).
No Golden Checkpoint files touched.
"""
import os
import sys
import time
import random
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

    t_start = time.time()
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
        .select("*")
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
    sample_audit_rows = []

    for idx, row in enumerate(rows, start=1):
        tid = row["id"]
        audio_id = row.get("audio_id")
        title = row.get("audio_title") or row.get("original_audio_title") or row.get("title") or ""
        artist = row.get("audio_artist") or row.get("original_audio_artist") or row.get("artist") or ""
        captions = row.get("sample_captions") or ""
        old_lang = row.get("language")

        lang_final = None
        lang_conf = 0.0
        lang_source = None

        # Check overrides first
        if audio_id and audio_id in overrides_map:
            lang_final = overrides_map[audio_id]
            lang_conf = 1.0
            lang_source = "override"
        else:
            try:
                cl = classify_audio(title, artist, captions)
                l_res = cl.get("language")
                c_res = cl.get("confidence", 0.0)
                pm_res = cl.get("provider_model") or "gemini/gemini-3.8-flash"

                if l_res and l_res != "unknown" and "failed" not in pm_res:
                    lang_final = l_res
                    lang_conf = c_res
                    lang_source = pm_res
                else:
                    # Fallback to old language column if Gemini call was rate limited or failed
                    if old_lang and old_lang != "unknown":
                        lang_final = old_lang
                        lang_conf = 0.60
                        lang_source = "fallback/old-language-column"
                    else:
                        lang_final = "other"
                        lang_conf = 0.50
                        lang_source = "fallback/default-other"
            except Exception as ex:
                logger.warning(f"Error classifying trend {tid}: {ex}")
                if old_lang and old_lang != "unknown":
                    lang_final = old_lang
                    lang_conf = 0.60
                    lang_source = "fallback/old-language-column"

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
                
                sample_audit_rows.append({
                    "id": tid,
                    "title": title,
                    "artist": artist,
                    "old_language": old_lang,
                    "language_final": lang_final,
                    "confidence": lang_conf
                })
                print(f"[{idx}/{total}] Classified trend {tid}: '{title[:25]}' -> {lang_final} (conf: {lang_conf:.2f}, source: {lang_source})", flush=True)
            except Exception as ue:
                logger.error(f"Failed to update DB for trend {tid}: {ue}")
                failure_count += 1
        else:
            failure_count += 1
            print(f"[{idx}/{total}] Trend ID {tid} left NULL (unclassified)", flush=True)

        time.sleep(0.1)

    duration = time.time() - t_start
    print("\n=== BACKFILL COMPLETED ===", flush=True)
    print(f"Total Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)", flush=True)
    print(f"Total Processed (Successfully Classified & Updated): {processed_count}", flush=True)
    print(f"Failures (Left NULL): {failure_count}", flush=True)
    print("\nCounts by language_final:", flush=True)
    for l_code, count in sorted(language_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {l_code}: {count}", flush=True)

    # Print 20 random sample rows
    print("\n=== 20 RANDOM SAMPLE ROWS AUDIT ===", flush=True)
    sample_size = min(20, len(sample_audit_rows))
    random_samples = random.sample(sample_audit_rows, sample_size) if sample_audit_rows else []
    for idx, s in enumerate(random_samples, 1):
        print(f"  {idx:2d}. ID: {s['id']:<5} | Title: '{s['title']:<30}' | Artist: '{s['artist']:<20}' | Old Lang: '{s['old_language']}' | language_final: '{s['language_final']}' | Confidence: {s['confidence']:.2f}", flush=True)

if __name__ == "__main__":
    run_backfill()
