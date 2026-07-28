#!/usr/bin/env python3
"""
One-shot backfill: update audio_use_count for ALL trends (not just active ones)
by reading max(audio_use_count) from the reels table.

Safe to run multiple times (only writes if live_max > stored).
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import psycopg2
import datetime

DB_URL = os.environ["SUPABASE_DB_URL"]
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

print(f"\n=== BACKFILL audio_use_count — {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC ===\n")

# Get all trends with their live max from reels
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

updated = 0
skipped = 0

for row in rows:
    d = dict(zip(cols, row))
    stored = d['stored_count'] or 0
    live = d['live_max'] or 0
    delta = live - stored

    if delta > 0:
        cur.execute(
            "UPDATE trends SET audio_use_count = %s WHERE id = %s",
            (live, d['id'])
        )
        print(f"  UPDATED id={d['id']:>3} '{d['audio_title'][:35]}' [{d['status']}]: {stored:>9,} -> {live:>9,} (delta={delta:+,})")
        updated += 1
    else:
        print(f"  ok     id={d['id']:>3} '{d['audio_title'][:35]}' [{d['status']}]: {stored:>9,}  (no change)")
        skipped += 1

conn.commit()
cur.close()
conn.close()

print(f"\n=== DONE: {updated} rows updated, {skipped} rows already current ===")
