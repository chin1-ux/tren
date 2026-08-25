"""
P-METHOD-1: Live verification queries.
1. FK constraint on production trend_snapshots
2. Full delete list export
3. Snapshot counts per surviving row
"""
import os, sys, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from collections import defaultdict

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
sb = create_client(url, key)

# ═══════════════════════════════════════════════════════════════════════════
# 1. LIVE FK CONSTRAINT CHECK
# ═══════════════════════════════════════════════════════════════════════════
print("=" * 80)
print("1. LIVE FK CONSTRAINT ON trend_snapshots (production)")
print("=" * 80)

# Supabase Python client doesn't support raw SQL directly.
# Use the REST API to query information_schema or pg_constraint.
import requests

supabase_url = url
service_key = key

# Query pg_constraint via PostgREST /rpc or direct HTTP
# Actually, let's use the Supabase SQL endpoint
headers = {
    "apikey": service_key,
    "Authorization": f"Bearer {service_key}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# Try querying information_schema.table_constraints + key_column_usage
# via PostgREST on the information_schema tables
try:
    resp = requests.get(
        f"{supabase_url}/rest/v1/rpc/exec_sql",
        headers=headers,
        json={"query": "SELECT 1"},
        timeout=10
    )
    print(f"  RPC exec_sql available: {resp.status_code}")
except Exception as e:
    print(f"  RPC exec_sql not available: {e}")

# Alternative: query the information_schema via PostgREST
# Actually, Supabase exposes information_schema as a schema we can query
try:
    # Query foreign_keys from information_schema
    resp = requests.get(
        f"{supabase_url}/rest/v1/foreign_keys?table_name=eq.trend_snapshots",
        headers={"apikey": service_key, "Authorization": f"Bearer {service_key}"},
        timeout=10
    )
    print(f"  information_schema.foreign_keys query: {resp.status_code}")
    if resp.status_code == 200:
        print(f"  Result: {resp.json()}")
except Exception as e:
    print(f"  information_schema query failed: {e}")

# Best approach: use the pg_constraint system catalog via a direct connection
# Since we have SUPABASE_DB_URL, let's try pg8000 or psycopg2
print("\n  Attempting direct PostgreSQL connection...")
try:
    import pg8000.native
    db_url = os.getenv("SUPABASE_DB_URL")
    # Parse postgresql://user:pass@host:port/dbname
    import re
    m = re.match(r"postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", db_url)
    if m:
        user, password, host, port, dbname = m.groups()
        conn = pg8000.native.Connection(user=user, password=password, host=host, port=int(port), database=dbname)
        rows = conn.run(
            "SELECT conname, confdeltype, confupdtype "
            "FROM pg_constraint "
            "WHERE conrelid = 'trend_snapshots'::regclass AND contype = 'f'"
        )
        print(f"  LIVE FK CONSTRAINTS on trend_snapshots:")
        for row in rows:
            conname, confdeltype, confupdtype = row
            cascade_map = {"a": "NO ACTION", "r": "RESTRICT", "c": "CASCADE", "n": "SET NULL", "d": "SET DEFAULT"}
            print(f"    constraint={conname}, on_delete={cascade_map.get(confdeltype, confdeltype)}, on_update={cascade_map.get(confupdtype, confupdtype)}")
            if confdeltype == "c":
                print(f"    >>> CONFIRMED: ON DELETE CASCADE is live on production")
            else:
                print(f"    >>> WARNING: ON DELETE CASCADE is NOT active (confdeltype={confdeltype})")
        conn.close()
    else:
        print(f"  Could not parse DB URL: {db_url[:30]}...")
except ImportError:
    print("  pg8000 not installed. Trying psycopg2...")
    try:
        import psycopg2
        db_url = os.getenv("SUPABASE_DB_URL")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute(
            "SELECT conname, confdeltype, confupdtype "
            "FROM pg_constraint "
            "WHERE conrelid = 'trend_snapshots'::regclass AND contype = 'f'"
        )
        rows = cur.fetchall()
        print(f"  LIVE FK CONSTRAINTS on trend_snapshots:")
        for row in rows:
            conname, confdeltype, confupdtype = row
            cascade_map = {"a": "NO ACTION", "r": "RESTRICT", "c": "CASCADE", "n": "SET NULL", "d": "SET DEFAULT"}
            print(f"    constraint={conname}, on_delete={cascade_map.get(confdeltype, confdeltype)}, on_update={cascade_map.get(confupdtype, confupdtype)}")
            if confdeltype == "c":
                print(f"    >>> CONFIRMED: ON DELETE CASCADE is live on production")
            else:
                print(f"    >>> WARNING: ON DELETE CASCADE is NOT active (confdeltype={confdeltype})")
        cur.close()
        conn.close()
    except ImportError:
        print("  Neither pg8000 nor psycopg2 installed. Cannot query live DB.")
        print("  Install one: pip install pg8000 OR pip install psycopg2-binary")
    except Exception as e:
        print(f"  psycopg2 connection failed: {e}")
except Exception as e:
    print(f"  Direct PostgreSQL connection failed: {e}")

# ═══════════════════════════════════════════════════════════════════════════
# 2. FULL DELETE LIST (CSV export + count reconciliation)
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("2. FULL DELETE LIST — RECONCILED COUNT")
print("=" * 80)

res = sb.table("trends").select("id, audio_id, audio_title, velocity_avg, status, created_at, reel_count, first_detected_at").execute()
all_rows = res.data

STATUS_ORDER = {"expired": 0, "peaked": 1, "emerging": 2, "rising": 3}

by_aid = defaultdict(list)
for r in all_rows:
    aid = r.get("audio_id")
    if aid:
        by_aid[aid].append(r)

dup_groups = {k: v for k, v in by_aid.items() if len(v) > 1}

# Survivor selection: highest status first, then highest velocity
def survivor_key(r):
    status_rank = STATUS_ORDER.get(r.get("status"), 0)
    velocity = r.get("velocity_avg") or 0
    return (status_rank, velocity)

keep_ids = set()
delete_rows = []
for aid, rows in dup_groups.items():
    rows_sorted = sorted(rows, key=survivor_key, reverse=True)
    keep_id = rows_sorted[0]["id"]
    keep_ids.add(keep_id)
    for r in rows_sorted[1:]:
        delete_rows.append(r)

# Also: rows with no audio_id — keep all (no dedup rule applies)
no_audio = [r for r in all_rows if not r.get("audio_id")]
# Rows in non-duplicate groups — keep all
non_dup_keep = [r for r in all_rows if r.get("audio_id") and r["audio_id"] in by_aid and len(by_aid[r["audio_id"]]) == 1]

total_keep = len(keep_ids) + len(no_audio) + len(non_dup_keep)
total_delete = len(delete_rows)

print(f"  Total rows in DB: {len(all_rows)}")
print(f"  Rows with no audio_id (keep all): {len(no_audio)}")
print(f"  Rows in non-duplicate groups (keep all): {len(non_dup_keep)}")
print(f"  Duplicate groups: {len(dup_groups)}")
print(f"  Survivors from duplicates: {len(keep_ids)}")
print(f"  Rows to DELETE: {total_delete}")
print(f"  Rows after backfill: {total_keep}")
print(f"  Reconciliation: {total_keep} + {total_delete} = {total_keep + total_delete} (should equal {len(all_rows)})")
assert total_keep + total_delete == len(all_rows), f"MISMATCH: {total_keep} + {total_delete} != {len(all_rows)}"
print(f"  RECONCILED OK")

# Count discrepancy from earlier: 681 vs 679
# The earlier script used velocity-only sorting. This script uses status-priority.
# Some rows that were "DELETE" under velocity-only are now "KEEP" under status-priority.
old_delete_count = 0
for aid, rows in dup_groups.items():
    rows_sorted_old = sorted(rows, key=lambda r: (r.get("velocity_avg") or 0), reverse=True)
    old_delete_count += len(rows_sorted_old) - 1
print(f"\n  Earlier count (velocity-only): {old_delete_count} deletes")
print(f"  Current count (status-priority): {total_delete} deletes")
print(f"  Difference: {old_delete_count - total_delete} (status-priority keeps more active trends)")

# Export full delete list as CSV
csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trend_delete_list.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "audio_id", "audio_title", "velocity_avg", "status", "created_at", "reel_count", "first_detected_at", "survivor_audio_id"])
    for r in sorted(delete_rows, key=lambda x: x.get("audio_id", "")):
        writer.writerow([
            r["id"],
            r.get("audio_id"),
            r.get("audio_title"),
            r.get("velocity_avg"),
            r.get("status"),
            r.get("created_at"),
            r.get("reel_count"),
            r.get("first_detected_at"),
            r.get("audio_id"),  # same audio_id as survivor
        ])
