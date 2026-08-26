"""
Migration: Add format trend detection columns to trends table.
"""
import os
import sys
from dotenv import load_dotenv
import urllib.request, json

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://gxxpvstrvphwhlqbvymv.supabase.co")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

if not SERVICE_KEY:
    print("ERROR: SUPABASE_KEY not set")
    sys.exit(1)

hdrs = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
}

# Add new columns via SQL (Supabase RPC)
columns_to_add = [
    ("dominant_format", "text DEFAULT 'unknown'"),
    ("format_replication_rate", "real DEFAULT 0.0"),
    ("format_concepts", "jsonb DEFAULT '[]'::jsonb"),
    ("creator_diversity", "real DEFAULT 0.0"),
    ("is_format_trend", "boolean DEFAULT false"),
    ("format_trend_score", "real DEFAULT 0.0"),
]

for col_name, col_def in columns_to_add:
    sql = f"ALTER TABLE trends ADD COLUMN IF NOT EXISTS {col_name} {col_def};"
    data = json.dumps({"query": sql}).encode()
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
        data=data,
        headers=hdrs,
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        print(f"  Added {col_name}: OK ({resp.status})")
    except Exception as e:
        # Try direct SQL via PostgREST
        print(f"  RPC failed for {col_name}: {e}")
        print(f"  Trying alternative method...")
        # Column may already exist or Supabase may not have exec_sql
        # Try inserting with the new columns to see if they exist
        break

# Test: try to query with new columns
print("\nVerifying columns exist...")
test_data = json.dumps({}).encode()
try:
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/trends?select=dominant_format,format_replication_rate,format_concepts,creator_diversity,is_format_trend,format_trend_score&limit=1",
        headers=hdrs,
    )
    resp = urllib.request.urlopen(req, timeout=15)
    result = json.loads(resp.read().decode())
    print(f"  Columns verified: {list(result[0].keys()) if result else 'empty'}")
except Exception as e:
    err_msg = str(e)
    try:
        err_msg = e.read().decode()[:300]
    except:
        pass
    print(f"  Columns may not exist yet: {err_msg}")
    print("  Note: If using Supabase, add columns via the Dashboard SQL editor:")
    print("  ALTER TABLE trends ADD COLUMN IF NOT EXISTS dominant_format text DEFAULT 'unknown';")
    print("  ALTER TABLE trends ADD COLUMN IF NOT EXISTS format_replication_rate real DEFAULT 0.0;")
    print("  ALTER TABLE trends ADD COLUMN IF NOT EXISTS format_concepts jsonb DEFAULT '[]'::jsonb;")
    print("  ALTER TABLE trends ADD COLUMN IF NOT EXISTS creator_diversity real DEFAULT 0.0;")
    print("  ALTER TABLE trends ADD COLUMN IF NOT EXISTS is_format_trend boolean DEFAULT false;")
    print("  ALTER TABLE trends ADD COLUMN IF NOT EXISTS format_trend_score real DEFAULT 0.0;")
