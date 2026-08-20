import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
if not url or not key:
    raise SystemExit("SUPABASE_URL and SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY must be set")
sb = create_client(url, key)

# Query trends for PITTAL, EX-FILES, Musicaltunnel
res = sb.table('trends').select('*').in_('name', ['PITTAL', 'EX-FILES', 'Musicaltunnel']).execute()
print("RAW OUTPUT - Trends for PITTAL, EX-FILES, Musicaltunnel:")
for row in res.data:
    print(row)
