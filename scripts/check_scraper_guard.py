import os
import sys
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv('backend/.env')
load_dotenv('.env')

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

def check_github_active_run():
    """Checks GitHub API to see if a scraper run is currently in progress."""
    try:
        import subprocess, json
        cmd = "gh run list --workflow 356465934 --status in_progress --repo chin1-ux/tren --json databaseId"
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if res.stdout.strip():
            runs = json.loads(res.stdout.strip())
            if isinstance(runs, list) and len(runs) > 0:
                return True, f"Active GitHub workflow run {runs[0].get('databaseId')} currently in_progress in chin1-ux/tren."
    except Exception as e:
        pass
    return False, None

def evaluate_guard_logic(cron_rows, now_dt=None, min_gap_minutes=150):
    """
    Pure evaluation logic for scraper guard.
    - Measures elapsed time from run START (run_at).
    - Threshold: 150 minutes (2.5 hours) to guarantee a strict 3-hour cadence.
    - Locks out if an active run is in progress.
    """
    if now_dt is None:
        now_dt = datetime.now(timezone.utc)

    # Rule 1: Check GitHub API for an active in_progress run
    gh_active, gh_msg = check_github_active_run()
    if gh_active:
        return True, f"Skipping: {gh_msg}"

    if not cron_rows:
        return False, "No previous cron runs found. Proceeding."

    # Rule 2: Check database in_progress / queued rows
    for r in cron_rows[:5]:
        st = (r.get("status") or "").lower()
        if st in ("running", "in_progress", "queued", "pending"):
            created_str = r.get("created_at") or r.get("run_at")
            if created_str:
                created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                age_minutes = (now_dt - created_dt).total_seconds() / 60.0
                if age_minutes < 120:
                    return True, f"Skipping: active scraper run in progress (status={st}, started {age_minutes:.1f}m ago)."

    # Rule 3: Find newest completed run with status 'success' or 'partial' (ordered by created_at DESC)
    latest_completed = None
    for r in cron_rows:
        st = (r.get("status") or "").lower()
        if st in ("success", "partial"):
            latest_completed = r
            break

    if not latest_completed:
        return False, "No successful/partial completed runs found. Proceeding."

    # Measure elapsed time strictly from run START (run_at)
    run_at_str = latest_completed.get("run_at")
    if run_at_str:
        start_dt = datetime.fromisoformat(run_at_str.replace("Z", "+00:00"))
    else:
        # Fallback if run_at was null: created_at minus duration_seconds
        created_dt = datetime.fromisoformat(latest_completed["created_at"].replace("Z", "+00:00"))
        dur_sec = float(latest_completed.get("duration_seconds") or 3000)
        start_dt = created_dt - timedelta(seconds=dur_sec)

    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)

    diff_minutes = (now_dt - start_dt).total_seconds() / 60.0

    if diff_minutes < min_gap_minutes:
        return True, f"Skipping: last run started {diff_minutes:.1f}m ago (under {min_gap_minutes}m threshold; status={latest_completed.get('status')}, scraped={latest_completed.get('reels_scraped')})."
    else:
        return False, f"Proceeding: last run started {diff_minutes:.1f}m ago (>={min_gap_minutes}m; status={latest_completed.get('status')}, scraped={latest_completed.get('reels_scraped')})."

def check_guard():
    if not url or not key:
        print("No Supabase credentials found, proceeding.")
        return False

    try:
        from supabase import create_client
        sb = create_client(url, key)
        # Fetch latest runs ordered strictly by created_at DESC (never run_at due to NULLs)
        res = sb.table('cron_runs') \
            .select('id, created_at, run_at, status, reels_scraped, new_reels_count, duration_seconds') \
            .order('created_at', desc=True) \
            .limit(10) \
            .execute()
        
        rows = res.data or []
        skip, msg = evaluate_guard_logic(rows)
        print(msg)
        return skip
    except Exception as e:
        print(f"Warning in scraper guard check: {e}. Proceeding.")
        return False

if __name__ == '__main__':
    skip = check_guard()
    github_output = os.getenv('GITHUB_OUTPUT')
    if github_output:
        with open(github_output, 'a') as f:
            f.write(f"skip={'true' if skip else 'false'}\n")
    if skip:
        print("Scraper guard: SKIP")
    else:
        print("Scraper guard: PROCEED")
