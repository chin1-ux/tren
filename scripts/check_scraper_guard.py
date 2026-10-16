import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv('backend/.env')
load_dotenv('.env')

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

def evaluate_guard_logic(cron_rows, now_dt=None, min_gap_minutes=165):
    """
    Pure evaluation logic for scraper guard.
    cron_rows: list of dicts from cron_runs ordered by created_at DESC.
    """
    if now_dt is None:
        now_dt = datetime.now(timezone.utc)

    if not cron_rows:
        return False, "No previous cron runs found. Proceeding."

    # Rule 1: If a run is currently in progress or queued, exit immediately (skip)
    for r in cron_rows[:5]:
        st = (r.get("status") or "").lower()
        if st in ("running", "in_progress", "queued", "pending"):
            created_str = r.get("created_at") or r.get("run_at")
            if created_str:
                created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                age_minutes = (now_dt - created_dt).total_seconds() / 60.0
                # If running for under 120 minutes, assume active lock
                if age_minutes < 120:
                    return True, f"Skipping: active scraper run in progress (status={st}, started {age_minutes:.1f}m ago)."

    # Rule 2: Find newest completed run with status 'success' or 'partial' (ordered by created_at)
    # Stop filtering on reels_scraped > 0!
    latest_completed = None
    for r in cron_rows:
        st = (r.get("status") or "").lower()
        if st in ("success", "partial"):
            latest_completed = r
            break

    if not latest_completed:
        return False, "No successful/partial completed runs found. Proceeding."

    # Use created_at (guaranteed NOT NULL), fallback to run_at
    ts_str = latest_completed.get("created_at") or latest_completed.get("run_at")
    if not ts_str:
        return False, "No valid timestamp on latest run. Proceeding."

    last_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    diff_minutes = (now_dt - last_dt).total_seconds() / 60.0

    if diff_minutes < min_gap_minutes:
        return True, f"Skipping: last completed run was {diff_minutes:.1f}m ago (under {min_gap_minutes}m threshold; status={latest_completed.get('status')}, scraped={latest_completed.get('reels_scraped')})."
    else:
        return False, f"Proceeding: last completed run was {diff_minutes:.1f}m ago (>={min_gap_minutes}m; status={latest_completed.get('status')}, scraped={latest_completed.get('reels_scraped')})."

def check_guard():
    if not url or not key:
        print("No Supabase credentials found, proceeding.")
        return False

    try:
        from supabase import create_client
        sb = create_client(url, key)
        # Fetch latest runs ordered strictly by created_at DESC (never run_at due to NULLs)
        res = sb.table('cron_runs') \
            .select('id, created_at, run_at, status, reels_scraped, new_reels_count') \
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
