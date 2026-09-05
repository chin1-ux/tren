import psycopg2
import os
import sys
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("SUPABASE_DB_URL")

# Use UTF-8 stdout to avoid Windows cp1252 issues
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

STATEMENTS = [
    "ALTER TABLE trends ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS trends_public_read ON trends",
    "DROP POLICY IF EXISTS trends_service_write ON trends",
    "CREATE POLICY trends_public_read ON trends FOR SELECT USING (true)",
    "CREATE POLICY trends_service_write ON trends FOR ALL TO service_role USING (true) WITH CHECK (true)",
    "ALTER TABLE reels ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS reels_public_read ON reels",
    "DROP POLICY IF EXISTS reels_service_write ON reels",
    "CREATE POLICY reels_public_read ON reels FOR SELECT USING (true)",
    "CREATE POLICY reels_service_write ON reels FOR ALL TO service_role USING (true) WITH CHECK (true)",
    "ALTER TABLE youtube_shorts ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS youtube_shorts_public_read ON youtube_shorts",
    "DROP POLICY IF EXISTS youtube_shorts_service_write ON youtube_shorts",
    "CREATE POLICY youtube_shorts_public_read ON youtube_shorts FOR SELECT USING (true)",
    "CREATE POLICY youtube_shorts_service_write ON youtube_shorts FOR ALL TO service_role USING (true) WITH CHECK (true)",
]

def main():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
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
        print("Done - RLS applied to trends and reels with zero errors.")
    else:
        print(f"Done with {errors} error(s).")

if __name__ == "__main__":
    main()
