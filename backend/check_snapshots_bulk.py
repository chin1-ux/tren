"""Snapshot count per surviving row — bulk query approach."""
import os, sys, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client
from collections import defaultdict

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
sb = create_client(url, key)

# Get all trend IDs that would survive
res = sb.table("trends").select("id, audio_id, velocity_avg, status, audio_title").execute()
all_rows = res.data

STATUS_ORDER = {"expired": 0, "peaked": 1, "emerging": 2, "rising": 3}
by_aid = defaultdict(list)
for r in all_rows:
    aid = r.get("audio_id")
    if aid:
        by_aid[aid].append(r)

dup_groups = {k: v for k, v in by_aid.items() if len(v) > 1}

keep_ids = set()
delete_ids = []
for aid, rows in dup_groups.items():
    rows_sorted = sorted(rows, key=lambda r: (STATUS_ORDER.get(r.get("status"), 0), r.get("velocity_avg") or 0), reverse=True)
    keep_ids.add(rows_sorted[0]["id"])
    for r in rows_sorted[1:]:
        delete_ids.append(r["id"])

# Also keep non-dup groups and no-audio rows
non_dup_keep = [r["id"] for r in all_rows if r.get("audio_id") and len(by_aid.get(r["audio_id"], [])) == 1]
all_keep_ids = list(keep_ids) + non_dup_keep + [r["id"] for r in all_rows if not r.get("audio_id")]

print(f"Keep IDs: {len(all_keep_ids)}, Delete IDs: {len(delete_ids)}")

# Bulk query ALL snapshots, then count by trend_id in Python
print("\nQuerying all trend_snapshots (bulk)...")
all_snaps = []
offset = 0
while True:
    res = sb.table("trend_snapshots").select("trend_id").range(offset, offset + 999).execute()
    if not res.data:
        break
    all_snaps.extend(res.data)
    offset += len(res.data)
    if len(res.data) < 1000:
        break

print(f"Total snapshots: {len(all_snaps)}")

# Count per trend_id
snap_by_tid = defaultdict(int)
for s in all_snaps:
    tid = s.get("trend_id")
    if tid:
        snap_by_tid[tid] += 1

# Survivor snapshot distribution
keep_snap_counts = [snap_by_tid.get(tid, 0) for tid in all_keep_ids if tid in keep_ids]
delete_snap_counts = [snap_by_tid.get(tid, 0) for tid in delete_ids]

print(f"\n--- SURVIVING ROWS (from duplicate groups) ---")
print(f"  Count: {len(keep_snap_counts)}")
if keep_snap_counts:
    print(f"  Snapshot count distribution:")
    print(f"    min: {min(keep_snap_counts)}")
    print(f"    max: {max(keep_snap_counts)}")
    print(f"    median: {statistics.median(keep_snap_counts):.0f}")
    print(f"    mean: {statistics.mean(keep_snap_counts):.1f}")
    print(f"    rows with 0 snapshots: {sum(1 for c in keep_snap_counts if c == 0)}")
    print(f"    rows with 1-2 snapshots: {sum(1 for c in keep_snap_counts if 1 <= c <= 2)}")
    print(f"    rows with 3+ snapshots: {sum(1 for c in keep_snap_counts if c >= 3)}")
    print(f"    rows with 10+ snapshots: {sum(1 for c in keep_snap_counts if c >= 10)}")

    # Show low-snapshot survivors
    low = [(tid, snap_by_tid.get(tid, 0)) for tid in keep_ids if snap_by_tid.get(tid, 0) < 3]
    if low:
        print(f"\n  Survivors with <3 snapshots (promotion gate requires 3):")
        for tid, count in sorted(low, key=lambda x: x[1]):
            row = next((r for r in all_rows if r["id"] == tid), None)
            if row:
                print(f"    trend_id={tid}: {count} snaps | {row.get('audio_title','?')[:40]} | status={row.get('status')}")
    else:
        print(f"\n  All survivors have >=3 snapshots OK")

print(f"\n--- DELETE ROWS ---")
print(f"  Count: {len(delete_snap_counts)}")
print(f"  Total snapshots on DELETE rows: {sum(delete_snap_counts)}")
print(f"  Snapshots that will be cascade-deleted: {sum(delete_snap_counts)}")

total_snaps = len(all_snaps)
lost = sum(delete_snap_counts)
print(f"\n--- TOTAL ---")
print(f"  Total snapshots: {total_snaps}")
print(f"  Lost on cascade: {lost}")
print(f"  Remaining: {total_snaps - lost}")
print(f"  Percentage lost: {lost/total_snaps*100:.1f}%" if total_snaps > 0 else "")
