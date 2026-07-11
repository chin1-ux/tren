"""
Migration: add new_reels_count column to cron_runs table.
Run once. Safe to re-run (uses IF NOT EXISTS equivalent via try/except).
"""
import os, sys
sys.path.insert(0, 'backend')
from supabase import create_client
from dotenv import load_dotenv
load_dotenv('backend/.env')

# Must use service role key for DDL
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
sb = create_client(url, key)

# Verify current columns
r = sb.table('cron_runs').select('*').limit(1).execute()
existing_cols = list(r.data[0].keys()) if r.data else []
print("Current cron_runs columns:", existing_cols)

if 'new_reels_count' in existing_cols:
    print("Column already exists. Nothing to do.")
    sys.exit(0)

# Supabase REST API doesn't support DDL — use the Postgres URL directly
import subprocess, sys

db_url = os.getenv('SUPABASE_DB_URL')
if not db_url:
    print()
    print("ERROR: SUPABASE_DB_URL not set.")
    print("Add it to backend/.env, then re-run this script.")
    print("Format: postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres")
    print()
    print("Alternatively, run this SQL manually in Supabase SQL Editor:")
    print()
    print("  ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS new_reels_count INTEGER DEFAULT 0;")
    print("  COMMENT ON COLUMN cron_runs.new_reels_count IS 'Number of new reels inserted by scraper in this run';")
    sys.exit(1)

sql = "ALTER TABLE cron_runs ADD COLUMN IF NOT EXISTS new_reels_count INTEGER DEFAULT 0;"
result = subprocess.run(
    ['python', '-c',
     f"import psycopg2; conn=psycopg2.connect('{db_url}'); cur=conn.cursor(); cur.execute(\"{sql}\"); conn.commit(); print('Done.'); conn.close()"],
    capture_output=True, text=True
)
print("stdout:", result.stdout)
print("stderr:", result.stderr)
print("returncode:", result.returncode)
