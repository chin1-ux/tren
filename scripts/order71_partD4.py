import os
import sys
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv("backend/.env")
from supabase import create_client

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
now = datetime.now(timezone.utc)

print("=" * 95)
print("PART D4: TAG YIELD FORMULA & RAW SQL CROSS-CHECKS")
print("=" * 95)

formula = """
EXACT FORMULA FOR 'NEW NON-ORIGINAL AUDIOS':
---------------------------------------------------------------------------------------------------
1. Observation Window : reels with created_at in [now - 3d, now] AND source_tag = <tag>
2. Prior 14-day Window: reels with created_at in [now - 17d, now - 3d)
3. Non-Original Filter: reel.is_original_audio = false (or has commercial music metadata)
4. New Audio Definition: audio_id IN (Observation Window non-original audios)
                         AND audio_id NOT IN (Prior 14-day Window audios)
---------------------------------------------------------------------------------------------------
"""
print(formula)

test_tags = ["tamilreels", "telugureels", "hiphopreels"]

# 1. Fetch runs seen per tag from tag_run_stats in last 3 days
cutoff_3d = (now - timedelta(days=3)).isoformat()
cutoff_17d = (now - timedelta(days=17)).isoformat()

# 2. Recompute 3 tags
print(f"{'Tag':<18} | {'Runs Seen (3d)':<16} | {'Total Reels (3d)':<18} | {'Non-Orig Audios':<18} | {'New Non-Orig'}")
print("-" * 95)

for tag in test_tags:
    # Query 3d reels for tag
    reels_3d = sb.table("reels") \
        .select("audio_id, is_original_audio, scraped_at, created_at") \
        .eq("source_tag", tag) \
        .gte("created_at", cutoff_3d) \
        .execute().data or []
        
    total_reels = len(reels_3d)
    # Estimate distinct runs from timestamps grouped by hour
    scrape_hours = {(r.get("scraped_at") or r.get("created_at") or "")[:13] for r in reels_3d if (r.get("scraped_at") or r.get("created_at"))}
    runs_seen = len(scrape_hours)
    
    # Non-original audio IDs in observation window
    non_orig_aids = {
        str(r["audio_id"]) for r in reels_3d
        if r.get("audio_id") and str(r.get("audio_id")) not in ("0", "Unknown") and r.get("is_original_audio") is False
    }
    
    # Check prior 14d presence for each candidate
    new_non_orig_count = 0
    if non_orig_aids:
        prior_res = sb.table("reels") \
            .select("audio_id") \
            .in_("audio_id", list(non_orig_aids)) \
            .gte("created_at", cutoff_17d) \
            .lt("created_at", cutoff_3d) \
            .execute().data or []
        prior_aids = {str(r["audio_id"]) for r in prior_res if r.get("audio_id")}
        new_non_orig = non_orig_aids - prior_aids
        new_non_orig_count = len(new_non_orig)
        
    print(f"#{tag:<17} | {runs_seen:<16} | {total_reels:<18} | {len(non_orig_aids):<18} | {new_non_orig_count}")

print("=" * 95)
