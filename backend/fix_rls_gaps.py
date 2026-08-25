"""
fix_rls_gaps.py — Fix 7 tables with RLS ON but no policies (total lockout),
and add missing write-block policies on public tables.

Issues to fix:
1. calendar_plans, creator_profiles, creator_trend_memory, pre_post_analyses,
   trend_feedback, trial_reel_plans — need owner-based policies
2. youtube_shorts — public read + service_role write
3. Anon DELETE on public tables (trends, reels) returns 204 — need explicit service_role-only write

Run: python backend/fix_rls_gaps.py
Safe to re-run (all uses DROP IF EXISTS before CREATE).
"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, '.env'))

SUPABASE_DB_URL = os.getenv('SUPABASE_DB_URL')
if not SUPABASE_DB_URL:
    print('ERROR: SUPABASE_DB_URL not set')
    sys.exit(1)

MIGRATIONS = [
    # ── 1. calendar_plans — user-owned ─────────────────────────────────────────
    'DROP POLICY IF EXISTS calendar_plans_owner_policy ON calendar_plans',
    """CREATE POLICY calendar_plans_owner_policy ON calendar_plans
       FOR ALL USING (user_email = auth.jwt() ->> 'email')""",

    # ── 2. creator_profiles — user-owned ───────────────────────────────────────
    'DROP POLICY IF EXISTS creator_profiles_owner_policy ON creator_profiles',
    """CREATE POLICY creator_profiles_owner_policy ON creator_profiles
       FOR ALL USING (user_email = auth.jwt() ->> 'email')""",

    # ── 3. creator_trend_memory — user-owned ───────────────────────────────────
    'DROP POLICY IF EXISTS creator_trend_memory_owner_policy ON creator_trend_memory',
    """CREATE POLICY creator_trend_memory_owner_policy ON creator_trend_memory
       FOR ALL USING (user_email = auth.jwt() ->> 'email')""",

    # ── 4. pre_post_analyses — user-owned ──────────────────────────────────────
    'DROP POLICY IF EXISTS pre_post_analyses_owner_policy ON pre_post_analyses',
    """CREATE POLICY pre_post_analyses_owner_policy ON pre_post_analyses
       FOR ALL USING (user_email = auth.jwt() ->> 'email')""",

    # ── 5. trend_feedback — user-owned ─────────────────────────────────────────
    'DROP POLICY IF EXISTS trend_feedback_owner_policy ON trend_feedback',
    """CREATE POLICY trend_feedback_owner_policy ON trend_feedback
       FOR ALL USING (user_email = auth.jwt() ->> 'email')""",

    # ── 6. trial_reel_plans — user-owned ───────────────────────────────────────
    'DROP POLICY IF EXISTS trial_reel_plans_owner_policy ON trial_reel_plans',
    """CREATE POLICY trial_reel_plans_owner_policy ON trial_reel_plans
       FOR ALL USING (user_email = auth.jwt() ->> 'email')""",

    # ── 7. youtube_shorts — public read + service_role write ───────────────────
    'DROP POLICY IF EXISTS youtube_shorts_public_read ON youtube_shorts',
    """CREATE POLICY youtube_shorts_public_read ON youtube_shorts
       FOR SELECT USING (true)""",
    'DROP POLICY IF EXISTS youtube_shorts_service_role ON youtube_shorts',
    """CREATE POLICY youtube_shorts_service_role ON youtube_shorts
       FOR ALL TO service_role USING (true)""",

    # ── 8. Block anon DELETE/UPDATE/INSERT on public-read tables ───────────────
    # trends: already has service_role policy, anon DELETE shouldn't work — 
    # the issue is the public read policy allows DELETE because it's FOR ALL on 'public'
    # Check: trends_public_read is FOR SELECT already (see audit). The DELETE 204 issue
    # is because there are no rows matching, so PostgREST returns 204 (no content) — this
    # is NOT actually deleting anything (RLS blocks it). The HTTP 204 is misleading.
    # Confirmed: trying to delete specific row returns 0 rows affected, not an actual deletion.
    # No additional fix needed for trends/reels DELETE — RLS already blocks writes.
    # The 204 is PostgREST's response to a filtered DELETE that matches 0 rows after RLS filtering.
]


def run():
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL, connect_timeout=15)
        conn.autocommit = True
        cur = conn.cursor()
        print(f'Connected to DB. Running {len(MIGRATIONS)} statements...')

        ok = 0
        failed = 0
        for stmt in MIGRATIONS:
            stmt = stmt.strip()
            if not stmt:
                continue
            try:
                cur.execute(stmt)
                print(f'OK  >> {stmt[:80]}')
                ok += 1
            except Exception as e:
                print(f'ERR >> {stmt[:80]}  [{e}]')
                failed += 1

        cur.close()
        conn.close()
        print(f'\nDone: {ok} OK, {failed} failed.')

    except Exception as e:
        print(f'Connection error: {e}')
        sys.exit(1)


if __name__ == '__main__':
    run()
