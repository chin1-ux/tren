import os
from dotenv import load_dotenv
load_dotenv('backend/.env')
from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
sb = create_client(url, key)

res = sb.table('cron_runs').select('id, run_at, reels_scraped, stage_timings, new_trends_found, trend_ids, status, cutoff_reason').gt('reels_scraped', 0).order('run_at', desc=True).limit(10).execute()
runs = res.data or []

print("=" * 95)
print("ORDER 77 ITEM 9: FUNNEL TABLE FOR LAST 10 SCRAPER RUNS (FROM cron_runs)")
print("=" * 95)
print(f"{'Run ID':<8} | {'Run At (UTC)':<20} | {'Scraped':<8} | {'Candidates':<11} | {'Confirmed':<10} | {'New Trends':<11} | {'Emerging IDs'}")
print("-" * 95)

total_scraped = 0
total_candidates = 0
total_confirmed = 0
total_new = 0

for r in runs:
    run_id = r.get('id')
    run_at = (r.get('run_at') or '')[:19].replace('T', ' ')
    scraped = r.get('reels_scraped') or 0
    timings = r.get('stage_timings') or {}
    clf = timings.get('classification') if isinstance(timings, dict) else {}
    candidates = clf.get('candidate_count', 0) if isinstance(clf, dict) else 0
    confirmed = clf.get('classified_count', 0) if isinstance(clf, dict) else 0
    new_tr = r.get('new_trends_found') or 0
    trend_ids = r.get('trend_ids') or []
    
    total_scraped += scraped
    total_candidates += candidates
    total_confirmed += confirmed
    total_new += new_tr
    
    t_ids_str = str(trend_ids[:4]) + (f" (+{len(trend_ids)-4})" if len(trend_ids) > 4 else "")
    print(f"{run_id:<8} | {run_at:<20} | {scraped:<8} | {candidates:<11} | {confirmed:<10} | {new_tr:<11} | {t_ids_str}")

print("-" * 95)
print(f"{'TOTAL':<8} | {'10 RUNS':<20} | {total_scraped:<8} | {total_candidates:<11} | {total_confirmed:<10} | {total_new:<11} |")
print(f"{'AVERAGE':<8} | {'PER RUN':<20} | {total_scraped/max(1, len(runs)):<8.1f} | {total_candidates/max(1, len(runs)):<11.1f} | {total_confirmed/max(1, len(runs)):<10.1f} | {total_new/max(1, len(runs)):<11.1f} |")
print("=" * 95)
