import os
import sys
try:
    import psycopg2
except ImportError:
    psycopg2 = None
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env
load_dotenv()

# Supabase REST client configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# PostgreSQL Direct Connection configuration
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

# SQL queries to create the requested tables
TABLES_SQL = {
    "reels": """
        CREATE TABLE IF NOT EXISTS reels (
            id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            platform text,
            reel_id text UNIQUE,
            view_count int,
            like_count int,
            comment_count int,
            share_count int,
            posted_at timestamp,
            owner_username text,
            owner_follower_count int,
            audio_title text,
            audio_artist text,
            hashtags text[],
            caption text,
            velocity_score float,
            content_type text,
            is_dance boolean,
            language text,
            video_url text,
            thumbnail_url text,
            created_at timestamp DEFAULT now()
        );
    """,
    "trends": """
        CREATE TABLE IF NOT EXISTS trends (
            id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            audio_title text,
            audio_artist text,
            platform text,
            trend_type text,
            velocity_avg float,
            reel_count int,
            is_dance boolean,
            needs_filming boolean,
            edit_style text,
            narrative_structure text,
            text_overlay_template text,
            language text,
            cultural_context text,
            ideal_content_description text,
            camera_style text,
            window_hours_remaining int,
            confidence float,
            status text DEFAULT 'rising',
            peak_velocity float,
            saturation_score float,
            optimal_post_hour_ist int,
            best_platform_first text,
            why_this_works text,
            audio_cue_second int,
            content_type text,
            format_transferable boolean DEFAULT false,
            transfer_instructions text,
            first_detected_at timestamp DEFAULT now()
        );
    """,
    "users": """
        CREATE TABLE IF NOT EXISTS users (
            id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            email text UNIQUE,
            niche text,
            language_preference text,
            plan text DEFAULT 'free',
            push_token text,
            auth_token text,
            created_at timestamp DEFAULT now()
        );
    """,
    "jobs": """
        CREATE TABLE IF NOT EXISTS jobs (
            id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            job_type text,
            status text DEFAULT 'pending',
            user_email text,
            progress int DEFAULT 0,
            input_data text,
            output_url text,
            error_message text,
            created_at timestamp DEFAULT now()
        );
    """,
    "youtube_shorts": """
        CREATE TABLE IF NOT EXISTS youtube_shorts (
            id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            video_id text UNIQUE,
            title text,
            channel_title text,
            channel_id text,
            view_count int,
            like_count int,
            comment_count int,
            published_at timestamp,
            tags text[],
            velocity_score float,
            region_code text,
            language text,
            created_at timestamp DEFAULT now()
        );
    """,
    "daily_ideas": """
        CREATE TABLE IF NOT EXISTS daily_ideas (
            id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            user_email text,
            niche text,
            title text,
            description text,
            hook text,
            audio_suggestion text,
            posting_time text,
            created_at timestamp DEFAULT now()
        );
    """,
    "calendar_plans": """
        CREATE TABLE IF NOT EXISTS calendar_plans (
            id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            user_email text UNIQUE,
            niche text,
            language text,
            frequency text,
            schedule_data jsonb,
            created_at timestamp DEFAULT now()
        );
    """,
    "creator_profiles": """
        CREATE TABLE IF NOT EXISTS creator_profiles (
            id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            user_email text UNIQUE,
            instagram_username text,
            niche text,
            followers int,
            engagement_rate float,
            trend_score float,
            portfolio_links text[],
            price_per_post int,
            is_active boolean DEFAULT true,
            created_at timestamp DEFAULT now()
        );
    """,
    "brand_deals": """
        CREATE TABLE IF NOT EXISTS brand_deals (
            id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            creator_email text,
            brand_name text,
            deal_amount int,
            commission_amount float,
            status text DEFAULT 'pending',
            details text,
            requirements text,
            created_at timestamp DEFAULT now()
        );
    """,
    "brand_deal_applications": """
        CREATE TABLE IF NOT EXISTS brand_deal_applications (
            id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            deal_id bigint,
            user_email text,
            pitch text,
            created_at timestamp DEFAULT now()
        );
    """,
    "collab_requests": """
        CREATE TABLE IF NOT EXISTS collab_requests (
            id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            from_email text,
            to_email text,
            message text,
            created_at timestamp DEFAULT now()
        );
    """,
    "pre_post_analyses": """
        CREATE TABLE IF NOT EXISTS pre_post_analyses (
            id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            user_email text,
            video_url text,
            analysis_details jsonb,
            score int,
            created_at timestamp DEFAULT now()
        );
    """,
    "trend_feedback": """
        CREATE TABLE IF NOT EXISTS trend_feedback (
            id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            trend_id bigint,
            feedback_type text,
            comment text,
            user_email text,
            created_at timestamp DEFAULT now()
        );
    """,
    "creator_trend_memory": """
        CREATE TABLE IF NOT EXISTS creator_trend_memory (
            id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            user_email text,
            trend_id bigint,
            format_name text,
            hook_variant text,
            planned_mode text,
            outcome_score float,
            notes text,
            created_at timestamp DEFAULT now()
        );
    """,
    "trial_reel_plans": """
        CREATE TABLE IF NOT EXISTS trial_reel_plans (
            id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            user_email text,
            trend_id bigint,
            decision text,
            rationale text,
            test_hook text,
            public_hook text,
            created_at timestamp DEFAULT now()
        );
    """,
    "consent_records": """
        CREATE TABLE IF NOT EXISTS consent_records (
            id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            user_email text,
            consent_type text,
            granted boolean DEFAULT true,
            ip_address text,
            user_agent text,
            created_at timestamp DEFAULT now()
        );
    """
}

