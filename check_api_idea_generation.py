import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
if not url or not key:
    raise SystemExit("SUPABASE_URL and SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY must be set")
sb = create_client(url, key)

# Get trends table schema to understand available columns
res = sb.table('trends').select('*').limit(1).execute()
if res.data:
    print("TRENDS TABLE COLUMNS:")
    for key in res.data[0].keys():
        print(f"  {key}")
