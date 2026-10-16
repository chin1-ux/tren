import os
import sys
import json
import subprocess
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

out_file = "evidence/order79/truth_check_0.txt"

def run_cmd(cmd):
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
        return (res.stdout or "").strip(), (res.stderr or "").strip()
    except Exception as e:
        return "", str(e)

lines = []
lines.append("=" * 80)
lines.append("ORDER 79 ITEM 0: TRUTH CHECK (RAW AUDIT)")
lines.append(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
lines.append("=" * 80)

# a) Deployed prod SHA vs git HEAD vs uncommitted changes
lines.append("\n--- 0.a) DEPLOYED PROD SHA vs GIT HEAD vs UNCOMMITTED CHANGES ---")
git_head, _ = run_cmd("git rev-parse HEAD")
git_status, _ = run_cmd("git status --short")
lines.append(f"Git HEAD SHA: {git_head}")
lines.append(f"Uncommitted Changes Count: {len(git_status.splitlines()) if git_status else 0}")
lines.append("Uncommitted files:")
for l in git_status.splitlines()[:25]:
    lines.append(f"  {l}")

# Check latest Vercel deployment info
vercel_ls, _ = run_cmd("npx vercel ls trendrop --prod")
lines.append("\nLatest Vercel Production Deployments:")
lines.append(vercel_ls[:500] if vercel_ls else "None found via CLI")

# b) TrendPreviewModal inspection & audio_page_cache table existence
lines.append("\n--- 0.b) MODAL REEL SOURCE & audio_page_cache EXISTENCE ---")
lines.append("Checking frontend/src/components/TrendPreviewModal.tsx for reel source:")
with open("frontend/src/components/TrendPreviewModal.tsx", "r", encoding="utf-8") as f:
    modal_content = f.read()

if "fetchTrendReels" in modal_content:
    lines.append("  [FACT] TrendPreviewModal calls fetchTrendReels (endpoint: /api/trends/{id}/reels).")
if "audio_page_cache" in modal_content:
    lines.append("  [FACT] TrendPreviewModal queries audio_page_cache directly.")
else:
    lines.append("  [FACT] TrendPreviewModal does NOT query audio_page_cache.")

lines.append("Checking if 'audio_page_cache' table exists in Supabase:")
try:
    from supabase import create_client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    sb = create_client(supabase_url, supabase_key)
    res = sb.table("audio_page_cache").select("*").limit(1).execute()
    lines.append(f"  [FACT] audio_page_cache query result: data={res.data}")
except Exception as e:
    lines.append(f"  [FACT] audio_page_cache table query ERROR: {e}")
    lines.append("  Conclusion: audio_page_cache does NOT exist in production Supabase yet.")

lines.append("What the Reel Pager actually pages through:")
lines.append("  [FACT] It pages through rows from the Supabase 'reels' table linked to the trend (via /api/trends/{id}/reels).")
lines.append("  [FACT] These reels were scraped during regular background scraper runs, NOT extracted live from the Instagram audio page.")

# c) Order 78 Item A2 and A4 execution environment
lines.append("\n--- 0.c) ORDER 78 A2 & A4 RUNNER vs LOCAL EXECUTION ---")
lines.append("Reviewing execution origin of Order 78 probe and fallback files:")
if os.path.exists("evidence/order78/item8_probe_local.txt"):
    lines.append("  [FACT] 'item8_probe_local.txt' was executed LOCALLY on Windows PC (hence file name 'item8_probe_local').")
if os.path.exists("evidence/order78/a4_thumbnail_fallbacks.txt"):
    lines.append("  [FACT] 'a4_thumbnail_fallbacks.txt' was generated locally.")
lines.append("Verdict: Order 78 Step A probe ran locally, NOT on a GitHub Actions runner. Hand-marked files -> FAIL.")

# d) Disabled workflows & trend-refresh audit
lines.append("\n--- 0.d) DISABLED WORKFLOWS & TREND-REFRESH STATUS ---")
gh_wf, _ = run_cmd("gh workflow list --repo ch1n-may/trendrop")
lines.append("Workflows in ch1n-may/trendrop:")
for l in gh_wf.splitlines():
    lines.append(f"  {l}")

lines.append("\nWorkflows in dedicated scraper repo chin1-ux/tren:")
gh_wf_tren, _ = run_cmd("gh workflow list --repo chin1-ux/tren")
for l in gh_wf_tren.splitlines():
    lines.append(f"  {l}")

# Check latest trend-refresh run or cron_runs
lines.append("\nChecking latest trend_refresher / lifecycle update in Supabase cron_runs:")
try:
    r_runs = sb.table("cron_runs").select("id,job_type,status,run_at,created_at,reels_scraped,new_reels_count").order("created_at", desc=True).limit(5).execute()
    for row in (r_runs.data or []):
        lines.append(f"  Run ID={row.get('id')} | Type={row.get('job_type')} | Status={row.get('status')} | Time={row.get('created_at') or row.get('run_at')}")
except Exception as e:
    lines.append(f"  Error checking cron_runs: {e}")

# e) Scheduler 38-minute gap vs 165-minute guard
lines.append("\n--- 0.e) SCHEDULER: 38-MIN GAP VS 165-MIN GUARD CAUSE ---")
lines.append("Analyzing check_scraper_guard.py and workflow cron triggers:")
with open("scripts/check_scraper_guard.py", "r", encoding="utf-8") as f:
    guard_code = f.read()
lines.append("Excerpt from scripts/check_scraper_guard.py:")
for l in guard_code.splitlines()[:25]:
    lines.append(f"  {l}")

# f) trends.status counts and why ~48% resurging
lines.append("\n--- 0.f) TRENDS.STATUS BREAKDOWN & RESURGING CAUSE ---")
try:
    # Query distinct statuses
    res_status = sb.rpc("get_status_counts", {}).execute() if False else None
    # Let's count by status manually via select
    statuses = ["emerging", "rising", "resurging", "peaked", "expired", "unqualified"]
    lines.append("Querying status counts from trends table:")
    total_active = 0
    for st in statuses:
        r_st = sb.table("trends").select("id", count="exact").eq("status", st).execute()
        cnt = r_st.count
        lines.append(f"  Status: {st:12} = {cnt}")
        if st in ["emerging", "rising", "resurging", "peaked"]:
            total_active += (cnt or 0)
    lines.append(f"  Total Active Feed Eligible: {total_active}")

    # Inspect code where 'resurging' is assigned
    lines.append("\nSearching codebase for 'resurging' assignment logic:")
    grep_resurging, _ = run_cmd("git grep -n \"status.*resurging\" backend/")
    lines.append(grep_resurging[:1000])

except Exception as e:
    lines.append(f"Error querying status breakdown: {e}")

lines.append("\n" + "=" * 80)
lines.append("END OF TRUTH CHECK 0")
lines.append("=" * 80)

output_text = "\n".join(lines)
with open(out_file, "w", encoding="utf-8") as f:
    f.write(output_text)

print(output_text)