def main():
    print("Connecting to Supabase...")
    
    # 1. Initialize Supabase python client
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Warning: SUPABASE_URL or SUPABASE_KEY is missing from environment variables.")
    else:
        try:
            # Check initialization
            supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            print("Successfully initialized Supabase Python client.")
        except Exception as e:
            print(f"Warning: Failed to initialize Supabase client: {e}")

    # 2. Check Database URL and execute DDL queries via direct PostgreSQL connection
    if not SUPABASE_DB_URL:
        print("Warning: SUPABASE_DB_URL is missing; skipping direct PostgreSQL setup.")
        conn = None
        cursor = None
    else:
        conn = None
        cursor = None

        if psycopg2 and SUPABASE_DB_URL:
            try:
                # Connect to Supabase Postgres database directly
                conn = psycopg2.connect(SUPABASE_DB_URL)
                conn.autocommit = True
                cursor = conn.cursor()
                print("Successfully connected to Supabase PostgreSQL database.")
            except Exception as e:
                print(f"Database connection error: {e}")
                print("Skipping DB setup; proceeding with Supabase client only.")
                conn = None
                cursor = None
        else:
            print("psycopg2 not installed or DB URL missing; skipping direct DB connection.")
            conn = None
            cursor = None

    all_success = True

    # 3. Create tables one by one with individual error handling
    if cursor:
        for table_name, sql_query in TABLES_SQL.items():
            try:
                print(f"Creating table '{table_name}'...")
                cursor.execute(sql_query)
                print(f"Table '{table_name}' checked/created successfully.")
            except Exception as e:
                print(f"Error creating table '{table_name}': {e}")
                all_success = False

    # 4. Perform alterations/indexes
    if cursor:
        try:
            print("Performing table alterations...")
            cursor.execute("ALTER TABLE trends ADD COLUMN IF NOT EXISTS format_transferable boolean DEFAULT false;")
            cursor.execute("ALTER TABLE trends ADD COLUMN IF NOT EXISTS transfer_instructions text;")
            cursor.execute("ALTER TABLE trends ADD COLUMN IF NOT EXISTS creator_fit_score float;")
            cursor.execute("ALTER TABLE trends ADD COLUMN IF NOT EXISTS saturation_penalty float;")
            cursor.execute("ALTER TABLE trends ADD COLUMN IF NOT EXISTS hook_retention_score float;")
            cursor.execute("ALTER TABLE trends ADD COLUMN IF NOT EXISTS composite_score float;")
            cursor.execute("ALTER TABLE brand_deals ADD COLUMN IF NOT EXISTS requirements text;")
            
            # 2.1 DATABASE OPTIMISATION: INDEXES
            print("Creating database indexes...")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reels_vel_type_lang_posted_audio ON reels (velocity_score, content_type, language, posted_at, audio_title);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trends_status_vel_type_lang_first ON trends (status, velocity_avg, content_type, language, first_detected_at);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status_email_created ON jobs (status, user_email, created_at);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email_niche_lang ON users (email, niche, language_preference);")
            
            # 1.2 ROW LEVEL SECURITY ON SUPABASE (Enable RLS on every table)
            print("Enabling Row Level Security (RLS) on all tables...")
            tables_to_rls = [
                "users", "jobs", "trends", "reels", "brand_deals",
                "brand_deal_applications", "collab_requests", "daily_ideas",
                "calendar_plans", "creator_profiles", "pre_post_analyses",
                "trend_feedback", "creator_trend_memory", "trial_reel_plans",
                "consent_records"
            ]
            for tbl in tables_to_rls:
                cursor.execute(f"ALTER TABLE IF EXISTS {tbl} ENABLE ROW LEVEL SECURITY;")
                
            # Create policies. Use sub-queries or metadata where appropriate.
            # First, drop policies if they exist. (In Postgres 9.6+, drop policy if exists is safe)
            # 1.2 policies requirements:
            # users: auth.uid() = id (or matching email via subquery or metadata)
            # jobs: auth.uid() = user_id (since jobs has user_email, we can do auth.jwt() ->> 'email' = user_email)
            # trends: all authenticated users can read, only service role can write (RLS enabled, select: true/authenticated, others: false/service role)
            # reels: only service role can read and write (default RLS is deny-all unless policy allows)
            # brand_deals: authenticated users can read open deals (status='open'), only service role can create/write.
            # deal_applications (brand_deal_applications): users can only read and create their own applications (user_email = auth.jwt() ->> 'email')
            # collab_requests: users can read requests where they are requester or target (from_email = auth.jwt() ->> 'email' or to_email = auth.jwt() ->> 'email')
            # content_ideas (daily_ideas): users can only read their own ideas (user_email = auth.jwt() ->> 'email')

            # We use auth.jwt() ->> 'email' for email matching since users tables use email as the identifier.
            
            # users policy
            cursor.execute("DROP POLICY IF EXISTS users_owner_policy ON users;")
            cursor.execute("CREATE POLICY users_owner_policy ON users FOR ALL USING (email = auth.jwt() ->> 'email');")
            
            # jobs policy
            cursor.execute("DROP POLICY IF EXISTS jobs_owner_policy ON jobs;")
            cursor.execute("CREATE POLICY jobs_owner_policy ON jobs FOR ALL USING (user_email = auth.jwt() ->> 'email');")
            
            # trends policy
            cursor.execute("DROP POLICY IF EXISTS trends_auth_read_policy ON trends;")
            cursor.execute("CREATE POLICY trends_auth_read_policy ON trends FOR SELECT TO authenticated USING (true);")
            
            # reels: no policy = service role bypasses RLS automatically, authenticated/public denied
            cursor.execute("DROP POLICY IF EXISTS reels_deny_policy ON reels;")
            
            # brand_deals policy
            cursor.execute("DROP POLICY IF EXISTS brand_deals_read_policy ON brand_deals;")
            cursor.execute("CREATE POLICY brand_deals_read_policy ON brand_deals FOR SELECT TO authenticated USING (status = 'open' OR creator_email = auth.jwt() ->> 'email');")
            
            # brand_deal_applications policy
            cursor.execute("DROP POLICY IF EXISTS deal_apps_owner_policy ON brand_deal_applications;")
            cursor.execute("CREATE POLICY deal_apps_owner_policy ON brand_deal_applications FOR ALL USING (user_email = auth.jwt() ->> 'email');")
            
            # collab_requests policy
            cursor.execute("DROP POLICY IF EXISTS collab_owner_policy ON collab_requests;")
            cursor.execute("DROP POLICY IF EXISTS collab_insert_policy ON collab_requests;")
            cursor.execute("CREATE POLICY collab_owner_policy ON collab_requests FOR SELECT USING (from_email = auth.jwt() ->> 'email' OR to_email = auth.jwt() ->> 'email');")
            cursor.execute("CREATE POLICY collab_insert_policy ON collab_requests FOR INSERT WITH CHECK (from_email = auth.jwt() ->> 'email');")
            
            # daily_ideas policy
            cursor.execute("DROP POLICY IF EXISTS daily_ideas_owner_policy ON daily_ideas;")
            cursor.execute("CREATE POLICY daily_ideas_owner_policy ON daily_ideas FOR SELECT USING (user_email = auth.jwt() ->> 'email');")

            # consent_records policy
            cursor.execute("DROP POLICY IF EXISTS consent_owner_policy ON consent_records;")
            cursor.execute("CREATE POLICY consent_owner_policy ON consent_records FOR ALL USING (user_email = auth.jwt() ->> 'email');")
            
            print("Table alterations, indexes, and RLS policies completed successfully.")
        except Exception as e:
            print(f"Error performing alterations/policies/indexes: {e}")
            all_success = False

    # Clean up connections
    if cursor:
        cursor.close()
    if conn:
        conn.close()

    if all_success:
        print("All tables and modifications executed successfully")
    else:
        print("Some database setup tasks failed. Please check the logs above.")

if __name__ == "__main__":
    main()
