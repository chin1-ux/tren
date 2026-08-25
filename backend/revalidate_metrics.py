import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client
import statistics

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
sb = create_client(url, key)

# === 1. CURRENT TOTALS ===
print("=== 1. CURRENT TOTALS ===")
all_res = sb.table("trends").select("id, audio_id, audio_title, audio_artist").execute()
rows = all_res.data
print(f"Total trend rows: {len(rows)}")

audio_ids = set()
title_artist_pairs = set()
for r in rows:
    aid = r.get("audio_id")
    if aid:
        audio_ids.add(str(aid))
    ta = (r.get("audio_title", "").strip(), r.get("audio_artist", "").strip())
    if ta[0]:
        title_artist_pairs.add(ta)

print(f"Distinct audio_id values: {len(audio_ids)}")
print(f"Distinct (title, artist) pairs: {len(title_artist_pairs)}")

# Check for duplicates
from collections import Counter
aid_counts = Counter(str(r.get("audio_id")) for r in rows if r.get("audio_id"))
ta_counts = Counter((r.get("audio_title", "").strip(), r.get("audio_artist", "").strip()) for r in rows if r.get("audio_title"))
dup_aids = {k: v for k, v in aid_counts.items() if v > 1}
dup_tas = {k: v for k, v in ta_counts.items() if v > 1}
print(f"Duplicate audio_ids: {len(dup_aids)} (should be 0)")
print(f"Duplicate (title, artist) pairs: {len(dup_tas)} (should be 0)")
if dup_aids:
    print(f"  DUP AUDIO_IDS: {dup_aids}")
if dup_tas:
    print(f"  DUP TITLE+ARTIST: {dup_tas}")

# === 2. STATUS BREAKDOWN ===
print("\n=== 2. STATUS BREAKDOWN ===")
status_counts = Counter(r.get("status", "unknown") for r in rows)
for status in ["rising", "emerging", "peaked", "expired"]:
    print(f"  {status}: {status_counts.get(status, 0)}")
print(f"  unknown/other: {status_counts.get('unknown', 0)}")
print(f"  Total: {sum(status_counts.values())}")

# === 3. new_trends_found metric ===
print("\n=== 3. new_trends_found METRIC ===")
# Check business_metrics.py
import importlib.util
spec = importlib.util.spec_from_file_location("business_metrics", "business_metrics.py")
if spec:
    bm = importlib.util.module_from_spec(spec)
    # Don't execute it, just show what we can
    print("business_metrics.py exists — checking for new_trends_found references...")

# Search for the metric in code
import subprocess
result = subprocess.run(
    ["grep", "-rn", "new_trends_found", "."],
    capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__))
)
print(f"Code references to new_trends_found:\n{result.stdout or '(none found)'}")

# Also check what the API returns for this metric
print("\nQuerying trends created in last 7 days (proxy for new_trends_found):")
from datetime import datetime, timedelta, timezone
week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
recent = sb.table("trends").select("id", count="exact").gte("first_detected_at", week_ago).execute()
print(f"  Trends created in last 7 days: {recent.count}")

recent_30d = sb.table("trends").select("id", count="exact").gte("first_detected_at", (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()).isoformat()
recent_30d_res = sb.table("trends").select("id", count="exact").gte("first_detected_at", (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()).execute()
print(f"  Trends created in last 30 days: {recent_30d_res.count}")

# === 4. RISING-BASELINE VELOCITY MEDIAN ===
print("\n=== 4. RISING-BASELINE VELOCITY MEDIAN ===")
rising = sb.table("trends").select("velocity_avg, audio_title").eq("status", "rising").execute()
rising_vels = [r.get("velocity_avg") or 0 for r in rising.data]
if rising_vels:
    print(f"  Rising trends: {len(rising_vels)}")
    print(f"  Velocity avg values: {[round(v, 1) for v in rising_vels]}")
    print(f"  Median velocity: {round(statistics.median(rising_vels), 1)}")
    print(f"  Mean velocity: {round(statistics.mean(rising_vels), 1)}")
    print(f"  Min: {round(min(rising_vels), 1)}")
    print(f"  Max: {round(max(rising_vels), 1)}")
else:
    print("  No rising trends found")

# === 5. SANITY CHECK ON SCALE ===
print("\n=== 5. SANITY CHECK ON SCALE ===")
reels_total = sb.table("reels").select("id", count="exact").execute()
tracked = sb.table("tracked_audio").select("audio_id", count="exact").execute()
print(f"  Total reels in DB: {reels_total.count}")
print(f"  Tracked audio entries: {tracked.count}")
print(f"  Trends per reel ratio: {len(rows)}/{reels_total.count} = {len(rows)/max(reels_total.count,1):.3f}")
print(f"  Trends per tracked audio: {len(rows)}/{tracked.count} = {len(rows)/max(tracked.count,1):.3f}")

# Recent scrape activity
recent_reels = sb.table("reels").select("id", count="exact").gte("created_at", (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()).execute()
print(f"  Reels scraped in last 7 days: {recent_reels.count}")
print(f"  Trends created in last 7 days: {recent.count}")
print(f"  Detection rate (trends/reels this week): {recent.count/max(recent_reels.count,1):.3f}")
