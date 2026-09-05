import os, sys, psycopg2
from dotenv import load_dotenv

load_dotenv("backend/.env")
db_url = os.getenv("SUPABASE_DB_URL")

if not db_url:
    print("Error: SUPABASE_DB_URL not found in backend/.env")
    sys.exit(1)

STATEMENTS = [
    # 1. reels
    "ALTER TABLE reels ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS reels_public_read ON reels",
    "DROP POLICY IF EXISTS reels_service_role ON reels",
    "CREATE POLICY reels_public_read ON reels FOR SELECT TO public USING (true)",
    "CREATE POLICY reels_service_role ON reels FOR ALL TO service_role USING (true) WITH CHECK (true)",

    # 2. trends
    "ALTER TABLE trends ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS trends_public_read ON trends",
    "DROP POLICY IF EXISTS trends_service_role ON trends",
    "CREATE POLICY trends_public_read ON trends FOR SELECT TO public USING (true)",
    "CREATE POLICY trends_service_role ON trends FOR ALL TO service_role USING (true) WITH CHECK (true)",

    # 3. audio_trend_scores
    "ALTER TABLE audio_trend_scores ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS audio_trend_scores_public_read ON audio_trend_scores",
    "DROP POLICY IF EXISTS audio_trend_scores_service_role ON audio_trend_scores",
    "CREATE POLICY audio_trend_scores_public_read ON audio_trend_scores FOR SELECT TO public USING (true)",
    "CREATE POLICY audio_trend_scores_service_role ON audio_trend_scores FOR ALL TO service_role USING (true) WITH CHECK (true)",

    # 4. tracked_audio
    "ALTER TABLE tracked_audio ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS tracked_audio_public_read ON tracked_audio",
    "DROP POLICY IF EXISTS tracked_audio_service_role ON tracked_audio",
    "CREATE POLICY tracked_audio_public_read ON tracked_audio FOR SELECT TO public USING (true)",
    "CREATE POLICY tracked_audio_service_role ON tracked_audio FOR ALL TO service_role USING (true) WITH CHECK (true)",

    # 5. instagram_tokens (service-role only, zero public access)
    "ALTER TABLE instagram_tokens ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS \"Users can view own Instagram tokens\" ON instagram_tokens",
    "DROP POLICY IF EXISTS \"Users can insert own Instagram tokens\" ON instagram_tokens",
    "DROP POLICY IF EXISTS \"Users can update own Instagram tokens\" ON instagram_tokens",
    "DROP POLICY IF EXISTS \"Users can delete own Instagram tokens\" ON instagram_tokens",
    "DROP POLICY IF EXISTS instagram_tokens_service_role ON instagram_tokens",
    "CREATE POLICY instagram_tokens_service_role ON instagram_tokens FOR ALL TO service_role USING (true) WITH CHECK (true)",

    # 6. cron_runs (service-role only, zero public access)
    "ALTER TABLE cron_runs ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS cron_runs_public_read ON cron_runs",
    "DROP POLICY IF EXISTS cron_runs_service_role ON cron_runs",
    "CREATE POLICY cron_runs_service_role ON cron_runs FOR ALL TO service_role USING (true) WITH CHECK (true)",

    # 7. jobs (service-role only, zero public access)
    "ALTER TABLE jobs ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS jobs_owner_policy ON jobs",
    "DROP POLICY IF EXISTS jobs_service_role ON jobs",
    "CREATE POLICY jobs_service_role ON jobs FOR ALL TO service_role USING (true) WITH CHECK (true)",

    # 8. users (user-owned + service-role)
    "ALTER TABLE users ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS users_owner_policy ON users",
    "DROP POLICY IF EXISTS users_service_role ON users",
    "CREATE POLICY users_owner_policy ON users FOR ALL TO public USING (email = auth.jwt() ->> 'email') WITH CHECK (email = auth.jwt() ->> 'email')",
    "CREATE POLICY users_service_role ON users FOR ALL TO service_role USING (true) WITH CHECK (true)",
]

try:
    print("Connecting to database...")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()
    print("Connected successfully!")
    
    for stmt in STATEMENTS:
        try:
            cur.execute(stmt)
            print(f"OK: {stmt[:60]}...")
        except Exception as e:
            print(f"ERROR executing: {stmt[:60]}... => {e}")
            
    cur.close()
    conn.close()
    print("RLS Lockdown complete.")
except Exception as e:
    print(f"Failed to connect or apply policies: {e}")
    sys.exit(1)
