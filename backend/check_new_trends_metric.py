import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
sb = create_client(url, key)

print("=== new_trends_found (from cron_runs table) ===")
res = sb.table("cron_runs").select("run_at, new_trends_found, status").order("run_at", desc=True).limit(20).execute()
for r in res.data:
    print(f"  {str(r.get('run_at',''))[:19]}  new_trends={r.get('new_trends_found')}  status={r.get('status')}")

print("\n=== TOTALS ===")
total = sb.table("cron_runs").select("new_trends_found", count="exact").execute()
values = [r.get("new_trends_found", 0) for r in total.data if r.get("new_trends_found") is not None]
print(f"  Total cron_runs with new_trends_found: {len(values)}")
if values:
    print(f"  Sum of all new_trends_found: {sum(values)}")
    print(f"  Max single run: {max(values)}")
    print(f"  Min single run: {min(values)}")
    print(f"  Avg per run: {sum(values)/len(values):.1f}")
