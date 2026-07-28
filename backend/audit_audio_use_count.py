#!/usr/bin/env python3
"""
Query ALL trends showing old vs corrected audio_use_count.
Runs BEFORE and AFTER the refresher to produce a comparison table.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import psycopg2
import datetime

DB_URL = os.environ["SUPABASE_DB_URL"]
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

print(f"\n=== ALL TRENDS — audio_use_count audit ===")
print(f"Timestamp: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n")

cur.execute("""
    SELECT
        t.id,
        t.audio_title,
        t.audio_artist,
        t.audio_id,
        t.status,
        t.audio_use_count AS stored_count,
        COALESCE(
            (SELECT MAX(r.audio_use_count)
             FROM reels r
             WHERE (t.audio_id IS NOT NULL AND r.audio_id = t.audio_id)
                OR (t.audio_id IS NULL AND r.audio_title = t.audio_title AND r.audio_artist = t.audio_artist)
            ), 0
        ) AS live_max
    FROM trends t
    ORDER BY t.id
""")

rows = cur.fetchall()
cols = [d[0] for d in cur.description]

stale_count = 0
print(f"{'ID':>4}  {'Audio Title':<30}  {'Status':<10}  {'Stored':>8}  {'LiveMax':>8}  {'Delta':>8}  {'Stale?'}")
print("-" * 95)
for row in rows:
    row_dict = dict(zip(cols, row))
    stored = row_dict['stored_count'] or 0
    live = row_dict['live_max'] or 0
    delta = live - stored
    stale = delta > 0
    if stale:
        stale_count += 1
    title = (row_dict['audio_title'] or '')[:30]
    status = (row_dict['status'] or '')[:10]
    flag = "STALE" if stale else "ok"
    print(f"{row_dict['id']:>4}  {title:<30}  {status:<10}  {stored:>8,}  {live:>8,}  {delta:>+8,}  {flag}")

print(f"\nTotal trends: {len(rows)}, Stale rows: {stale_count}")
cur.close()
conn.close()
