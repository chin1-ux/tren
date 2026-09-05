import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client
from collections import defaultdict

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
sb = create_client(url, key)

res = sb.table("trends").select("id, audio_id, audio_title, velocity_avg, status, created_at").execute()
all_rows = res.data
print(f"Current total: {len(all_rows)}")

by_aid = defaultdict(list)
for r in all_rows:
    aid = r.get("audio_id")
    if aid:
        by_aid[str(aid)].append(r)

dups = {k: v for k, v in by_aid.items() if len(v) > 1}
print(f"Remaining duplicate groups: {len(dups)}")
print(f"Rows in duplicate groups: {sum(len(v) for v in dups.values())}")
print(f"Excess rows still to delete: {sum(len(v) - 1 for v in dups.values())}")
print()

STATUS_ORDER = {"expired": 0, "peaked": 1, "emerging": 2, "rising": 3}
for aid, rows in sorted(dups.items(), key=lambda x: len(x[1]), reverse=True):
    rows_sorted = sorted(rows, key=lambda r: (STATUS_ORDER.get(r.get("status"), 0), r.get("velocity_avg") or 0), reverse=True)
    survivor = rows_sorted[0]
    deletes = rows_sorted[1:]
    title = (survivor.get("audio_title") or "?")[:50]
    print(f"GROUP: {title} (audio_id={aid}, {len(rows)} rows)")
    print(f"  SURVIVOR: id={survivor['id']} vel={survivor.get('velocity_avg') or 0:.0f} status={survivor.get('status')}")
    for r in deletes:
        print(f"  DELETE:   id={r['id']} vel={r.get('velocity_avg') or 0:.0f} status={r.get('status')}")
    print()

# Collect the IDs to delete
delete_ids = []
for aid, rows in dups.items():
    rows_sorted = sorted(rows, key=lambda r: (STATUS_ORDER.get(r.get("status"), 0), r.get("velocity_avg") or 0), reverse=True)
    for r in rows_sorted[1:]:
        delete_ids.append(r["id"])
delete_ids.sort()
print(f"Additional IDs to delete: {len(delete_ids)}")
print(f"IDs: {delete_ids}")
print(f"After cleanup: {len(all_rows) - len(delete_ids)} rows")
