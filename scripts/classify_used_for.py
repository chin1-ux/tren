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
from llm import call_gemini_only

ALLOWED_USED_FOR = {
    "dance", "transition", "lip-sync", "meme", "voiceover",
    "outfit-showcase", "tutorial", "storytime", "other"
}

def clean_text(text, max_len=150):
    if not text:
        return ""
    if isinstance(text, list):
        text = " ".join([str(c) for c in text if c])
    else:
        text = str(text)
    text = text.replace("\n", " ").strip()
    return text[:max_len]

def run_used_for_classification():
    out = []
    out.append("=== ORDER 27: USED FOR BATCHED CLASSIFICATION START ===")

    # 1. Fetch active trends requiring classification (used_for is NULL)
    trends_res = supabase.table("trends").select(
        "id, audio_title, audio_artist, sample_captions, used_for"
    ).in_("status", ["rising", "emerging", "resurging", "peaked"]).execute()

    all_trends = trends_res.data or []
    target_trends = [r for r in all_trends if not r.get("used_for")]

    total_target = len(target_trends)
    out.append(f"Total active trends evaluated: {len(all_trends)}")
    out.append(f"Target active trends requiring classification (used_for is NULL): {total_target}")

    if not target_trends:
        out.append("All active trends already classified for used_for!")
        print("\n".join(out))
        return

    # 2. Batched fetch of reels for context across all target trends
    audio_titles = list(set([r["audio_title"] for r in target_trends if r.get("audio_title")]))
    reels_fetched = []
    chunk_size = 50
    for i in range(0, len(audio_titles), chunk_size):
        chunk = audio_titles[i:i + chunk_size]
        res = supabase.table("reels").select(
            "audio_title, audio_artist, caption, view_count"
        ).in_("audio_title", chunk).order("view_count", desc=True).limit(500).execute()
        if res.data:
            reels_fetched.extend(res.data)

    reels_by_track = {}
    for r in reels_fetched:
        key = (r.get("audio_title"), r.get("audio_artist"))
        if key not in reels_by_track:
            reels_by_track[key] = []
        if len(reels_by_track[key]) < 3:
            reels_by_track[key].append(clean_text(r.get("caption"), 150))

    out.append(f"Fetched reel captions context for {len(reels_by_track)} tracks.")

    # 3. System Prompt for Used For classification
    system_prompt = (
        "You are an expert social media trend and reel format classifier.\n"
        "Your task: Classify the primary creator content format / use-case of each audio track in the batch.\n\n"
        "CRITICAL RULES:\n"
        "1. Allowed format categories for 'used_for' (MUST be one of):\n"
        "   - dance: Dance routines, choreography, rhythmic movements\n"
        "   - transition: Quick cuts, outfit changes, glow-up transitions, beat drops\n"
        "   - lip-sync: Lip-syncing to dialogue, lyrics, or funny voice lines\n"
        "   - meme: Humor, skits, relatable situations, funny reaction reels\n"
        "   - voiceover: Background audio for storytelling, vlogs, commentary, quotes\n"
        "   - outfit-showcase: Fashion, OOTD, aesthetic visuals, lookbooks\n"
        "   - tutorial: Educational, how-to, fitness demos, cooking recipes\n"
        "   - storytime: Personal anecdotes, POV scenarios, text-on-screen stories\n"
        "   - other: Format not fitting the above categories\n"
        "2. Provide a 'note': ONE short sentence (max 12 words) explaining why creators use this audio.\n"
        "3. You MUST return an entry for EVERY SINGLE input track in the batch.\n"
        "4. Output MUST be a JSON array of objects with EXACT keys:\n"
        '   [{"id": 1234, "used_for": "category", "note": "One short sentence explanation."}]\n'
    )

    batch_size = 10
    now_iso = datetime.now(timezone.utc).isoformat()
    
    queue = list(target_trends)
    attempts = {r["id"]: 0 for r in queue}
    row_by_id = {r["id"]: r for r in queue}

    classified_payloads = []
    hard_failures = []
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
            
            title = r.get("audio_title") or ""
            artist = r.get("audio_artist") or ""
            key = (title, artist)
            reel_caps = reels_by_track.get(key, [])

            batch_input.append({
                "id": tid,
                "title": title,
                "artist": artist,
                "sample_captions": clean_text(r.get("sample_captions"), 150),
                "reel_captions": reel_caps
            })

        user_prompt = (
            f"Classify the reel format use-case of these {len(batch_input)} tracks (Return JSON array with ALL {len(batch_input)} IDs):\n"
            + json.dumps(batch_input, indent=2)
            + "\nReturn ONLY a JSON array of objects."
        )

        res_json = None
        try:
            time.sleep(0.5)
            res_json = call_gemini_only(system_prompt, user_prompt, response_mime_type="application/json", timeout=30)
        except Exception as e:
            out.append(f"Batch {batch_num} API error: {e}")

        if isinstance(res_json, dict):
            if "items" in res_json and isinstance(res_json["items"], list):
                res_json = res_json["items"]
            elif "trends" in res_json and isinstance(res_json["trends"], list):
                res_json = res_json["trends"]
            elif "id" in res_json:
                res_json = [res_json]

        returned_ids = set()
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
                    uf = str(item.get("used_for") or "other").lower().strip()
                    if uf not in ALLOWED_USED_FOR:
                        uf = "other"
                    note = str(item.get("note") or f"Popular audio for creator {uf} reels.").strip()[:200]

                    classified_payloads.append({
                        "id": tid,
                        "used_for": uf,
                        "used_for_note": note,
                        "used_for_classified_at": now_iso
                    })

        missing_ids = sent_ids - returned_ids
        if missing_ids:
            out.append(f"[Batch {batch_num}] Sent {len(sent_ids)}, Processed {len(returned_ids)}, Missing {len(missing_ids)} IDs.")
            for mid in missing_ids:
                if attempts[mid] < 3:
                    queue.append(row_by_id[mid])
                else:
                    hard_failures.append(mid)
        else:
            out.append(f"[Batch {batch_num}] 1:1 SUCCESS! Sent {len(sent_ids)}, Classified {len(returned_ids)}/10 tracks.")

    out.append(f"\nTotal items classified: {len(classified_payloads)}")
    out.append(f"Total hard failures: {len(hard_failures)}")

    # 4. Batched Writes: Chunked updates (50 rows per batch) to respect Supabase limits
    write_chunk_size = 50
    out.append(f"\nExecuting chunked DB updates ({len(classified_payloads)} records in chunks of {write_chunk_size})...")

    updated_count = 0
    for i in range(0, len(classified_payloads), write_chunk_size):
        chunk = classified_payloads[i:i + write_chunk_size]
        for payload in chunk:
            try:
                supabase.table("trends").update({
                    "used_for": payload["used_for"],
                    "used_for_note": payload["used_for_note"],
                    "used_for_classified_at": payload["used_for_classified_at"]
                }).eq("id", payload["id"]).execute()
                updated_count += 1
            except Exception as e:
                out.append(f"Failed to update used_for for trend {payload['id']}: {e}")

    out.append(f"Chunked DB updates complete! Total trends updated: {updated_count}")

    # 5. Final Audit Query of used_for breakdown across active trends
    audit_res = supabase.table("trends").select("used_for").in_("status", ["rising", "emerging", "resurging", "peaked"]).execute()
    audit_data = audit_res.data or []
    
    used_for_counts = {}
    for r in audit_data:
        uf = str(r.get("used_for") or "<NULL>")
        used_for_counts[uf] = used_for_counts.get(uf, 0) + 1

    out.append("\n=== FINAL AUDIT REPORT: COUNTS BY USED_FOR ===")
    out.append(f"Total Active Trends Evaluated: {len(audit_data)}\n")
    for uf, c in sorted(used_for_counts.items(), key=lambda x: x[1], reverse=True):
        out.append(f"  {uf:<18}: {c}")

    if hard_failures:
        out.append(f"\nHard Failure IDs: {hard_failures}")

    out_text = "\n".join(out)
    print(out_text, flush=True)

    with open("scripts/used_for_report.txt", "w", encoding="utf-8") as f:
        f.write(out_text)

if __name__ == "__main__":
    run_used_for_classification()
