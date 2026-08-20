"""
P-METHOD-1 Cleanup DELETE — Step 1b of 4.
Deletes 13 remaining excess rows from 12 duplicate groups missed by first pass.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
import psycopg2

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise SystemExit("DATABASE_URL must be set")

DELETE_IDS = [226, 367, 613, 629, 668, 750, 823, 844, 892, 896, 900, 908, 913]

assert len(DELETE_IDS) == 13, f"Expected 13 IDs, got {len(DELETE_IDS)}"
assert len(set(DELETE_IDS)) == 13, f"Duplicate IDs in list"

print(f"DELETE target: {len(DELETE_IDS)} rows")
print(f"IDs: {DELETE_IDS}")

conn = psycopg2.connect(DB_URL)
conn.autocommit = False
cur = conn.cursor()

try:
    # Pre-check
    placeholders = ",".join(["%s"] * len(DELETE_IDS))
    cur.execute(f"SELECT COUNT(*) FROM trends WHERE id IN ({placeholders})", DELETE_IDS)
    existing = cur.fetchone()[0]
    print(f"Pre-check: {existing} of {len(DELETE_IDS)} target IDs exist")

    # DELETE with RETURNING
    cur.execute(f"DELETE FROM trends WHERE id IN ({placeholders}) RETURNING id", DELETE_IDS)
    deleted_ids = [row[0] for row in cur.fetchall()]
    deleted_count = len(deleted_ids)
    print(f"DELETE executed: {deleted_count} rows deleted")
    print(f"Deleted IDs: {sorted(deleted_ids)}")

    # Post-check
    cur.execute("SELECT COUNT(*) FROM trends")
    remaining = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM trend_snapshots")
    snaps = cur.fetchone()[0]
    cur.execute("SELECT audio_id, COUNT(*) FROM trends GROUP BY audio_id HAVING COUNT(*) > 1")
    dups = cur.fetchall()

    conn.commit()
    print(f"\nCOMMITTED")
    print(f"Remaining trends: {remaining} (expected: 321)")
    print(f"Remaining snapshots: {snaps}")
    print(f"Remaining duplicate groups: {len(dups)}")
    print(f"Verification: {'PASS' if remaining == 321 and len(dups) == 0 else 'FAIL'}")

except Exception as e:
    conn.rollback()
    print(f"\nERROR: {e}")
    print(f"ROLLED BACK")
    raise
finally:
    cur.close()
    conn.close()
