import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
import psycopg2

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise SystemExit("DATABASE_URL must be set")
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# Check for NULLs in audio_id
cur.execute("SELECT COUNT(*) FROM trends WHERE audio_id IS NULL")
null_count = cur.fetchone()[0]

# Check for remaining duplicates
cur.execute("SELECT audio_id, COUNT(*) as cnt FROM trends GROUP BY audio_id HAVING COUNT(*) > 1")
dups = cur.fetchall()

# Check existing indexes on audio_id
cur.execute("""
    SELECT indexname, indexdef
    FROM pg_indexes
    WHERE tablename = 'trends' AND indexdef LIKE '%audio_id%'
""")
indexes = cur.fetchall()

# Check NOT NULL constraint on audio_id
cur.execute("""
    SELECT is_nullable
    FROM information_schema.columns
    WHERE table_name = 'trends' AND column_name = 'audio_id'
""")
nullable = cur.fetchone()

print(f"NULL audio_ids: {null_count}")
print(f"Remaining duplicate groups: {len(dups)}")
print(f"Existing indexes on audio_id: {indexes}")
print(f"Column nullable: {nullable}")

cur.close()
conn.close()
