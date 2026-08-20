import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
if not url or not key:
    raise SystemExit("SUPABASE_URL and SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY must be set")
sb = create_client(url, key)

# Query last 10 cron runs
res = sb.table('cron_runs').select('*').order('run_at', desc=True).limit(10).execute()
print("RAW OUTPUT - Last 10 cron runs:")
for row in res.data:
    print(row)
