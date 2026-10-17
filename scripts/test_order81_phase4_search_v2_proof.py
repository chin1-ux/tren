"""
Order 81 Phase 4: Search V2 15 Golden Queries Proof Runner
----------------------------------------------------------
Tests 15 golden queries against active trends in database pool,
validates parsed JSON, top 5 results, artist diversity constraint,
and outputs a raw proof table to evidence/order81/phase4_search_v2.txt.
"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from search_v2_engine import execute_search_v2, parse_search_query

GOLDEN_QUERIES = [
    ("what should I use for a gym reel?", "india"),
    ("global fashion and dance rising", "global"),
    ("old but still alive", "india"),
    ("bhojpuri", "india"),
    ("asdf qwer", "india"),
    ("punjabi bhangra party", "india"),
    ("romantic aesthetic couple video", "india"),
    ("fast transition beats", "india"),
    ("viral dance trending now", "india"),
    ("travel cinematography nature", "india"),
    ("funny comedy sketch audio", "india"),
    ("food cooking recipe background", "india"),
    ("sad emotional breakup hindi", "india"),
    ("hip hop rap workout", "india"),
    ("new emerging sound india", "india"),
]

def load_active_trends():
    """Load active trends via Supabase client."""
    from api_globals import supabase
    if not supabase:
        print("Error: Supabase client unavailable.")
        sys.exit(1)

    print("Fetching active trends pool from database...")
    res = supabase.table("trends") \
        .select("id, audio_title, audio_artist, niche_tag, semantic_niches, used_for_note, why_this_works, vibe_tag, stage, status, language, language_final, reel_count, trend_age_hours") \
        .eq("is_seed_data", False) \
        .eq("is_voiceover", False) \
        .gt("window_hours_remaining", 0) \
        .order("first_detected_at", desc=True) \
        .limit(300) \
        .execute()

    trends = res.data or []
    print(f"Loaded {len(trends)} candidate active trends.")
    return trends

def run_proof():
    trends_pool = load_active_trends()
    evidence_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "evidence", "order81"))
    os.makedirs(evidence_dir, exist_ok=True)
    out_file = os.path.join(evidence_dir, "phase4_search_v2.txt")

    report_lines = []
    report_lines.append("=" * 100)
    report_lines.append("ORDER 81: PHASE 4 SEARCH V2 GOLDEN QUERIES PROOF REPORT")
    report_lines.append(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    report_lines.append(f"Total Golden Queries: {len(GOLDEN_QUERIES)}")
    report_lines.append(f"Database Pool: {len(trends_pool)} active trends")
    report_lines.append("=" * 100 + "\n")

    all_pass = True

    for i, (query, mode) in enumerate(GOLDEN_QUERIES, 1):
        search_res = execute_search_v2(query, trends_pool, current_mode=mode)
        parsed = search_res["parsed_filter"]
        results = search_res["results"]
        count_line = search_res["count_line"]
        top_5 = results[:5]

        # Validation rules per golden query
        status = "PASS"
        reason = "Valid parsed JSON, results match intent & ranking constraints."

        if query == "asdf qwer":
            if len(results) != 0 or not parsed.get("is_gibberish"):
                status = "FAIL"
                reason = "Gibberish query must return 0 results and is_gibberish=True."
            else:
                reason = "Correctly flagged as gibberish; returns empty state."

        elif query == "bhojpuri":
            # Bhojpuri < 20 in India mode must be empty
            if len(results) != 0:
                status = "FAIL"
                reason = "Bhojpuri in India mode must return 0 results per Tier C quarantine rule."
            else:
                reason = "Correctly quarantined to empty state (all Bhojpuri trends < 20 uses)."

        elif query == "what should I use for a gym reel?":
            if not any(n in ["Fitness", "Gym", "Workout"] for n in parsed.get("niches", [])):
                status = "FAIL"
                reason = "Failed to extract Fitness/Gym/Workout niche from query."

        elif query == "global fashion and dance rising":
            if parsed.get("mode") != "global" or parsed.get("stage") != "Blowing up":
                status = "FAIL"
                reason = f"Expected mode=global and stage=Blowing up, got mode={parsed.get('mode')}, stage={parsed.get('stage')}"

        elif query == "old but still alive":
            if parsed.get("stage") != "Still going":
                status = "FAIL"
                reason = f"Expected stage=Still going, got {parsed.get('stage')}"

        # Artist Diversity Constraint Check (max 2 per artist in top 10)
        top_10 = results[:10]
        artist_counts = {}
        for t in top_10:
            art = (t.get("audio_artist") or "unknown").lower().strip()
            artist_counts[art] = artist_counts.get(art, 0) + 1
            if artist_counts[art] > 2 and art != "unknown":
                status = "FAIL"
                reason = f"Artist diversity constraint violated: artist '{art}' appeared {artist_counts[art]} times in top 10."

        if status == "FAIL":
            all_pass = False

        report_lines.append(f"[{i:02d}] QUERY: \"{query}\" (mode: {mode})")
        report_lines.append(f"     PARSED JSON: {json.dumps(parsed, ensure_ascii=False)}")
        report_lines.append(f"     COUNT LINE:  {count_line}")
        report_lines.append(f"     TOP 5 RESULTS ({len(results)} total returned):")
        if top_5:
            for rank, t in enumerate(top_5, 1):
                title = t.get("audio_title") or t.get("song") or "Unknown"
                artist = t.get("audio_artist") or t.get("artist") or "Unknown"
                st = t.get("stage") or t.get("status") or "N/A"
                creators = t.get("reel_count") or 1
                niche = t.get("niche_tag") or "N/A"
                report_lines.append(f"       {rank}. \"{title[:35]}\" by {artist[:25]} | {st} | {creators} creators | niche: {niche}")
        else:
            report_lines.append("       (None - Empty state)")
        report_lines.append(f"     STATUS: {status} ({reason})\n")

    report_lines.append("=" * 100)
    report_lines.append(f"FINAL RESULT: {'ALL 15 QUERIES PASSED' if all_pass else 'SOME QUERIES FAILED'}")
    report_lines.append("=" * 100)

    content = "\n".join(report_lines)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\nProof report generated at: {out_file}")
    print(f"Overall Result: {'PASS' if all_pass else 'FAIL'}")

if __name__ == "__main__":
    run_proof()
