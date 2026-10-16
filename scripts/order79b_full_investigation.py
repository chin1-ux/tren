import os
import sys
import json
import subprocess
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv('backend/.env')
load_dotenv('.env')

from supabase import create_client
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
sb = create_client(url, key)

lines = []
lines.append("=" * 80)
lines.append("ORDER 79B & 79C: WORKFLOW MAP, DB DUPLICATION & LIFECYCLE AUDIT")
lines.append(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
lines.append("=" * 80)

# 1. WORKFLOW MAP for chin1-ux/tren
lines.append("\n--- 1. WORKFLOW MAP FOR chin1-ux/tren (ALL WORKFLOWS) ---")
res = subprocess.run("gh workflow list --all --repo chin1-ux/tren", shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
lines.append(res.stdout.strip())

# Check recent runs of Scraper and Trend Refresh
lines.append("\n--- 2. RECENT RUNS OF SCRAPER & REFRESH WORKFLOWS IN chin1-ux/tren ---")
res_runs = subprocess.run("gh run list --repo chin1-ux/tren --limit 20", shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
lines.append(res_runs.stdout.strip())

# 3. Check duplicate reels in Supabase
lines.append("\n--- 3. DUPLICATE REELS IN DATABASE ---")
try:
    # Query sample of reels to inspect duplicate reel_id count
    # Since we can't do raw SQL GROUP BY directly without RPC, query recent 2000 reels and check duplicate rate
    r_reels = sb.table("reels").select("id, reel_id, audio_id, scraped_at").order("id", desc=True).limit(5000).execute()
    reels_data = r_reels.data or []
    seen = {}
    duplicates = []
    for r in reels_data:
        rid = r.get("reel_id")
        if rid:
            if rid in seen:
                duplicates.append((rid, r.get("id"), seen[rid]))
            else:
                seen[rid] = r.get("id")
    
    lines.append(f"Analyzed sample of {len(reels_data)} latest reels:")
    lines.append(f"  Unique reel_ids in sample: {len(seen)}")
    lines.append(f"  Duplicate reel_ids in sample: {len(duplicates)}")
    lines.append(f"  Sample duplication rate: {(len(duplicates) / len(reels_data) * 100):.2f}%")
    if duplicates:
        lines.append("  Sample duplicates (reel_id, dup_id, first_id):")
        for d in duplicates[:5]:
            lines.append(f"    Reel {d[0]}: ID {d[1]} and ID {d[2]}")
except Exception as e:
    lines.append(f"  Error checking duplicate reels: {e}")

# 4. Check cron_runs history to inspect scheduler gaps and job execution
lines.append("\n--- 4. LATEST 10 CRON_RUNS IN SUPABASE ---")
try:
    r_cron = sb.table("cron_runs").select("id, run_at, created_at, status, reels_scraped, new_reels_count").order("created_at", desc=True).limit(10).execute()
    cron_rows = r_cron.data or []
    for row in cron_rows:
        lines.append(f"  Run ID={row.get('id'):<6} | CreatedAt={row.get('created_at')} | RunAt={str(row.get('run_at')):<26} | Status={row.get('status'):<8} | Scraped={row.get('reels_scraped')} | New={row.get('new_reels_count')}")
except Exception as e:
    lines.append(f"  Error querying cron_runs: {e}")

output_text = "\n".join(lines)
with open("evidence/order79/workflow_map_and_root_cause.txt", "w", encoding="utf-8") as f:
    f.write(output_text)
print(output_text)
