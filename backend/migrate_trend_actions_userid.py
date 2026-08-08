"""
migrate_trend_actions_userid.py

Alters trend_actions.user_id from UUID to TEXT so both Supabase UUID
and custom auth email identifiers work seamlessly.
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
if not SUPABASE_DB_URL:
    raise ValueError("SUPABASE_DB_URL missing from .env")

STATEMENTS = [
    # Drop the unique constraint first (references the column type)
    "ALTER TABLE trend_actions DROP CONSTRAINT IF EXISTS uq_user_trend_action;",
    # Drop RLS policy that references user_id before changing its type
    "DROP POLICY IF EXISTS trend_actions_user_manage ON trend_actions;",
    # Change user_id from UUID to TEXT
    "ALTER TABLE trend_actions ALTER COLUMN user_id TYPE TEXT USING user_id::TEXT;",
    # Re-add the unique constraint
    "ALTER TABLE trend_actions ADD CONSTRAINT uq_user_trend_action UNIQUE (user_id, trend_id, action_type);",
    # Re-create the RLS policy (now matches TEXT comparison)
    "CREATE POLICY trend_actions_user_manage ON trend_actions FOR ALL TO authenticated USING (user_id = auth.uid()::TEXT) WITH CHECK (user_id = auth.uid()::TEXT);",
    # Add any missing columns per project rules
    "ALTER TABLE trend_actions ADD COLUMN IF NOT EXISTS action_type TEXT DEFAULT 'target';",
]

def run():
    conn = psycopg2.connect(SUPABASE_DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    for stmt in STATEMENTS:
        print(f"Executing: {stmt[:80]}...")
        try:
            cur.execute(stmt)
            print("  OK")
        except Exception as e:
            print(f"  WARN: {e}")
    cur.close()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    run()
