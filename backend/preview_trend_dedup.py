"""
P-METHOD-1: Preview SELECT — shows exactly which rows would be deleted.
NO DELETE runs. Read-only. Simplified to avoid per-ID snapshot queries.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from collections import defaultdict, Counter

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
sb = create_client(url, key)

print("=" * 80)
print("1. STATUS DISTRIBUTION (before)")
print("=" * 80)
res = sb.table("trends").select("id, audio_id, audio_title, velocity_avg, status, created_at, reel_count").execute()
all_rows = res.data

status_counts = Counter(r["status"] for r in all_rows)
for status, count in sorted(status_counts.items()):
    print(f"  {status}: {count}")
print(f"  TOTAL: {len(all_rows)}")

print()
print("=" * 80)
print("2. DUPLICATE GROUPS")
print("=" * 80)
by_aid = defaultdict(list)
for r in all_rows:
    aid = r.get("audio_id")
    if aid:
        by_aid[aid].append(r)

dup_groups = {k: v for k, v in by_aid.items() if len(v) > 1}
dup_groups_sorted = sorted(dup_groups.items(), key=lambda x: len(x[1]), reverse=True)

total_dup_rows = sum(len(v) for _, v in dup_groups_sorted)
rows_to_delete = total_dup_rows - len(dup_groups)

print(f"  Unique audio_ids: {len(by_aid)}")
print(f"  Rows with no audio_id: {sum(1 for r in all_rows if not r.get('audio_id'))}")
print(f"  Duplicate groups (count > 1): {len(dup_groups)}")
print(f"  Total rows in duplicate groups: {total_dup_rows}")
print(f"  Rows to DELETE (keeping highest velocity per group): {rows_to_delete}")

print()
print("=" * 80)
print("3. TOP 25 DUPLICATE GROUPS")
print("=" * 80)
for aid, rows in dup_groups_sorted[:25]:
    rows_sorted = sorted(rows, key=lambda r: (r.get("velocity_avg") or 0), reverse=True)
    title = rows_sorted[0].get("audio_title", "?")
    print(f"\n  [{len(rows)}x] {title} (audio_id={aid})")
    print(f"  {'ID':>6} | {'vel_avg':>10} | {'reels':>6} | {'status':>10} | {'created':>12} | {'action':>6}")
    print(f"  {'-'*6}-+-{'-'*10}-+-{'-'*6}-+-{'-'*10}-+-{'-'*12}-+-{'-'*6}")
    for i, r in enumerate(rows_sorted):
        action = "KEEP" if i == 0 else "DEL"
        ca = (r.get("created_at") or "")[:10]
        print(f"  {r['id']:>6} | {(r.get('velocity_avg') or 0):>10.0f} | {r.get('reel_count') or 0:>6} | {r.get('status') or '':>10} | {ca:>12} | {action:>6}")

print()
print("=" * 80)
print("4. FULL DELETE LIST (all groups)")
print("=" * 80)
delete_ids = []
delete_details = []
for aid, rows in dup_groups_sorted:
    rows_sorted = sorted(rows, key=lambda r: (r.get("velocity_avg") or 0), reverse=True)
    for r in rows_sorted[1:]:
        delete_ids.append(r["id"])
        delete_details.append((r["id"], aid, r.get("audio_title","?"), r.get("velocity_avg") or 0, r.get("status")))

print(f"  Total rows to DELETE: {len(delete_ids)}")
print(f"  Total rows to KEEP: {len(dup_groups) + sum(1 for r in all_rows if not r.get('audio_id') or r.get('audio_id') not in dup_groups)}")

# Group by title for readability
by_title = defaultdict(list)
for d in delete_details:
    by_title[d[2]].append(d)

print(f"\n  Unique titles affected: {len(by_title)}")
for title in sorted(by_title.keys(), key=lambda t: len(by_title[t]), reverse=True)[:30]:
    items = by_title[title]
    ids = [d[0] for d in items]
    print(f"    [{len(items)+1}x] {title} — delete IDs: {ids}")

print()
print("=" * 80)
print("5. SNAPSHOT LOSS ESTIMATE (batch query)")
print("=" * 80)
# Query all snapshot trend_ids in one go
if delete_ids:
    # Supabase .in_() has limits, chunk it
    CHUNK = 100
    all_snap_trend_ids = []
    for i in range(0, len(delete_ids), CHUNK):
        chunk = delete_ids[i:i+CHUNK]
        snap_res = sb.table("trend_snapshots").select("trend_id").in_("trend_id", chunk).execute()
        all_snap_trend_ids.extend([r["trend_id"] for r in snap_res.data])

    print(f"  Snapshots attached to DELETE rows: {len(all_snap_trend_ids)}")

    # Also count total snapshots
    total_snap_res = sb.table("trend_snapshots").select("id", count="exact").execute()
    # count might not work, use len
    print(f"  Total snapshots in table: queried separately")
else:
    print("  No rows to delete")

print()
print("=" * 80)
print("6. METRICS BASELINE (before backfill)")
print("=" * 80)
rising = [r for r in all_rows if r.get("status") == "rising"]
emerging = [r for r in all_rows if r.get("status") == "emerging"]
peaked = [r for r in all_rows if r.get("status") == "peaked"]
expired = [r for r in all_rows if r.get("status") == "expired"]

import statistics
def safe_median(vals):
    return statistics.median(vals) if vals else 0

print(f"  rising:   {len(rising)} trends, median velocity = {safe_median([r.get('velocity_avg') or 0 for r in rising]):.0f}")
print(f"  emerging: {len(emerging)} trends, median velocity = {safe_median([r.get('velocity_avg') or 0 for r in emerging]):.0f}")
print(f"  peaked:   {len(peaked)} trends, median velocity = {safe_median([r.get('velocity_avg') or 0 for r in peaked]):.0f}")
print(f"  expired:  {len(expired)} trends, median velocity = {safe_median([r.get('velocity_avg') or 0 for r in expired]):.0f}")
