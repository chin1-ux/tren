#!/usr/bin/env python3
"""
Live DB query for Pati Manila audio_use_count.
Queries the LIVE database, NOT the backup snapshot.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
import datetime

DB_URL = os.environ["SUPABASE_DB_URL"]

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# 1. Find all trends matching "Pati Manila" (song title or audio title)
cur.execute("""
    SELECT
        id,
        audio_title,
        audio_artist,
        audio_id,
        audio_use_count,
        status,
        reel_count,
        velocity_avg,
        first_detected_at,
        llm_classified_at
    FROM trends
    WHERE
        lower(audio_title) LIKE lower('%Pati Manila%')
        OR lower(audio_artist) LIKE lower('%Pati Manila%')
    ORDER BY first_detected_at DESC
""")

rows = cur.fetchall()
cols = [d[0] for d in cur.description]

print(f"\n=== LIVE DB QUERY — {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC ===")
print(f"Found {len(rows)} row(s) matching 'Pati Manila'\n")

for row in rows:
    for col, val in zip(cols, row):
        print(f"  {col}: {val}")
    print()

# 2. Also check reels table for this audio
cur.execute("""
    SELECT
        COUNT(*) as reel_count,
        MAX(audio_use_count) as max_audio_use_count,
        MIN(audio_use_count) as min_audio_use_count,
        MAX(view_count) as max_view_count,
        MAX(scraped_at) as latest_scraped_at
    FROM reels
    WHERE
        lower(audio_title) LIKE lower('%Pati Manila%')
        OR lower(audio_artist) LIKE lower('%Pati Manila%')
""")

reels_row = cur.fetchone()
print("=== REELS TABLE AGGREGATE ===")
print(f"  reel_count (rows in reels table): {reels_row[0]}")
print(f"  max_audio_use_count: {reels_row[1]}")
print(f"  min_audio_use_count: {reels_row[2]}")
print(f"  max_view_count: {reels_row[3]}")
print(f"  latest_scraped_at: {reels_row[4]}")

cur.close()
conn.close()
print("\n=== QUERY COMPLETE (LIVE DB, NOT BACKUP) ===")
