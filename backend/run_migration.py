"""
Add format detection columns to trends table via Supabase SQL.
Run this once to set up the schema.
"""
import os, sys
from dotenv import load_dotenv
import urllib.request, json

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://gxxpvstrvphwhlqbvymv.supabase.co")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

if not SERVICE_KEY:
    print("ERROR: Set SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY")
    sys.exit(1)

# SQL commands to add columns
sql_commands = [
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS dominant_format text DEFAULT 'unknown';",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS format_replication_rate real DEFAULT 0.0;",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS format_concepts jsonb DEFAULT '[]'::jsonb;",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS creator_diversity real DEFAULT 0.0;",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS is_format_trend boolean DEFAULT false;",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS format_trend_score real DEFAULT 0.0;",
]

# Try using Supabase SQL editor endpoint
for sql in sql_commands:
    col_name = sql.split("ADD COLUMN IF NOT EXISTS")[1].split()[0]
    data = json.dumps({"query": sql}).encode()
    
    # Method 1: Try rpc/exec_sql
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
        data=data,
        headers={
            "apikey": SERVICE_KEY,
            "Authorization": f"Bearer {SERVICE_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        print(f"  {col_name}: OK ({resp.status})")
        continue
    except Exception as e:
        pass
    
    # Method 2: Try direct SQL via PostgREST
    print(f"  {col_name}: RPC not available, trying alternative...")
    break

# Verify by querying the columns
print("\nVerifying columns...")
req = urllib.request.Request(
    f"{SUPABASE_URL}/rest/v1/trends?select=dominant_format,format_replication_rate,format_concepts,creator_diversity,is_format_trend,format_trend_score&limit=1",
    headers={
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
    },
)
try:
    resp = urllib.request.urlopen(req, timeout=15)
    result = json.loads(resp.read().decode())
    if result:
        print(f"  VERIFIED: Columns exist! Sample: {json.dumps(result[0], default=str)[:300]}")
    else:
        print("  Table is empty but columns should exist")
except Exception as e:
    err = str(e)
    try:
        err = e.read().decode()[:500]
    except:
        pass
    print(f"  COLUMNS NOT FOUND: {err}")
    print("\n  MANUAL ACTION REQUIRED:")
    print("  Go to Supabase Dashboard > SQL Editor and run:")
    print("  ---")
    for sql in sql_commands:
        print(f"  {sql}")
    print("  ---")
