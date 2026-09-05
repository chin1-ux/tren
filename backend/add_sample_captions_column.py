"""
Migration: add sample_captions column to trends table.

Run once to enable the nightly LLM batch to read top reel captions
for better LLM enrichment context.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL or SUPABASE_DB_URL not set in .env")
    sys.exit(1)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

cur.execute("ALTER TABLE trends ADD COLUMN IF NOT EXISTS sample_captions TEXT;")

conn.commit()
cur.close()
conn.close()
print("Migration complete: trends.sample_captions column added (if not already present).")
