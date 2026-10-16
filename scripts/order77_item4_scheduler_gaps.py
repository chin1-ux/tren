import json
import subprocess
from datetime import datetime

cmd = [
    "gh", "run", "list",
    "--repo", "chin1-ux/tren",
    "--workflow", "scraper_cron.yml",
    "--limit", "40",
    "--json", "databaseId,status,conclusion,createdAt,startedAt,updatedAt,event"
]

res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
if res.returncode != 0:
    # Try workflow name if file name not recognized
    cmd[4] = "Trendrop Scheduled Scraper Pipeline Cron"
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

runs = json.loads(res.stdout) if res.stdout else []

print("=" * 95)
print("ORDER 77 ITEM 4: SCHEDULER GAPS AUDIT (LAST 40 RUNS OF SCRAPER CRON ON chin1-ux/tren)")
print("=" * 95)
print(f"{'Run ID':<14} | {'Started At (UTC)':<20} | {'Status':<11} | {'Conclusion':<11} | {'Gap From Prev'}")
print("-" * 95)

prev_start = None
gaps = []

# Sort oldest to newest for chronological gaps
runs_chrono = sorted(runs, key=lambda x: x.get("startedAt") or x.get("createdAt") or "")

for r in reversed(runs_chrono): # print newest first
    run_id = r.get("databaseId")
    started = (r.get("startedAt") or r.get("createdAt") or "")[:19].replace("T", " ")
    status = r.get("status") or ""
    conclusion = r.get("conclusion") or ""
    
    # Calculate gap to previous run
    gap_str = "N/A (Latest)"
    dt = datetime.fromisoformat((r.get("startedAt") or r.get("createdAt") or "").replace("Z", "+00:00"))
    if prev_start:
        gap_sec = (prev_start - dt).total_seconds()
        gap_hrs = gap_sec / 3600.0
        gap_str = f"{gap_hrs:.2f} hrs ({gap_sec/60:.0f} min)"
        gaps.append(gap_hrs)
    prev_start = dt
    
    print(f"{run_id:<14} | {started:<20} | {status:<11} | {conclusion:<11} | {gap_str}")

print("-" * 95)
if gaps:
    print(f"Total Runs Analyzed: {len(runs)}")
    print(f"Average Gap Between Runs: {sum(gaps)/len(gaps):.2f} hours")
    print(f"Max Gap Between Runs    : {max(gaps):.2f} hours")
    print(f"Min Gap Between Runs    : {min(gaps):.2f} hours")
    gaps_gt_3h = sum(1 for g in gaps if g > 3.5)
    print(f"Runs with gap > 3.5 hours: {gaps_gt_3h}/{len(gaps)} ({gaps_gt_3h/len(gaps)*100:.1f}%)")
print("=" * 95)
