import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv('backend/.env')

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

def check_guard():
    if not url or not key:
        print("No Supabase credentials found, proceeding.")
        return False

    try:
        from supabase import create_client
        sb = create_client(url, key)
        res = sb.table('cron_runs').select('id, run_at, reels_scraped, status').gt('reels_scraped', 0).order('run_at', desc=True).limit(1).execute()
        if res.data:
            last_run = res.data[0]
            run_at_str = last_run['run_at']
            last_dt = datetime.fromisoformat(run_at_str.replace('Z', '+00:00'))
            now_dt = datetime.now(timezone.utc)
            diff_minutes = (now_dt - last_dt).total_seconds() / 60.0
            if diff_minutes < 165:
                print(f"Skipping: last run was {diff_minutes:.1f} minutes ago (under 2h45m threshold).")
                return True
            else:
                print(f"Proceeding: last run was {diff_minutes:.1f} minutes ago (>= 165m).")
                return False
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
        # Non-zero exit code or skip flag can be used
        print("Scraper guard: SKIP")
    else:
        print("Scraper guard: PROCEED")
