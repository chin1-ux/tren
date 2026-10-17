import os
import sys
import subprocess
import json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv("backend/.env")
load_dotenv(".env")

def check_guard_v3(min_gap_minutes: int = None):
    """
    Guard v3:
    - Queries GitHub API for recent scraper_cron runs.
    - Measures elapsed time from run START (created_at).
    - Any run started within the threshold (default 600m / 10h, configurable via SCRAPER_GUARD_MIN_GAP_MINUTES) blocks execution.
    - Consumes 0 Supabase egress.
    """
    if min_gap_minutes is None:
        try:
            min_gap_minutes = int(os.getenv("SCRAPER_GUARD_MIN_GAP_MINUTES", "600"))
        except (ValueError, TypeError):
            min_gap_minutes = 600

    now_dt = datetime.now(timezone.utc)
    current_run_id = os.getenv("GITHUB_RUN_ID")
    repo = os.getenv("GITHUB_REPOSITORY", "chin1-ux/tren")
    gh_token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    
    print(f"=== SCRAPER GUARD V3 CHECK @ {now_dt.strftime('%Y-%m-%d %H:%M:%S UTC')} ===")
    print(f"Target Repo: {repo} | Current Run ID: {current_run_id} | Gap Threshold: {min_gap_minutes}m")
    
    runs = []
    
    # Attempt 1: GitHub API via gh CLI or curl
    try:
        cmd = ["gh", "run", "list", "--workflow", "scraper_cron.yml", "--repo", repo, "--limit", "10", "--json", "databaseId,createdAt,status,conclusion"]
        env = os.environ.copy()
        if gh_token:
            env["GH_TOKEN"] = gh_token
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=15)
        if res.returncode == 0 and res.stdout.strip():
            runs = json.loads(res.stdout.strip())
            print(f"Retrieved {len(runs)} recent workflow runs from GitHub API.")
    except Exception as e:
        print(f"GitHub API query via gh CLI failed: {e}")

    # Fallback if gh CLI unavailable: direct requests/urllib
    if not runs and gh_token:
        try:
            import urllib.request
            req = urllib.request.Request(
                f"https://api.github.com/repos/{repo}/actions/workflows/scraper_cron.yml/runs?per_page=10",
                headers={
                    "Authorization": f"Bearer {gh_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "GuardV3-Client"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                for r in data.get("workflow_runs", []):
                    runs.append({
                        "databaseId": r.get("id"),
                        "createdAt": r.get("created_at"),
                        "status": r.get("status"),
                        "conclusion": r.get("conclusion")
                    })
            print(f"Retrieved {len(runs)} recent workflow runs from GitHub REST API.")
        except Exception as e2:
            print(f"GitHub REST API query failed: {e2}")

    # Evaluate runs if retrieved
    if runs:
        # Rule 1: Active in_progress or queued run (excluding current run)
        for r in runs:
            r_id = str(r.get("databaseId"))
            if current_run_id and r_id == str(current_run_id):
                continue
            st = (r.get("status") or "").lower()
            if st in ("in_progress", "queued", "waiting", "requested"):
                msg = f"Skipping: another scraper run {r_id} is currently {st}."
                print(msg)
                return True, msg

        # Rule 2: Elapsed time from START (createdAt) of the most recent other run
        for r in runs:
            r_id = str(r.get("databaseId"))
            if current_run_id and r_id == str(current_run_id):
                continue
            created_str = r.get("createdAt")
            if created_str:
                created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                diff_minutes = (now_dt - created_dt).total_seconds() / 60.0
                conclusion = r.get("conclusion") or r.get("status")
                if diff_minutes < min_gap_minutes:
                    msg = f"Skipping: last run #{r_id} started {diff_minutes:.1f}m ago (under {min_gap_minutes}m threshold; conclusion={conclusion})."
                    print(msg)
                    return True, msg
                else:
                    msg = f"Proceeding: last run #{r_id} started {diff_minutes:.1f}m ago (>={min_gap_minutes}m threshold; conclusion={conclusion})."
                    print(msg)
                    return False, msg

    # Fallback to Supabase cron_runs only if GitHub API is completely unavailable
    print("Warning: GitHub API returned no runs. Falling back to Supabase cron_runs check.")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if url and key:
        try:
            from supabase import create_client
            sb = create_client(url, key)
            res = sb.table("cron_runs").select("id, created_at, run_at, status").order("created_at", desc=True).limit(5).execute()
            rows = res.data or []
            for r in rows:
                c_str = r.get("run_at") or r.get("created_at")
                if c_str:
                    c_dt = datetime.fromisoformat(c_str.replace("Z", "+00:00"))
                    diff = (now_dt - c_dt).total_seconds() / 60.0
                    if diff < min_gap_minutes:
                        msg = f"Skipping (DB fallback): last DB run started {diff:.1f}m ago (under {min_gap_minutes}m)."
                        print(msg)
                        return True, msg
                    else:
                        msg = f"Proceeding (DB fallback): last DB run started {diff:.1f}m ago (>={min_gap_minutes}m)."
                        print(msg)
                        return False, msg
        except Exception as e:
            print(f"Supabase DB fallback check failed: {e}")

    return False, "Proceeding: no previous runs found."

if __name__ == "__main__":
    skip, message = check_guard_v3()
    github_output = os.getenv("GITHUB_OUTPUT")
    if github_output and os.path.exists(github_output):
        with open(github_output, "a") as f:
            f.write(f"skip={'true' if skip else 'false'}\n")
    print(f"Scraper guard decision: {'SKIP' if skip else 'PROCEED'}")
    sys.exit(0)