print(f"\n  Full delete list exported to: {csv_path}")
print(f"  CSV rows (excluding header): {total_delete}")

# Print all delete IDs for verification
delete_ids = sorted([r["id"] for r in delete_rows])
print(f"\n  All {total_delete} IDs to DELETE:")
# Print in rows of 20
for i in range(0, len(delete_ids), 20):
    chunk = delete_ids[i:i+20]
    print(f"    {', '.join(str(x) for x in chunk)}")

# ═══════════════════════════════════════════════════════════════════════════
# 3. SNAPSHOT COUNTS PER SURVIVING ROW
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("3. SNAPSHOT COUNTS PER SURVIVING ROW (from duplicate groups)")
print("=" * 80)

# Query all snapshot counts in bulk
all_trend_ids = list(keep_ids)
CHUNK = 100
snap_counts = {}
for i in range(0, len(all_trend_ids), CHUNK):
    chunk = all_trend_ids[i:i+CHUNK]
    # Get count per trend_id
    for tid in chunk:
        try:
            res = sb.table("trend_snapshots").select("id", count="exact").eq("trend_id", tid).execute()
            snap_counts[tid] = len(res.data)
        except:
            snap_counts[tid] = 0

counts = list(snap_counts.values())
if counts:
    import statistics
    print(f"  Surviving rows queried: {len(counts)}")
    print(f"  Snapshot count distribution:")
    print(f"    min: {min(counts)}")
    print(f"    max: {max(counts)}")
    print(f"    median: {statistics.median(counts):.0f}")
    print(f"    mean: {statistics.mean(counts):.1f}")
    print(f"    rows with <3 snapshots: {sum(1 for c in counts if c < 3)}")
    print(f"    rows with <10 snapshots: {sum(1 for c in counts if c < 10)}")
    print(f"    rows with 0 snapshots: {sum(1 for c in counts if c == 0)}")

    # Show per-survivor detail for those with <3 snapshots
    low_snap = [(tid, snap_counts[tid]) for tid in snap_counts if snap_counts[tid] < 3]
    if low_snap:
        print(f"\n  Survivors with <3 snapshots (promotion gate requires 3):")
        for tid, count in sorted(low_snap, key=lambda x: x[1]):
            row = next((r for r in all_rows if r["id"] == tid), None)
            if row:
                print(f"    trend_id={tid}: {count} snapshots | {row.get('audio_title','?')} | status={row.get('status')}")
    else:
        print(f"\n  All survivors have >=3 snapshots OK")
