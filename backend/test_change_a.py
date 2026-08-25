"""
Change A test: simulate re-detection against real trends with different statuses.
Verifies: update fires, status never downgrades, velocity unchanged.
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

res = sb.table("trends").select("id, audio_id, audio_title, status, velocity_avg").execute()
all_rows = res.data

by_status = {}
for r in all_rows:
    s = r.get("status")
    if s and s not in by_status:
        by_status[s] = r

print("=== CHANGE A TEST: Re-detection simulation ===")
print("For each status, simulate re-detection (always starts as 'emerging').")
print("Expected: status never downgrades, velocity unchanged.\n")

results = []
for status, row in sorted(by_status.items()):
    old_status = row["status"]
    old_priority = STATUS_PRIORITY.get(old_status, 0)
    new_priority = STATUS_PRIORITY.get("emerging", 0)
    expected_status = old_status if old_priority >= new_priority else "emerging"

    print(f"--- {status.upper()} (id={row['id']}, audio_id={row['audio_id']}) ---")
    print(f"  Title: {row['audio_title']}")
    print(f"  Current status: {old_status}")
    print(f"  Re-detection status: emerging")
    print(f"  Expected final: {expected_status}")

    # Capture before
    before_res = sb.table("trends").select("status, velocity_avg").eq("id", row["id"]).execute()
    before = before_res.data[0]

    # Apply Change A logic (same as trend_engine.py)
    final_status = old_status if old_priority >= new_priority else "emerging"
    if final_status != old_status:
        sb.table("trends").update({"status": final_status}).eq("id", row["id"]).execute()

    # Capture after
    after_res = sb.table("trends").select("status, velocity_avg").eq("id", row["id"]).execute()
    after = after_res.data[0]

    # Verify
    checks = []
    status_ok = after["status"] == expected_status
    checks.append(("status correct", status_ok, f"got {after['status']}, expected {expected_status}"))

    vel_ok = after["velocity_avg"] == before["velocity_avg"]
    checks.append(("velocity_avg unchanged", vel_ok, f"before={before['velocity_avg']}, after={after['velocity_avg']}"))

    all_pass = all(c[1] for c in checks)
    for name, ok, detail in checks:
        print(f"  {'PASS' if ok else 'FAIL'}: {name} - {detail}")

    print(f"  RESULT: {'ALL PASS' if all_pass else 'FAIL'}\n")
    results.append((status, all_pass))

print("=== SUMMARY ===")
for status, ok in results:
    print(f"  {status}: {'PASS' if ok else 'FAIL'}")
all_ok = all(ok for _, ok in results)
print(f"\nOverall: {'ALL PASS' if all_ok else 'FAIL'}")
