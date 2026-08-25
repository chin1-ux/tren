import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client
import statistics
from collections import Counter
from datetime import datetime, timedelta, timezone

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
sb = create_client(url, key)

# === 1. STATUS BREAKDOWN (raw values) ===
print("=== 1. STATUS BREAKDOWN (raw) ===")
all_res = sb.table("trends").select("id, status, audio_title, audio_artist, velocity_avg, audio_id, first_detected_at").execute()
rows = all_res.data
print(f"Total rows: {len(rows)}")

raw_statuses = Counter(r.get("status") for r in rows)
print(f"Raw status values: {dict(raw_statuses)}")

# Show a few examples
print("\nSample rows (first 5):")
for r in rows[:5]:
    print(f"  id={r['id']} status='{r.get('status')}' title='{r.get('audio_title','')[:40]}' vel={r.get('velocity_avg')}")

# === 2. DUPLICATE TITLE+ARTIST PAIRS ===
print("\n=== 2. DUPLICATE TITLE+ARTIST PAIRS ===")
ta_groups = {}
for r in rows:
    ta = (r.get("audio_title", "").strip(), r.get("audio_artist", "").strip())
    ta_groups.setdefault(ta, []).append(r)

dups = {k: v for k, v in ta_groups.items() if len(v) > 1}
print(f"Duplicate (title, artist) groups: {len(dups)}")
for (title, artist), group in dups.items():
    print(f"\n  '{title}' by '{artist}' ({len(group)} rows):")
    for r in group:
        print(f"    id={r['id']} audio_id={r.get('audio_id')} status='{r.get('status')}' vel={r.get('velocity_avg')}")

# === 3. RISING-BASELINE (using raw status) ===
print("\n=== 3. RISING-BASELINE VELOCITY ===")
# Try both possible status values
for status_val in ["rising", "RISING", "Rising"]:
    rising = [r for r in rows if r.get("status") == status_val]
    if rising:
        print(f"  Found {len(rising)} rising rows with status='{status_val}'")
        break
else:
    # Show what statuses exist
    print(f"  No 'rising' rows found. Unique status values: {set(r.get('status') for r in rows)}")
    # Try all non-null statuses
    non_null = [r for r in rows if r.get("status")]
    print(f"  Rows with non-null status: {len(non_null)}")
    if non_null:
        print(f"  Status values: {set(r.get('status') for r in non_null)}")

# === 4. SCALE CHECK ===
print("\n=== 4. SCALE CHECK ===")
reels_total = sb.table("reels").select("id", count="exact").execute()
tracked = sb.table("tracked_audio").select("audio_id", count="exact").execute()
week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
recent_reels = sb.table("reels").select("id", count="exact").gte("created_at", week_ago).execute()
recent_trends = sb.table("trends").select("id", count="exact").gte("first_detected_at", week_ago).execute()

print(f"  Total reels: {reels_total.count}")
print(f"  Tracked audio: {tracked.count}")
print(f"  Trends: {len(rows)}")
print(f"  Reels (7d): {recent_reels.count}")
print(f"  Trends (7d): {recent_trends.count}")

# === 5. FIRST_DETECTED_AT distribution ===
print("\n=== 5. FIRST_DETECTED_AT DISTRIBUTION ===")
dates = []
for r in rows:
    fda = r.get("first_detected_at")
    if fda:
        try:
            dates.append(str(fda)[:10])
        except:
            pass
date_counts = Counter(dates)
print(f"  Rows with first_detected_at: {len(dates)}")
print(f"  Rows without: {len(rows) - len(dates)}")
for d in sorted(date_counts.keys())[-10:]:
    print(f"    {d}: {date_counts[d]}")
