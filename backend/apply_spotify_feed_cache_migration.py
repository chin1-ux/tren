import os, sys
from dotenv import load_dotenv
import psycopg2

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

DB_URL = os.getenv('SUPABASE_DB_URL')
if not DB_URL:
    print('Error: SUPABASE_DB_URL not set in environment.', file=sys.stderr)
    sys.exit(1)

SQL_FILE = os.path.join(os.path.dirname(__file__), "migrations", "add_spotify_feed_cache.sql")

with open(SQL_FILE, "r", encoding="utf-8") as f:
    sql_content = f.read()

print("Applying migration add_spotify_feed_cache.sql...")

conn = psycopg2.connect(DB_URL)
conn.autocommit = True
cur = conn.cursor()

try:
    cur.execute(sql_content)
    print("[OK] Migration executed successfully!")
    
    # Verify table structure
    cur.execute("""
        SELECT column_name, data_type 
        from information_schema.columns 
        WHERE table_name = 'spotify_feed_cache';
    """)
    cols = cur.fetchall()
    print("\nTable 'spotify_feed_cache' Columns Verified:")
    for col in cols:
        print(f"  - {col[0]} ({col[1]})")

except Exception as e:
    print(f"Error applying migration: {e}", file=sys.stderr)
    sys.exit(1)
finally:
    cur.close()
    conn.close()