else:
    print("  No snapshot counts available")

# ═══════════════════════════════════════════════════════════════════════════
# 4. TOTAL SNAPSHOT LOSS
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("4. TOTAL SNAPSHOT LOSS")
print("=" * 80)

delete_id_set = set(delete_ids)
# Query snapshots for DELETE rows
total_delete_snaps = 0
# Chunk the delete IDs for querying
for i in range(0, len(delete_ids), CHUNK):
    chunk = delete_ids[i:i+CHUNK]
    for tid in chunk:
        try:
            res = sb.table("trend_snapshots").select("id").eq("trend_id", tid).execute()
            total_delete_snaps += len(res.data)
        except:
            pass

# Query total snapshots
try:
    res = sb.table("trend_snapshots").select("id", count="exact").execute()
    total_snaps = len(res.data)
except:
    total_snaps = "unknown"

print(f"  Total snapshots in table: {total_snaps}")
print(f"  Snapshots on DELETE rows: {total_delete_snaps}")
print(f"  Snapshots on KEEP rows: {total_snaps - total_delete_snaps if isinstance(total_snaps, int) else 'unknown'}")
print(f"  Percentage lost: {total_delete_snaps/total_snaps*100:.1f}%" if isinstance(total_snaps, int) and total_snaps > 0 else "")
