import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Initialize Supabase client
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
if not url or not key:
    raise RuntimeError('Supabase credentials not set in environment')
sb = create_client(url, key)

def get_counts():
    reels_res = sb.table('reels').select('id', count='exact').execute()
    trends_res = sb.table('trends').select('id', count='exact').execute()
    reels_cnt = reels_res.count if hasattr(reels_res, 'count') else len(reels_res.data)
    trends_cnt = trends_res.count if hasattr(trends_res, 'count') else len(trends_res.data)
    return reels_cnt, trends_cnt

def main():
    parser = argparse.ArgumentParser(description='Run the Trendrop trend pipeline (or a subset of stages).')
    parser.add_argument(
        '--stages', default=None,
        help='Comma-separated stage subset to run. Default runs all stages. '
             'Valid: schema,scrape,backfill,detect,refresh,snapshots,alerts'
    )
    args = parser.parse_args()

    stages = args.stages.split(',') if args.stages else None
    before_reels, before_trends = get_counts()
    print(f'Before run - reels: {before_reels}, trends: {before_trends}')
    # Run the full pipeline (same as cron job) or the requested stage subset
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from cron_job import run_full_pipeline
    try:
        run_full_pipeline(stages=stages)
    except Exception as e:
        print(f'Pipeline execution failed: {e}', file=sys.stderr)
        sys.exit(1)
    after_reels, after_trends = get_counts()
    print(f'After run - reels: {after_reels}, trends: {after_trends}')
    # Show differences
    print(f'New reels added: {after_reels - before_reels}')
    print(f'New trends added: {after_trends - before_trends}')

if __name__ == '__main__':
    main()
