"""
Query GitHub Actions run history for the scraper workflow.
Requires GH_TOKEN env var (Personal Access Token with repo/actions:read scope).

Usage:
  Set GH_TOKEN in backend/.env, then run:
  python scratch/check_gh_actions.py
"""
import os, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, 'backend')
from dotenv import load_dotenv
load_dotenv('backend/.env')

try:
    import requests
except ImportError:
    print("requests not installed. Run: pip install requests")
    sys.exit(1)

from datetime import datetime, timezone, timedelta

GH_TOKEN = os.getenv('GH_TOKEN') or os.getenv('GITHUB_TOKEN')
REPO = 'ch1n-may/trendrop'
WORKFLOW = 'scraper.yml'

if not GH_TOKEN:
    print("ERROR: GH_TOKEN not set.")
    print()
    print("Steps to fix:")
    print("1. Go to https://github.com/settings/tokens/new")
    print("2. Create a Classic token with scopes: repo (or at minimum: actions:read, metadata:read)")
    print("3. Add to backend/.env:  GH_TOKEN=ghp_xxxxxxxxxxxx")
    print("4. Re-run this script.")
    sys.exit(1)

headers = {
    'Authorization': f'Bearer {GH_TOKEN}',
    'Accept': 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
}

url = f'https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW}/runs?per_page=20'
resp = requests.get(url, headers=headers, timeout=15)

if resp.status_code == 401:
    print("ERROR: Token is invalid or expired.")
    sys.exit(1)
elif resp.status_code == 403:
    print("ERROR: Token lacks permissions (need actions:read scope on this repo).")
    sys.exit(1)
elif resp.status_code != 200:
    print(f"ERROR: GitHub API returned {resp.status_code}: {resp.text[:300]}")
    sys.exit(1)

data = resp.json()
runs = data.get('workflow_runs', [])
print(f"=== GITHUB ACTIONS: {WORKFLOW} — {len(runs)} most recent runs ===")
print()
print("%-12s %-22s %-22s %-12s %-12s %s" % (
    "run_id", "created_at (UTC)", "updated_at (UTC)", "status", "conclusion", "trigger"))
print("-" * 110)

for r in runs:
    created = r.get('created_at', '')[:19]
    updated = r.get('updated_at', '')[:19]
    print("%-12s %-22s %-22s %-12s %-12s %s" % (
        r.get('id', ''),
        created,
        updated,
        r.get('status', ''),
        r.get('conclusion', '') or '(running)',
        r.get('event', '')
    ))

# ── Check the 2026-07-11 18:00 UTC slot specifically ──────────────────────────
print()
print("=== CHECKING 2026-07-11 18:00 UTC SCHEDULED SLOT ===")
target_start = datetime(2026, 7, 11, 17, 30, tzinfo=timezone.utc)  # 30min window
target_end   = datetime(2026, 7, 11, 18, 30, tzinfo=timezone.utc)

slot_runs = []
for r in runs:
    created_str = r.get('created_at', '')
    if created_str:
        try:
            created_dt = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
            if target_start <= created_dt <= target_end:
                slot_runs.append(r)
        except Exception:
            pass

if slot_runs:
    print(f"Found {len(slot_runs)} run(s) in the 17:30-18:30 UTC window:")
    for r in slot_runs:
        print(f"  run_id={r.get('id')}  created={r.get('created_at')}  status={r.get('status')}  conclusion={r.get('conclusion')}  trigger={r.get('event')}")
else:
    print("NO RUNS found in the 17:30-18:30 UTC window on 2026-07-11.")
    print("This confirms the 18:00 UTC scheduled run DID NOT FIRE on GitHub's side.")
    print("Possible causes:")
    print("  - GitHub Actions scheduler delay/skip (common for low-traffic repos)")
    print("  - Workflow was disabled or paused")
    print("  - Repository had no activity and GH put the cron to sleep")
