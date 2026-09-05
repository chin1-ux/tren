import os, sys, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client
from datetime import datetime
from collections import defaultdict

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
sb = create_client(url, key)

deleted = []
with open("trend_delete_list.csv", "r", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        deleted.append({"id": int(row["id"]), "created_at": row["created_at"]})
print(f"Deleted rows: {len(deleted)}")

runs = sb.table("cron_runs").select("run_at, new_trends_found").order("run_at").execute()
run_times = []
for r in runs.data:
    rt = r.get("run_at", "")
    if rt.endswith("Z"):
        rt = rt[:-1] + "+00:00"
    try:
        run_times.append((datetime.fromisoformat(rt), r.get("new_trends_found", 0)))
    except:
        pass
run_times.sort()
print(f"Cron runs: {len(run_times)}")

# Match each deleted row to the cron run that created it
run_dupes = defaultdict(int)
matched = 0
unmatched = 0
for d in deleted:
    ca = d["created_at"]
    if ca.endswith("Z"):
        ca = ca[:-1] + "+00:00"
    try:
        created_dt = datetime.fromisoformat(ca)
    except:
        unmatched += 1
        continue
    for run_at, ntrends in run_times:
        if created_dt <= run_at:
            run_dupes[str(run_at)[:19]] += 1
            matched += 1
            break
    else:
        unmatched += 1

print(f"\nMatched to cron run: {matched}")
print(f"Unmatched (external pipeline or no run): {unmatched}")
print(f"Runs that created duplicates: {len(run_dupes)}")

# For each run that created dupes, show its new_trends_found vs how many were dupes
print(f"\nRun-by-run breakdown (runs with duplicates):")
total_dupes_from_runs = 0
for run_at, dupe_count in sorted(run_dupes.items()):
    # Find the new_trends_found for this run
    nt = next((n for t, n in run_times if str(t)[:19] == run_at), "?")
    total_dupes_from_runs += dupe_count
    print(f"  {run_at}  new_trends_found={nt}  dupes_created={dupe_count}")

print(f"\nTotal duplicates attributable to cron runs: {total_dupes_from_runs}")
print(f"Total new_trends_found across all runs: {sum(n for _, n in run_times)}")
print(f"Inflation: {total_dupes_from_runs} of {sum(n for _, n in run_times)} new_trends_found were duplicates")
pct = total_dupes_from_runs / max(sum(n for _, n in run_times), 1) * 100
print(f"Percentage inflated: {pct:.1f}%")
