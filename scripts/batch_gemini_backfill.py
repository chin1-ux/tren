import sys
import os
import json
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend')
sys.path.insert(0, backend_dir)
env_path = os.path.join(backend_dir, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

from api_globals import supabase
from llm import call_llm
from artist_language_map import get_artist_language

ALLOWED_LANGUAGES = {
    "hi", "pa", "ta", "te", "kn", "ml", "mr", "bn", "gu", "ne",
    "en", "es", "pt", "ko", "instrumental", "other", "unknown"
}

def clean_captions(sample_captions):
    if not sample_captions:
        return ""
    if isinstance(sample_captions, list):
        text = " ".join([str(c) for c in sample_captions if c])
    else:
        text = str(sample_captions)
    text = text.replace("\n", " ").strip()
    return text[:150]

def run_order_26_backfill():
    out = []
    out.append("=== ORDER 26: BATCHED LLM & ARTIST MAP COMPLETION PASS ===")
    
    # 1. Select all target rows: active trends that are fallback OR language_source/language_final is NULL
    res = supabase.table("trends").select(
        "id, audio_title, audio_artist, sample_captions, language, language_final, language_source"
    ).in_("status", ["rising", "emerging", "resurging", "peaked"]).execute()

    all_rows = res.data or []
    target_rows = []
    for r in all_rows:
        ls = r.get("language_source")
        lf = r.get("language_final")
        if ls == "fallback/old-language-column" or ls is None or lf is None:
            target_rows.append(r)

    total_target = len(target_rows)
    out.append(f"Total target active trends to process: {total_target}")

    if not target_rows:
        out.append("No target trends require processing!")
        print("\n".join(out))
        return

    now_iso = datetime.now(timezone.utc).isoformat()
    
    # Step A: First apply static artist_language_map to any target rows
    artist_map_resolved = 0
    unresolved_target_rows = []

    for r in target_rows:
        artist = str(r.get("audio_artist") or "").strip()
        mapped_lang = get_artist_language(artist)
        if mapped_lang:
            try:
                payload = {
                    "language_final": mapped_lang,
                    "language_confidence": 0.90,
                    "language_source": "artist-map",
                    "language_classified_at": now_iso
                }
                supabase.table("trends").update(payload).eq("id", r["id"]).execute()
                artist_map_resolved += 1
            except Exception as e:
                out.append(f"Failed to update artist-map for trend {r['id']}: {e}")
                unresolved_target_rows.append(r)
        else:
            unresolved_target_rows.append(r)

    out.append(f"Resolved via artist-map: {artist_map_resolved}")
    out.append(f"Remaining rows requiring Batched LLM classification: {len(unresolved_target_rows)}")

    if not unresolved_target_rows:
        out.append("All target rows resolved via artist-map!")
        print("\n".join(out))
        return

    # Step B: Process remaining unresolved rows in batches of 10 with verification & 2 retries
    system_prompt = (
        "You are an expert music and vocal language classifier.\n"
        "Your sole task: Classify the SUNG vocal language of each audio track in the provided batch.\n\n"
        "CRITICAL RULES:\n"
        "1. Classify the language of the vocal lyrics/singing, using title, artist, and creator caption/hashtag cues.\n"
        "2. Allowed language codes (MUST use exact 2-letter ISO or allowed string):\n"
        "   - hi: Hindi\n"
        "   - pa: Punjabi\n"
        "   - ta: Tamil\n"
        "   - te: Telugu\n"
        "   - kn: Kannada\n"
        "   - ml: Malayalam\n"
        "   - mr: Marathi\n"
        "   - bn: Bengali\n"
        "   - gu: Gujarati\n"
        "   - ne: Nepali\n"
        "   - en: English\n"
        "   - es: Spanish (Latin / Reggaeton)\n"
        "   - pt: Portuguese (Brazilian Funk / Portuguese)\n"
        "   - ko: Korean (K-pop)\n"
        "   - instrumental: Audio with NO vocal lyrics\n"
        "   - other: Vocal lyrics present in a language not listed above\n"
        "   - unknown: Unsure or insufficient data\n"
        "3. You MUST return an entry for EVERY SINGLE input track in the batch.\n"
        "4. Output MUST be a JSON array of objects with EXACT keys:\n"
        '   [{"id": 1234, "language": "code", "confidence": 0.85, "vocal_evidence": "reason"}]\n'
    )

    batch_size = 10
    total_llm_updated = 0
    hard_failures = []

    # Queue of items to process: list of row dicts
    queue = list(unresolved_target_rows)
    
    # Track attempt count for each ID
    attempts = {r["id"]: 0 for r in queue}
    row_by_id = {r["id"]: r for r in queue}

    batch_num = 0
    while queue:
        batch_num += 1
        current_batch = queue[:batch_size]
        queue = queue[batch_size:]

        sent_ids = set()
        batch_input = []
        for r in current_batch:
            tid = r["id"]
            attempts[tid] += 1
            sent_ids.add(tid)
            batch_input.append({
                "id": tid,
                "title": r.get("audio_title") or "",
                "artist": r.get("audio_artist") or "",
                "captions": clean_captions(r.get("sample_captions"))
            })

        user_prompt = (
            f"Classify the vocal language of these {len(batch_input)} tracks (Return JSON array with ALL {len(batch_input)} IDs):\n"
            + json.dumps(batch_input, indent=2)
            + "\nReturn ONLY a JSON array of objects."
        )

        res_json = None
        try:
            time.sleep(0.5)
            res_json = call_llm(system_prompt, user_prompt, response_mime_type="application/json", timeout=30)
        except Exception as e:
            out.append(f"Batch {batch_num} API call error: {e}")

        if isinstance(res_json, dict):
            if "items" in res_json and isinstance(res_json["items"], list):
                res_json = res_json["items"]
            elif "trends" in res_json and isinstance(res_json["trends"], list):
                res_json = res_json["trends"]
            elif "id" in res_json:
                res_json = [res_json]

        returned_ids = set()
        batch_updated = 0

        if isinstance(res_json, list):
            for item in res_json:
                if not isinstance(item, dict):
                    continue
                tid = item.get("id")
                if tid is None:
                    continue
                try:
                    tid = int(tid)
                except ValueError:
                    pass

                if tid in sent_ids:
                    returned_ids.add(tid)
                    lang = str(item.get("language") or "unknown").lower().strip()
                    conf = item.get("confidence", 0.85)

                    if lang not in ALLOWED_LANGUAGES:
                        lang = "other"

                    try:
                        payload = {
                            "language_final": lang,
                            "language_confidence": float(conf),
                            "language_source": "gemini-batch/gemini-3.8-flash",
                            "language_classified_at": now_iso
                        }
                        supabase.table("trends").update(payload).eq("id", tid).execute()
                        batch_updated += 1
                    except Exception as ue:
                        out.append(f"Failed to update trend {tid}: {ue}")

        total_llm_updated += batch_updated
        missing_ids = sent_ids - returned_ids

        if missing_ids:
            out.append(f"[Batch {batch_num}] Sent {len(sent_ids)}, Updated {batch_updated}, Missing {len(missing_ids)} IDs.")
            # Handle missing IDs: retry if attempt < 3, else hard failure
            for mid in missing_ids:
                if attempts[mid] < 3:
                    queue.append(row_by_id[mid])
                    out.append(f"  -> Retrying ID {mid} (Attempt {attempts[mid] + 1}/3)")
                else:
                    hard_failures.append(mid)
                    out.append(f"  -> HARD FAILURE: ID {mid} failed after 3 attempts.")
        else:
            out.append(f"[Batch {batch_num}] 1:1 SUCCESS! Sent {len(sent_ids)}, Updated {batch_updated}/10 tracks.")

    out.append("\n=== EXECUTION SUMMARY ===")
    out.append(f"Total Target Rows Evaluated : {total_target}")
    out.append(f"Total Resolved via Artist Map: {artist_map_resolved}")
    out.append(f"Total Resolved via LLM Batch : {total_llm_updated}")
    out.append(f"Total Hard Failures          : {len(hard_failures)}")
    if hard_failures:
        out.append(f"Hard Failure IDs: {hard_failures}")

    # Step C: Final Canonical Audit Query across all active trends
    audit_res = supabase.table("trends").select(
        "id, language_final, language_source"
    ).in_("status", ["rising", "emerging", "resurging", "peaked"]).execute()

    audit_data = audit_res.data or []
    audit_total = len(audit_data)

    langs_audit = {}
    sources_audit = {}
    unnormalized_audit = []
    fallback_audit = []

    for r in audit_data:
        lf = r.get("language_final")
        ls = r.get("language_source")
        
        lf_str = str(lf) if lf is not None else "<NULL>"
        ls_str = str(ls) if ls is not None else "<NULL>"
        
        langs_audit[lf_str] = langs_audit.get(lf_str, 0) + 1
        sources_audit[ls_str] = sources_audit.get(ls_str, 0) + 1

        if lf in ["latin", "korean", "brazilian"]:
            unnormalized_audit.append(r)
        if ls == "fallback/old-language-column":
            fallback_audit.append(r)

    out.append("\n=== FINAL CANONICAL AUDIT REPORT (ALL ACTIVE TRENDS) ===")
    out.append(f"Total Active Trends Evaluated: {audit_total}\n")

    out.append("Counts by language_final:")
    for l, c in sorted(langs_audit.items(), key=lambda x: x[1], reverse=True):
        out.append(f"  {l:<15}: {c}")

    out.append("\nCounts by language_source:")
    for s, c in sorted(sources_audit.items(), key=lambda x: x[1], reverse=True):
        out.append(f"  {s:<35}: {c}")

    out.append(f"\nUnnormalized rows remaining ('latin', 'korean', 'brazilian'): {len(unnormalized_audit)}")
    out.append(f"Fallback source rows remaining ('fallback/old-language-column'): {len(fallback_audit)}")

    out_text = "\n".join(out)
    print(out_text, flush=True)

    with open("scripts/order_26_report.txt", "w", encoding="utf-8") as f:
        f.write(out_text)

if __name__ == "__main__":
    run_order_26_backfill()
