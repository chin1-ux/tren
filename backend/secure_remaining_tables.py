import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("SUPABASE_DB_URL")

STATEMENTS = [
    # creator_baselines (service-role only)
    "ALTER TABLE creator_baselines ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS creator_baselines_public_read ON creator_baselines",
    "DROP POLICY IF EXISTS creator_baselines_service_write ON creator_baselines",
    # Service role has full access (SELECT, INSERT, UPDATE, DELETE)
    "CREATE POLICY creator_baselines_service_write ON creator_baselines FOR ALL TO service_role USING (true) WITH CHECK (true)",

    # trend_snapshots (public read, service-role write)
    "ALTER TABLE trend_snapshots ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS trend_snapshots_public_read ON trend_snapshots",
    "DROP POLICY IF EXISTS trend_snapshots_service_write ON trend_snapshots",
    "CREATE POLICY trend_snapshots_public_read ON trend_snapshots FOR SELECT USING (true)",
    "CREATE POLICY trend_snapshots_service_write ON trend_snapshots FOR ALL TO service_role USING (true) WITH CHECK (true)",
]

def main():
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
        
    if not DB_URL:
        print("Error: SUPABASE_DB_URL not found in environment variables.")
        return
        
    try:
        print("Testing database connection...")
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cur = conn.cursor()
        print("OK: Connected successfully.")
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        return

    print("Executing security statements...")
    errors = 0
    for stmt in STATEMENTS:
        try:
            cur.execute(stmt + ";")
            print(f"OK  {stmt[:70]}...")
        except Exception as e:
            print(f"ERR {stmt[:70]}... => {e}")
            errors += 1
    cur.close()
    conn.close()
    if errors == 0:
        print("Done - RLS and policies applied to creator_baselines and trend_snapshots.")
    else:
        print(f"Done with {errors} error(s).")

if __name__ == "__main__":
    main()
