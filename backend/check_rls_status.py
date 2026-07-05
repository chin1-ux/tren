import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("SUPABASE_DB_URL")

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()
cur.execute("SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;")
rows = cur.fetchall()
print("TABLE NAME                          | RLS ENABLED")
print("-" * 50)
for row in rows:
    print(f"{row[0]:<35} | {row[1]}")
cur.close()
conn.close()
