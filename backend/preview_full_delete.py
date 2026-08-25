"""Clean preview SELECT — paste complete output. No encoding issues."""
import os, sys, csv, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client
from collections import defaultdict

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
sb = create_client(url, key)

# Fetch ALL trends
res = sb.table("trends").select("id, audio_id, audio_title, velocity_avg, status, created_at, reel_count").execute()
all_rows = res.data

print(f"TOTAL ROWS: {len(all_rows)}")

STATUS_ORDER = {"expired": 0, "peaked": 1, "emerging": 2, "rising": 3}

by_aid = defaultdict(list)
for r in all_rows:
    aid = r.get("audio_id")
    if aid:
        by_aid[aid].append(r)

dup_groups = {k: v for k, v in by_aid.items() if len(v) > 1}
print(f"UNIQUE AUDIO_IDS: {len(by_aid)}")
print(f"DUPLICATE GROUPS: {len(dup_groups)}")

# Survivor: highest status first, then velocity
keep_ids = set()
delete_rows = []
for aid, rows in dup_groups.items():
    rows_sorted = sorted(rows, key=lambda r: (STATUS_ORDER.get(r.get("status"), 0), r.get("velocity_avg") or 0), reverse=True)
    keep_ids.add(rows_sorted[0]["id"])
    for r in rows_sorted[1:]:
        delete_rows.append(r)

delete_ids = sorted([r["id"] for r in delete_rows])
print(f"ROWS TO DELETE: {len(delete_ids)}")
print(f"ROWS TO KEEP: {len(all_rows) - len(delete_ids)}")
print(f"RECONCILIATION: {len(all_rows) - len(delete_ids)} + {len(delete_ids)} = {len(all_rows)}")

# Print ALL delete IDs, one per line, with group headers
print(f"\n{'='*80}")
print(f"FULL DELETE LIST: {len(delete_ids)} rows across {len(dup_groups)} groups")
print(f"{'='*80}")

for aid, rows in sorted(dup_groups.items(), key=lambda x: len(x[1]), reverse=True):
    rows_sorted = sorted(rows, key=lambda r: (STATUS_ORDER.get(r.get("status"), 0), r.get("velocity_avg") or 0), reverse=True)
    survivor = rows_sorted[0]
    deletes = rows_sorted[1:]
    title = survivor.get("audio_title", "?")[:50]
    print(f"\nGROUP: {title} (audio_id={aid}, {len(rows)} rows, survivor=id:{survivor['id']})")
    for r in deletes:
        print(f"  DELETE id={r['id']} vel={r.get('velocity_avg') or 0:.0f} status={r.get('status')} created={str(r.get('created_at',''))[:10]}")

print(f"\n{'='*80}")
print(f"ALL DELETE IDs (sorted):")
print(f"{'='*80}")
# Print all IDs in rows of 10
for i in range(0, len(delete_ids), 10):
    chunk = delete_ids[i:i+10]
    print(f"  {', '.join(str(x) for x in chunk)}")

print(f"\nTOTAL DELETE IDs: {len(delete_ids)}")

# CSV export
csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trend_delete_list.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "audio_id", "audio_title", "velocity_avg", "status", "created_at", "reel_count"])
    for r in sorted(delete_rows, key=lambda x: x["id"]):
        writer.writerow([r["id"], r.get("audio_id"), r.get("audio_title"), r.get("velocity_avg"), r.get("status"), r.get("created_at"), r.get("reel_count")])
print(f"\nCSV exported: {csv_path}")

# Row count drift investigation
print(f"\n{'='*80}")
print(f"ROW COUNT DRIFT INVESTIGATION")
print(f"{'='*80}")
print(f"Original audit (earlier session): 1,012 total rows, 170 duplicate groups, 681 excess")
print(f"Current count: {len(all_rows)} total rows, {len(dup_groups)} duplicate groups, {len(delete_ids)} to delete")
print(f"Drift: {1012 - len(all_rows)} total rows, {170 - len(dup_groups)} groups, {681 - len(delete_ids)} excess")
print(f"\nPossible causes:")
print(f"  1. Scraper ran between sessions and added new trends")
print(f"  2. Scraper ran and updated statuses (emerging->peaked->expired), changing which rows are duplicates")
print(f"  3. Earlier count was approximate/different query method")

# Check for very recent trends (today)
from datetime import datetime, timezone
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
recent = [r for r in all_rows if str(r.get("created_at",""))[:10] == today]
print(f"\nTrends created today ({today}): {len(recent)}")
for r in recent:
    print(f"  id={r['id']} {r.get('audio_title','?')[:40]} status={r.get('status')}")
