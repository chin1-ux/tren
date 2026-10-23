import os
import sys
import json
import subprocess
from datetime import datetime, timezone

def check_guard_v3(min_gap_minutes: int = None):
    """
    Tier-3 Early Exit Guard for Scraper Pipeline.
    Zero-egress guard based on GitHub Actions API workflow run history.
    - Measures elapsed time from run START (created_at) of the last real scraping run (duration >= 3m).
    - Manual workflow_dispatch triggers bypass the guard automatically.
    - Any run started within the threshold (default 165m / 2h45m) blocks execution.
    - Consumes 0 Supabase egress.
    """
    if min_gap_minutes is None:
        try:
            min_gap_minutes = int(os.getenv("SCRAPER_GUARD_MIN_GAP_MINUTES", "150"))
        except (ValueError, TypeError):
            min_gap_minutes = 150

    # Manual workflow_dispatch always bypasses guard
    if os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch":
        msg = "Proceeding: manual trigger via workflow_dispatch bypasses guard."
        print(msg)
        return False, msg

    now_dt = datetime.now(timezone.utc)
    current_run_id = os.getenv("GITHUB_RUN_ID")
    repo = os.getenv("GITHUB_REPOSITORY", "chin1-ux/tren")
    gh_token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    
    print(f"=== SCRAPER GUARD V3 CHECK @ {now_dt.strftime('%Y-%m-%d %H:%M:%S UTC')} ===")
    print(f"Target Repo: {repo} | Current Run ID: {current_run_id} | Gap Threshold: {min_gap_minutes}m")
    
    runs = []
    
    # Attempt 1: GitHub API via gh CLI or curl
    try:
        cmd = ["gh", "run", "list", "--workflow", "scraper_cron.yml", "--repo", repo, "--limit", "15", "--json", "databaseId,createdAt,updatedAt,status,conclusion"]
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
                f"https://api.github.com/repos/{repo}/actions/workflows/scraper_cron.yml/runs?per_page=15",
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
                        "updatedAt": r.get("updated_at"),
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

        # Rule 2: Elapsed time from START (createdAt) of the most recent REAL scraping run
        # A REAL run is defined by the pipeline step actually executing (conclusion != 'skipped'),
        # NEVER by duration. Skipped runs never reset the clock.
        def is_real_scraping_run(run_dict):
            rid = str(run_dict.get("databaseId"))
            try:
                cmd_j = ["gh", "api", f"/repos/{repo}/actions/runs/{rid}/jobs", "--jq", ".jobs[0].steps"]
                env_j = os.environ.copy()
                if gh_token:
                    env_j["GH_TOKEN"] = gh_token
                res_j = subprocess.run(cmd_j, env=env_j, capture_output=True, text=True, timeout=10)
                if res_j.returncode == 0 and res_j.stdout.strip():
                    steps_data = json.loads(res_j.stdout.strip())
                    for s in steps_data:
                        if "Run Full Scraper" in s.get("name", ""):
                            c = s.get("conclusion")
                            st = s.get("status")
                            # If pipeline step was skipped, this run was a guard skip
                            if c == "skipped":
                                return False
                            # If step concluded (success/failure/cancelled) or is running, it is a REAL run
                            if c in ("success", "failure", "cancelled") or st == "in_progress":
                                return True
            except Exception as _je:
                pass
            
            # Fallback check via Supabase REST API (standard library only)
            url_env = os.getenv("SUPABASE_URL")
            key_env = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
            if url_env and key_env:
                try:
                    import urllib.request
                    req_cr = urllib.request.Request(
                        f"{url_env.rstrip('/')}/rest/v1/cron_runs?github_run_id=eq.{rid}&select=id&limit=1",
                        headers={
                            "apikey": key_env,
                            "Authorization": f"Bearer {key_env}",
                            "Accept": "application/json",
                        }
                    )
                    with urllib.request.urlopen(req_cr, timeout=5) as resp_cr:
                        if resp_cr.status == 200:
                            data_cr = json.loads(resp_cr.read().decode())
                            if data_cr:
                                return True
                except Exception:
                    pass
            return False

        for r in runs:
            r_id = str(r.get("databaseId"))
            if current_run_id and r_id == str(current_run_id):
                continue
            
            if not is_real_scraping_run(r):
                # Skipped run at guard — ignore it completely, does not reset clock
                continue

            created_str = r.get("createdAt")
            if created_str:
                created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                diff_minutes = (now_dt - created_dt).total_seconds() / 60.0
                conclusion = r.get("conclusion") or r.get("status")
                if diff_minutes < min_gap_minutes:
                    msg = f"Skipping: last real scrape #{r_id} started {diff_minutes:.1f}m ago (under {min_gap_minutes}m threshold; conclusion={conclusion})."
                    print(msg)
                    return True, msg
                else:
                    msg = f"Proceeding: last real scrape #{r_id} started {diff_minutes:.1f}m ago (>={min_gap_minutes}m threshold; conclusion={conclusion})."
                    print(msg)
                    return False, msg

    # Fallback to Supabase cron_runs only if GitHub API is completely unavailable
    print("Warning: GitHub API returned no valid runs. Falling back to Supabase cron_runs check.")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if url and key:
        try:
            import urllib.request
            req_db = urllib.request.Request(
                f"{url.rstrip('/')}/rest/v1/cron_runs?select=id,created_at,run_at,status,reels_scraped&order=created_at.desc&limit=5",
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Accept": "application/json",
                }
            )
            with urllib.request.urlopen(req_db, timeout=5) as resp_db:
                if resp_db.status == 200:
                    rows = json.loads(resp_db.read().decode())
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
