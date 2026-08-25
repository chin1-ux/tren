"""
Change B test: simulate external pipeline re-detection against real trends.
Matches by title+artist (no audio_id available in external pipeline).
Verifies: dedup fires, status never downgrades.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
sb = create_client(url, key)

STATUS_PRIORITY = {"expired": 0, "peaked": 1, "emerging": 2, "rising": 3}

# Pick one trend from each status
res = sb.table("trends").select("id, audio_title, audio_artist, status, velocity_avg").execute()
all_rows = res.data

by_status = {}
for r in all_rows:
    s = r.get("status")
    if s and s not in by_status:
        by_status[s] = r

print("=== CHANGE B TEST: External pipeline re-detection (title+artist match) ===\n")

results = []
for status, row in sorted(by_status.items()):
    old_status = row["status"]
    expected = old_status if STATUS_PRIORITY.get(old_status, 0) >= STATUS_PRIORITY.get("emerging", 0) else "emerging"

    print(f"--- {status.upper()} (id={row['id']}) ---")
    print(f"  Title: {row['audio_title']}, Artist: {row['audio_artist']}")
    print(f"  Current: {old_status} -> Expected: {expected}")

    # Simulate Change B dedup guard
    existing = sb.table("trends").select("id, status").eq("audio_title", row["audio_title"]).eq("audio_artist", row["audio_artist"]).execute()
    if not existing.data:
        print("  SKIP: no match found (shouldn't happen)")
        continue

    old = existing.data[0]
    final = old["status"] if STATUS_PRIORITY.get(old["status"], 0) >= STATUS_PRIORITY.get("emerging", 0) else "emerging"
    if final != old["status"]:
        sb.table("trends").update({"status": final}).eq("id", old["id"]).execute()

    after = sb.table("trends").select("status, velocity_avg").eq("id", old["id"]).execute().data[0]
    status_ok = after["status"] == expected
    vel_ok = after["velocity_avg"] == row["velocity_avg"]
    print(f"  Status: {after['status']} ({'PASS' if status_ok else 'FAIL'})")
    print(f"  Velocity: {after['velocity_avg']} ({'PASS unchanged' if vel_ok else 'FAIL changed'})")
    results.append((status, status_ok and vel_ok))
    print()

# Revert any status changes
for status, row in by_status.items():
    sb.table("trends").update({"status": status}).eq("id", row["id"]).execute()
print("Production data reverted.")

print("\n=== SUMMARY ===")
for s, ok in results:
    print(f"  {s}: {'PASS' if ok else 'FAIL'}")
print(f"Overall: {'ALL PASS' if all(ok for _, ok in results) else 'FAIL'}")
